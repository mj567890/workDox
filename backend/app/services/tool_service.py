"""Agent tools: function definitions and execution for document library queries."""

import json
import logging

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentCategory, Tag
from app.models.ai import DocumentChunk

logger = logging.getLogger(__name__)

# ── Tool definitions (OpenAI function-calling schema) ──────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                "在文档库中搜索文档。按关键词匹配文档名称和描述。"
                "仅返回文档元数据（名称、类型、状态），不含文档正文内容。"
                "用于回答'有没有关于X的文档'、'找一下X相关的文件'等问题。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词，会匹配文档名称和描述",
                    },
                    "file_type": {
                        "type": "string",
                        "description": "可选的文件类型过滤，如 pdf、docx、md、pptx",
                    },
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_all_documents",
            "description": (
                "列出文档库中的所有文档（支持分页、状态筛选）。"
                "仅返回文档元数据（名称、类型、状态、大小），不含文档正文内容。"
                "用于回答'有哪些文档'、'列出所有文档'等问题。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "可选的状态过滤：draft、published、archived",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量上限，默认20",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_document_detail",
            "description": (
                "获取指定文档的详细信息，包括文件类型、大小、状态、分类、标签、版本等元数据。"
                "不含文档正文内容（正文需通过检索获取）。"
                "用于回答'某个文档的详细信息'、'文档ID为X的文档是什么'等问题。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "integer",
                        "description": "文档ID",
                    },
                },
                "required": ["document_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_library_overview",
            "description": (
                "获取文档库的整体概览统计，包括文档总数、类型分布、状态分布。"
                "用于回答'文档库整体情况'、'各种类型有多少文档'等问题。"
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# ── Tool execution ─────────────────────────────────────────────────

async def execute_tool(db: AsyncSession, tool_name: str, arguments: dict) -> str:
    """Execute a tool by name and return JSON string result."""

    try:
        if tool_name == "search_documents":
            return await _search_documents(db, arguments)

        if tool_name == "list_all_documents":
            return await _list_all_documents(db, arguments)

        if tool_name == "get_document_detail":
            return await _get_document_detail(db, arguments)

        if tool_name == "get_library_overview":
            return await _get_library_overview(db)

        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except Exception as e:
        logger.exception("Tool execution error: %s(%s)", tool_name, arguments)
        return json.dumps(
            {"error": f"工具 {tool_name} 执行时发生内部错误"},
            ensure_ascii=False,
        )


async def _search_documents(db: AsyncSession, args: dict) -> str:
    keyword = (args.get("keyword") or "").strip()
    if not keyword:
        return json.dumps(
            {"found": 0, "message": "请提供搜索关键词。", "documents": []},
            ensure_ascii=False,
        )
    file_type = args.get("file_type")

    tsquery = " | ".join(keyword.split())
    extra = ""
    params: dict = {"q": tsquery}

    if file_type:
        extra = " AND d.file_type = :ft"
        params["ft"] = file_type

    sql = text(
        "SELECT d.id, d.original_name, d.file_type, d.status, "
        "COALESCE(d.description, '') as desc "
        "FROM document d "
        "WHERE d.is_deleted = false "
        "AND to_tsvector('simple', coalesce(d.original_name, '') || ' ' || coalesce(d.description, '')) "
        "@@ to_tsquery('simple', :q)"
        + extra +
        " ORDER BY d.id LIMIT 20"
    )
    result = await db.execute(sql, params)
    rows = result.fetchall()

    if not rows:
        return json.dumps(
            {"found": 0, "message": f"未找到与'{keyword}'相关的文档。", "documents": []},
            ensure_ascii=False,
        )

    docs = [
        {
            "id": r[0],
            "name": r[1],
            "file_type": r[2],
            "status": r[3],
            "description": r[4] or "",
        }
        for r in rows
    ]
    return json.dumps({"found": len(docs), "documents": docs}, ensure_ascii=False)


async def _list_all_documents(db: AsyncSession, args: dict) -> str:
    status = args.get("status")
    try:
        limit = min(int(args.get("limit", 20)), 50)
    except (TypeError, ValueError):
        limit = 20

    extra = ""
    params: dict = {"limit": limit}

    if status:
        extra = " AND status = :status"
        params["status"] = status

    sql = text(
        "SELECT id, original_name, file_type, status, "
        "COALESCE(description, '') as desc, "
        "pg_size_pretty(file_size::bigint) as size "
        "FROM document "
        "WHERE is_deleted = false" + extra +
        " ORDER BY id LIMIT :limit"
    )
    result = await db.execute(sql, params)
    rows = result.fetchall()

    docs = [
        {
            "id": r[0],
            "name": r[1],
            "file_type": r[2],
            "status": r[3],
            "description": r[4],
            "size": r[5],
        }
        for r in rows
    ]

    # Total count
    total_sql = text("SELECT count(*) FROM document WHERE is_deleted = false")
    total = (await db.execute(total_sql)).scalar()

    return json.dumps(
        {"total": total, "returned": len(docs), "documents": docs},
        ensure_ascii=False,
    )


async def _get_document_detail(db: AsyncSession, args: dict) -> str:
    doc_id = args.get("document_id")
    if doc_id is None or not isinstance(doc_id, (int, float)) or int(doc_id) <= 0:
        return json.dumps({"error": "请提供有效的文档ID"}, ensure_ascii=False)
    doc_id = int(doc_id)

    sql = text(
        "SELECT d.id, d.original_name, d.file_type, d.file_size, d.mime_type, "
        "d.status, d.description, d.permission_scope, d.created_at, d.updated_at, "
        "COALESCE(dc.name, '未分类') as category_name, "
        "COALESCE(d.extracted_text IS NOT NULL AND d.extracted_text != '', false) as has_text "
        "FROM document d "
        "LEFT JOIN document_category dc ON d.category_id = dc.id "
        "WHERE d.id = :did AND d.is_deleted = false"
    )
    result = await db.execute(sql, {"did": doc_id})
    row = result.fetchone()

    if not row:
        return json.dumps({"error": f"文档#{doc_id}不存在"}, ensure_ascii=False)

    # Tags
    tag_sql = text(
        "SELECT t.name FROM tag t "
        "JOIN document_tag dt ON t.id = dt.tag_id "
        "WHERE dt.document_id = :did"
    )
    tags_result = await db.execute(tag_sql, {"did": doc_id})
    tags = [r[0] for r in tags_result.fetchall()]

    # Chunk count
    chunk_count = (await db.execute(
        text("SELECT count(*) FROM document_chunk WHERE document_id = :did"),
        {"did": doc_id},
    )).scalar()

    doc = {
        "id": row[0],
        "name": row[1],
        "file_type": row[2],
        "file_size": row[3],
        "mime_type": row[4],
        "status": row[5],
        "description": row[6] or "",
        "permission_scope": row[7],
        "created_at": str(row[8]) if row[8] else None,
        "updated_at": str(row[9]) if row[9] else None,
        "category": row[10],
        "has_extracted_text": bool(row[11]),
        "tags": tags,
        "chunk_count": chunk_count,
    }
    return json.dumps(doc, ensure_ascii=False)


async def _get_library_overview(db: AsyncSession) -> str:
    # Total
    total = (await db.execute(
        text("SELECT count(*) FROM document WHERE is_deleted = false")
    )).scalar()

    # By status
    status_rows = (await db.execute(
        text("SELECT status, count(*) FROM document WHERE is_deleted = false GROUP BY status ORDER BY count(*) DESC")
    )).fetchall()

    # By type
    type_rows = (await db.execute(
        text("SELECT file_type, count(*) FROM document WHERE is_deleted = false GROUP BY file_type ORDER BY count(*) DESC")
    )).fetchall()

    # Has embeddings
    with_embeddings = (await db.execute(
        text("SELECT count(DISTINCT d.id) FROM document d JOIN document_chunk dc ON d.id = dc.document_id WHERE d.is_deleted = false")
    )).scalar()

    return json.dumps(
        {
            "total_documents": total,
            "by_status": [{"status": r[0], "count": r[1]} for r in status_rows],
            "by_type": [{"file_type": r[0], "count": r[1]} for r in type_rows],
            "documents_with_embeddings": with_embeddings,
        },
        ensure_ascii=False,
    )
