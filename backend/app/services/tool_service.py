"""Agent tools: function definitions and execution for document library queries."""

import json
import logging
import re

from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentCategory, Tag
from app.models.ai import DocumentChunk

logger = logging.getLogger(__name__)

# ── Section detection patterns ────────────────────────────────────

# Patterns for Chinese document section headers; ordered by hierarchy
SECTION_PATTERNS = [
    # 附录A / 附录 A / 附录一 / Appendix A
    (re.compile(r'附录\s*[A-Za-z一-鿿]'), "appendix"),
    # 第X章 / 第一章 / 第1章
    (re.compile(r'第[一二三四五六七八九十百\d]+章'), "chapter"),
    # 第X节 / 第一节 / 第1节
    (re.compile(r'第[一二三四五六七八九十百\d]+节'), "section"),
    # 一、/ 二、/ ... (Chinese numbered items)
    (re.compile(r'[一二三四五六七八九十]+、'), "item"),
    # \d+\.\s  (Western numbered items)
    (re.compile(r'\d+\.\s'), "item"),
    # Standalone number at line start (e.g., "6 个人信息保护合规审计内容和方法")
    (re.compile(r'(?:^|\n)\s*\d+\s+(?=\S)', re.MULTILINE), "numeric_heading"),
    # Decimal subsection (e.g., "6.1 个人信息处理活动的合法性")
    (re.compile(r'(?:^|\n)\s*\d+\.\d+\s+(?=\S)', re.MULTILINE), "numeric_subsection"),
]

MAX_CONTENT_CHARS = 8000

# Chinese numeral to digit mapping for translating "第X章" to numeric headers
_CHINESE_TO_DIGIT: dict[str, str] = {
    '一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
    '六': '6', '七': '7', '八': '8', '九': '9', '十': '10',
    '百': '',  # handled via regex, not simple mapping
}


def _extract_chapter_number(section: str) -> str | None:
    """If section looks like '第X章' or '第X节', return the digit string.

    Handles: 第六章→6, 第6章→6, 第十一章→11, 第12章→12
    """
    m = re.match(r'第\s*([一二三四五六七八九十百\d]+)\s*[章节]', section)
    if not m:
        return None
    raw = m.group(1)
    # Already a digit
    if raw.isdigit():
        return raw
    # Simple Chinese numeral: 一→九
    if raw in _CHINESE_TO_DIGIT and _CHINESE_TO_DIGIT[raw]:
        return _CHINESE_TO_DIGIT[raw]
    # Compound: 十一→十一 handled literally, not common in documents
    return None


def _score_match(match: re.Match, full_text: str) -> int:
    """Score a section match by heading-likeness. Higher = more likely a real heading."""
    score = 0
    start = match.start()
    end = match.end()

    # At line start — strong heading indicator.
    # Most patterns include a (?:^|\n) prefix, so match.start() is at the \n.
    # Check whether this match begins at a line boundary.
    if start == 0 or full_text[start] == '\n':
        score += 30
    # Handle rare case where the match starts after a newline (no \n in capture)
    elif start >= 2 and full_text[start - 1:start] == '\n':
        score += 30

    # Multi-line match penalty: real headings have number+title on ONE line.
    # Patterns with (?:^|\n) include the \n prefix — exclude it from the check.
    match_text = full_text[start:end]
    if match_text.startswith('\n'):
        match_text = match_text[1:]
    if '\n' in match_text:
        score -= 40  # Spans multiple lines = list item, not a section heading

    # Prefer heading-style continuations: "6 Title" beats "6.1.4 Subtitle"
    # Check what immediately follows the match on the same line
    next_char = full_text[end] if end < len(full_text) else ''
    if next_char in ' \t':
        score += 8   # Number+space = likely a section heading
    elif next_char.isdigit():
        score -= 8   # "6"→"6.19" or "6.1"→"6.19.1" = sub-subsection reference
    elif next_char in '.．、':
        score -= 5   # Number+dot = likely a subsection reference (6.1.4)

    # Content after match on same line — real headings have substantial text
    line_end = full_text.find('\n', end)
    if line_end == -1:
        line_end = len(full_text)
    rest = full_text[end:line_end]
    meaningful = rest.strip()

    if len(meaningful) >= 10:
        score += 25  # Rich content = real heading
    elif len(meaningful) >= 2:
        score += 10  # Some content
    else:
        score -= 10  # Empty line = probably not a heading

    # Penalize inline cross-references (match preceded by non-newline content on same line).
    # Only check when the match does NOT start at a line boundary — if the match already
    # starts at \n, the heading is at the start of its line, so there's no inline context.
    if start > 0 and full_text[start] != '\n':
        prev_nl = full_text.rfind('\n', 0, start)
        before_on_line = full_text[prev_nl + 1:start].strip()
        if len(before_on_line) > 3:
            score -= 25  # Inline reference like "可参考本文件第六章"

    return score

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
    {
        "type": "function",
        "function": {
            "name": "get_document_content",
            "description": (
                "读取文档的正文内容。可按章节标题定位到指定部分。"
                "用于回答'把某文档的附录X内容导出来'、'查看某文档第X章的内容'、"
                "'这个文档的某个章节讲了什么'等需要直接读取文档正文的问题。"
                "注意：此工具返回的是文档原始全文或指定章节的文本，不是元数据。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "integer",
                        "description": "要读取的文档ID",
                    },
                    "section": {
                        "type": "string",
                        "description": (
                            "可选，要定位的章节标题关键词。"
                            "支持中文章节名（如'附录C'、'第三章'、'第二节'）和数字编号（如'6'、'6.1'）。"
                            "工具会在文档中搜索该关键词，找到后返回从该位置开始的内容。"
                            "如果不指定，返回文档全文开头。"
                            "提示：如果文档使用数字编号（如'6 审计内容'），直接用数字搜索效果更好。"
                        ),
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "返回的最大字符数，默认4000，最大8000。超过会截断并将truncated设为true。",
                    },
                    "offset": {
                        "type": "integer",
                        "description": (
                            "可选，在定位到章节后，再向后跳过的字符数。"
                            "用于分页读取：第一次调用不带offset，如果返回 truncated=true，"
                            "第二次调用设置 offset=上次返回的字符数（或更大）来获取后续内容。"
                            "默认0。"
                        ),
                    },
                },
                "required": ["document_id"],
            },
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

        if tool_name == "get_document_content":
            return await _get_document_content(db, arguments)

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


async def _get_document_content(db: AsyncSession, args: dict) -> str:
    """Read document full text, optionally locating a section by keyword."""
    doc_id = args.get("document_id")
    if doc_id is None or not isinstance(doc_id, (int, float)) or int(doc_id) <= 0:
        return json.dumps({"error": "请提供有效的文档ID"}, ensure_ascii=False)
    doc_id = int(doc_id)

    max_chars = min(
        int(args.get("max_chars", 4000) or 4000),
        MAX_CONTENT_CHARS,
    )
    section = (args.get("section") or "").strip()
    offset = max(0, int(args.get("offset", 0) or 0))

    # 1. Fetch document
    sql = text(
        "SELECT id, original_name, file_type, extracted_text "
        "FROM document WHERE id = :did AND is_deleted = false"
    )
    result = await db.execute(sql, {"did": doc_id})
    row = result.fetchone()
    if not row:
        return json.dumps({"error": f"文档#{doc_id}不存在"}, ensure_ascii=False)

    full_text = row[3]  # extracted_text
    if not full_text:
        return json.dumps(
            {
                "document_id": doc_id,
                "document_name": row[1],
                "has_content": False,
                "message": "此文档尚未提取文本内容。请先在文档详情页执行文本提取操作。",
            },
            ensure_ascii=False,
        )

    # 2. Locate section if specified
    start_pos = 0
    section_found = None
    total_chars = len(full_text)

    if section:
        all_matches: list[tuple[re.Match, int]] = []  # (match, score)

        # Build a fuzzy regex: allow optional whitespace between every char of the keyword
        fuzzy_parts = []
        for ch in section:
            if ch.strip():
                fuzzy_parts.append(re.escape(ch))
            else:
                fuzzy_parts.append(r'\s*')
        fuzzy_str = r'\s*'.join(fuzzy_parts)
        fuzzy_pattern = r'(?:(?:^|\n)\s*' + fuzzy_str + r'\b)'
        alt_pattern = r'(?:(?:^|\n)\s*' + fuzzy_str + r')'

        for p in [fuzzy_pattern, alt_pattern]:
            try:
                for m in re.finditer(p, full_text, re.IGNORECASE):
                    all_matches.append((m, _score_match(m, full_text)))
            except re.error:
                continue

        # Also try SECTION_PATTERNS (not just as fallback — documents may use different conventions)
        for pat, _kind in SECTION_PATTERNS:
            for m in pat.finditer(full_text):
                matched_norm = re.sub(r'\s+', '', m.group())
                section_norm = re.sub(r'\s+', '', section)
                if section_norm.lower() in matched_norm.lower():
                    all_matches.append((m, _score_match(m, full_text)))

        # Chinese chapter → numeric alternative (e.g., "第六章" → "6 ")
        # Also handle bare numeric sections (e.g., "6", "6.1")
        chapter_num = _extract_chapter_number(section)
        num_pats = []
        if chapter_num:
            num_pats = [
                re.compile(rf'(?:^|\n)\s*{chapter_num}\s+(?=\S)', re.MULTILINE),
                re.compile(rf'(?:^|\n)\s*{chapter_num}\.\d+\s+(?=\S)', re.MULTILINE),
                re.compile(rf'(?:^|\n)\s*{chapter_num}\.\s+(?=\S)', re.MULTILINE),
            ]
        else:
            bare_match = re.match(r'^(\d+(?:\.\d+)?)\s*$', section)
            if bare_match:
                num = bare_match.group(1)
                num_pats = [
                    re.compile(rf'(?:^|\n)\s*{re.escape(num)}\s+(?=\S)', re.MULTILINE),
                ]
        for pat in num_pats:
            for m in pat.finditer(full_text):
                all_matches.append((m, _score_match(m, full_text)))

        # Fallback: strip all whitespace, substring search
        if not all_matches:
            text_no_ws = re.sub(r'\s+', '', full_text)
            section_no_ws = re.sub(r'\s+', '', section)
            idx = text_no_ws.lower().find(section_no_ws.lower())
            if idx >= 0:
                orig_pos = 0
                no_ws_pos = 0
                for ch in full_text:
                    if no_ws_pos >= idx:
                        break
                    if not ch.isspace():
                        no_ws_pos += 1
                    orig_pos += 1
                line_start = full_text.rfind("\n", 0, orig_pos) + 1
                start_pos = line_start
                section_found = full_text[line_start:full_text.find("\n", orig_pos)].strip()[:80]

        if all_matches:
            # Pick the best match by score, breaking ties with later position (content > TOC)
            best_match, best_score = max(all_matches, key=lambda x: (x[1], x[0].start()))
            start_pos = best_match.start()
            section_found = best_match.group().strip()

    # 3. Apply offset (for pagination after initial section match)
    start_pos = min(start_pos + offset, total_chars)

    # 4. Extract text from start_pos
    content = full_text[start_pos:start_pos + max_chars]
    truncated = (start_pos + max_chars) < total_chars

    # 5. Build hint for section-match failures
    hint = None
    if section and start_pos == 0:
        hint = (
            f"未找到与'{section}'匹配的章节标题。"
            "请尝试更简洁的关键词（如'6'、'6.1'），或先用 get_document_content 不带 section 参数浏览目录结构。"
        )

    # 6. Build response
    return json.dumps(
        {
            "document_id": doc_id,
            "document_name": row[1],
            "file_type": row[2],
            "total_chars": total_chars,
            "section_requested": section or None,
            "section_found": section_found,
            "start_offset": start_pos,
            "returned_chars": len(content),
            "truncated": truncated,
            "hint": hint,
            "content": content,
        },
        ensure_ascii=False,
    )
