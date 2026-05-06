"""Document intelligence service — auto-classification, similar document search, text extraction."""

from sqlalchemy import select, func, text, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentCategory, Tag
from app.utils.text_extractor import extract_text


# ---------- Keyword-based category suggestion ----------

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    # These are defaults; will be augmented by actual category names from the DB
    "招生": ["招生", "录取", "报名", "考试", "分数线", "志愿", "批次"],
    "教学": ["教学", "课程", "学分", "考试", "成绩", "毕业", "论文", "答辩"],
    "科研": ["科研", "课题", "项目", "经费", "论文", "专利", "成果", "学术"],
    "人事": ["人事", "招聘", "考核", "薪酬", "合同", "编制", "职称"],
    "财务": ["财务", "预算", "报销", "审计", "经费", "采购", "资产"],
    "行政": ["行政", "公文", "通知", "会议", "纪要", "督办", "档案"],
    "学生": ["学生", "学籍", "社团", "奖助", "就业", "宿舍", "辅导员"],
    "后勤": ["后勤", "基建", "物业", "食堂", "绿化", "维修"],
    "安全": ["安全", "消防", "保卫", "应急", "预案", "演练"],
}


async def suggest_category(
    db: AsyncSession, file_name: str = "", extracted_text: str | None = None
) -> list[dict]:
    """Suggest categories based on file name and extracted text content.

    Returns list of {category_id, category_name, score} sorted by relevance.
    """
    combined = f"{file_name} {extracted_text or ''}"

    # Build keyword map from DB categories plus defaults
    result = await db.execute(select(DocumentCategory).order_by(DocumentCategory.sort_order))
    categories = result.scalars().all()

    scores = []
    for cat in categories:
        # Get keywords: try DB defaults from CATEGORY_KEYWORDS, then derive from name
        keywords = CATEGORY_KEYWORDS.get(cat.name, [cat.name])
        score = sum(1 for kw in keywords if kw in combined)
        if score > 0:
            scores.append({
                "category_id": cat.id,
                "category_name": cat.name,
                "score": score,
            })

    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores[:3]


async def suggest_tags(
    db: AsyncSession, extracted_text: str | None = None
) -> list[dict]:
    """Suggest tags based on extracted text content.

    Returns list of {tag_id, tag_name, matched_keyword} based on keyword matching.
    """
    if not extracted_text:
        return []

    result = await db.execute(select(Tag))
    tags = result.scalars().all()

    suggestions = []
    for tag in tags:
        if tag.name in extracted_text:
            suggestions.append({
                "tag_id": tag.id,
                "tag_name": tag.name,
                "matched_keyword": tag.name,
            })

    return suggestions


# ---------- Similar document search ----------

async def find_similar_documents(
    db: AsyncSession,
    doc_id: int,
    limit: int = 10,
) -> list[dict]:
    """Find documents similar to the given document using PostgreSQL full-text search.

    Uses ts_rank over the FTS GIN index on document.original_name + extracted_text.
    """
    # First get the source document's text
    doc_result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.is_deleted == False)
    )
    source_doc = doc_result.scalars().first()
    if not source_doc:
        return []

    # Build query text from the source document
    query_parts = []
    if source_doc.original_name:
        query_parts.append(source_doc.original_name)
    if source_doc.extracted_text:
        # Take first 2000 chars to keep the query reasonable
        query_parts.append(source_doc.extracted_text[:2000])
    if source_doc.description:
        query_parts.append(source_doc.description)

    query_text = " ".join(query_parts)
    if not query_text.strip():
        return []

    # Use plainto_tsquery for natural language matching
    # Exclude the source document itself
    similarity_sql = text("""
        SELECT
            d.id,
            d.original_name,
            d.file_type,
            d.description,
            d.status,
            ts_rank(
                to_tsvector('simple', coalesce(d.original_name, '') || ' ' || coalesce(d.extracted_text, '') || ' ' || coalesce(d.description, '')),
                plainto_tsquery('simple', :query)
            ) AS rank,
            ts_headline(
                'simple',
                coalesce(d.extracted_text, coalesce(d.description, '')),
                plainto_tsquery('simple', :query),
                'MaxWords=40, MinWords=15, ShortWord=2'
            ) AS headline
        FROM document d
        WHERE d.id != :doc_id
          AND d.is_deleted = false
          AND to_tsvector('simple', coalesce(d.original_name, '') || ' ' || coalesce(d.extracted_text, '') || ' ' || coalesce(d.description, ''))
              @@ plainto_tsquery('simple', :query)
        ORDER BY rank DESC
        LIMIT :limit
    """)

    result = await db.execute(similarity_sql, {
        "query": query_text,
        "doc_id": doc_id,
        "limit": limit,
    })

    return [
        {
            "document_id": row[0],
            "original_name": row[1],
            "file_type": row[2],
            "description": row[3],
            "status": row[4],
            "similarity_score": round(float(row[5]), 4),
            "headline": row[6],
        }
        for row in result.all()
    ]


async def find_similar_by_text(
    db: AsyncSession,
    search_text: str,
    exclude_id: int | None = None,
    limit: int = 10,
) -> list[dict]:
    """Find documents similar to arbitrary text (e.g., for upload-time suggestions)."""
    if not search_text.strip():
        return []

    conditions = "d.is_deleted = false"
    params = {"query": search_text, "limit": limit}

    if exclude_id is not None:
        conditions += " AND d.id != :exclude_id"
        params["exclude_id"] = exclude_id

    similarity_sql = text(f"""
        SELECT
            d.id,
            d.original_name,
            d.file_type,
            d.description,
            d.status,
            ts_rank(
                to_tsvector('simple', coalesce(d.original_name, '') || ' ' || coalesce(d.extracted_text, '') || ' ' || coalesce(d.description, '')),
                plainto_tsquery('simple', :query)
            ) AS rank,
            ts_headline(
                'simple',
                coalesce(d.extracted_text, coalesce(d.description, '')),
                plainto_tsquery('simple', :query),
                'MaxWords=40, MinWords=15, ShortWord=2'
            ) AS headline
        FROM document d
        WHERE {conditions}
          AND to_tsvector('simple', coalesce(d.original_name, '') || ' ' || coalesce(d.extracted_text, '') || ' ' || coalesce(d.description, ''))
              @@ plainto_tsquery('simple', :query)
        ORDER BY rank DESC
        LIMIT :limit
    """)

    result = await db.execute(similarity_sql, params)

    return [
        {
            "document_id": row[0],
            "original_name": row[1],
            "file_type": row[2],
            "description": row[3],
            "status": row[4],
            "similarity_score": round(float(row[5]), 4),
            "headline": row[6],
        }
        for row in result.all()
    ]


# ---------- Text extraction on upload ----------

async def extract_and_store_text(
    db: AsyncSession,
    doc_id: int,
    file_data: bytes,
    file_type: str,
    original_name: str,
) -> str | None:
    """Extract text from file content and store it on the document record.

    Returns the extracted text or None.
    """
    extracted = extract_text(file_data, file_type, original_name)

    if extracted:
        await db.execute(
            text("UPDATE document SET extracted_text = :txt WHERE id = :id"),
            {"txt": extracted, "id": doc_id},
        )
        await db.commit()

    return extracted


# ---------- Vector-based similar document search ----------

async def find_similar_by_vector(
    db: AsyncSession, doc_id: int, limit: int = 10,
) -> list[dict]:
    """Find similar documents using pgvector cosine distance."""
    result = await db.execute(
        text("SELECT embedding FROM document WHERE id = :did AND is_deleted = false"),
        {"did": doc_id},
    )
    row = result.scalar_one_or_none()
    if not row:
        return []

    sql = text("""
        SELECT d.id, d.original_name, d.file_type, d.description, d.status,
               1 - (d.embedding <=> :embedding) AS similarity
        FROM document d
        WHERE d.id != :doc_id
          AND d.is_deleted = false
          AND d.embedding IS NOT NULL
        ORDER BY d.embedding <=> :embedding
        LIMIT :limit
    """)
    result = await db.execute(sql, {"embedding": row, "doc_id": doc_id, "limit": limit})
    return [
        {
            "document_id": r[0],
            "original_name": r[1],
            "file_type": r[2],
            "description": r[3],
            "status": r[4],
            "similarity_score": round(float(r[5]), 4),
            "headline": None,
        }
        for r in result.all()
    ]


# ---------- Document relation graph data ----------

async def get_document_graph_data(
    db: AsyncSession,
    doc_id: int,
    depth: int = 1,
) -> dict:
    """Build force-directed graph data for a document and its related documents.

    Returns {nodes: [...], links: [...]} for ECharts force graph.
    """
    # Get source document
    doc_result = await db.execute(
        select(Document)
        .options(selectinload(Document.category), selectinload(Document.tags))
        .where(Document.id == doc_id, Document.is_deleted == False)
    )
    source = doc_result.scalars().first()
    if not source:
        return {"nodes": [], "links": []}

    nodes = [{
        "id": f"doc_{source.id}",
        "name": source.original_name[:30],
        "type": "document",
        "symbolSize": 50,
        "category": 0,  # source
    }]
    links = []
    node_ids = {source.id}

    # 1. Documents in the same category
    if source.category_id:
        category_docs_result = await db.execute(
            select(Document).where(
                Document.category_id == source.category_id,
                Document.id != source.id,
                Document.is_deleted == False,
            ).limit(10)
        )
        for doc in category_docs_result.scalars().all():
            if doc.id not in node_ids:
                nodes.append({
                    "id": f"doc_{doc.id}",
                    "name": doc.original_name[:30],
                    "type": "document",
                    "symbolSize": 30,
                    "category": 1,  # same category
                })
                node_ids.add(doc.id)
            links.append({
                "source": f"doc_{source.id}",
                "target": f"doc_{doc.id}",
                "label": "同分类",
            })

    # 2. Documents with similar content (FTS)
    if source.extracted_text:
        similar = await find_similar_documents(db, doc_id, limit=8)
        for s in similar:
            sid = s["document_id"]
            if sid not in node_ids:
                nodes.append({
                    "id": f"doc_{sid}",
                    "name": s["original_name"][:30],
                    "type": "document",
                    "symbolSize": 25 + s["similarity_score"] * 15,
                    "category": 2,  # similar
                })
                node_ids.add(sid)
            links.append({
                "source": f"doc_{source.id}",
                "target": f"doc_{sid}",
                "label": f"相似度 {s['similarity_score']:.2f}",
            })

    # 3. Documents that share tags
    if source.tags:
        tag_ids = [t.id for t in source.tags]
        tag_docs_result = await db.execute(
            select(Document)
            .join(Document.tags)
            .where(
                Tag.id.in_(tag_ids),
                Document.id != source.id,
                Document.is_deleted == False,
            )
            .limit(8)
        )
        for doc in tag_docs_result.scalars().all():
            if doc.id not in node_ids:
                nodes.append({
                    "id": f"doc_{doc.id}",
                    "name": doc.original_name[:30],
                    "type": "document",
                    "symbolSize": 25,
                    "category": 3,  # same tags
                })
                node_ids.add(doc.id)
            links.append({
                "source": f"doc_{source.id}",
                "target": f"doc_{doc.id}",
                "label": "相同标签",
            })

    return {
        "nodes": nodes,
        "links": links,
        "categories": [
            {"name": "当前文档"},
            {"name": "同事项"},
            {"name": "内容相似"},
            {"name": "相同标签"},
        ],
    }
