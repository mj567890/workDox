"""Seed preset task templates on first startup."""

from sqlalchemy import select, func

PRESET_TEMPLATES = [
    {
        "name": "公开招标",
        "category": "采购",
        "is_system": True,
        "description": "公开招标采购流程 — 6 个阶段",
        "stages": [
            {"name": "预算与计划", "order": 1, "slots": [
                {"name": "采购预算批复", "is_required": True, "file_type_hints": ["pdf", "docx"]},
                {"name": "采购计划表", "is_required": True, "file_type_hints": ["xlsx", "docx"]},
                {"name": "采购需求书", "is_required": True, "file_type_hints": ["docx", "pdf"]},
            ]},
            {"name": "审计与立项", "order": 2, "slots": [
                {"name": "审计意见书", "is_required": True, "file_type_hints": ["pdf"]},
                {"name": "立项批复文件", "is_required": True, "file_type_hints": ["pdf", "docx"]},
                {"name": "可行性论证报告", "is_required": False, "file_type_hints": ["docx"]},
            ]},
            {"name": "招标实施", "order": 3, "slots": [
                {"name": "招标公告", "is_required": True, "file_type_hints": ["pdf", "docx"]},
                {"name": "招标文件", "is_required": True, "file_type_hints": ["docx", "pdf"]},
                {"name": "投标文件汇总", "is_required": True, "file_type_hints": ["zip"]},
                {"name": "评标报告", "is_required": True, "file_type_hints": ["docx", "pdf"]},
                {"name": "中标通知书", "is_required": True, "file_type_hints": ["pdf"]},
            ]},
            {"name": "合同与实施", "order": 4, "slots": [
                {"name": "合同文本", "is_required": True, "file_type_hints": ["docx", "pdf"]},
                {"name": "合同审批表", "is_required": True, "file_type_hints": ["pdf"]},
                {"name": "实施进度报告", "is_required": False, "file_type_hints": ["docx"]},
            ]},
            {"name": "验收", "order": 5, "slots": [
                {"name": "验收申请", "is_required": True, "file_type_hints": ["docx"]},
                {"name": "验收报告", "is_required": True, "file_type_hints": ["pdf", "docx"]},
                {"name": "验收清单", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
            {"name": "请款与归档", "order": 6, "slots": [
                {"name": "发票", "is_required": True, "file_type_hints": ["pdf", "jpg"]},
                {"name": "付款申请单", "is_required": True, "file_type_hints": ["docx", "pdf"]},
                {"name": "归档材料清单", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
        ]
    },
    {
        "name": "邀请招标",
        "category": "采购",
        "is_system": True,
        "description": "邀请招标采购流程 — 6 个阶段",
        "stages": [
            {"name": "预算与计划", "order": 1, "slots": [
                {"name": "采购预算批复", "is_required": True, "file_type_hints": ["pdf", "docx"]},
                {"name": "采购计划表", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
            {"name": "审计与立项", "order": 2, "slots": [
                {"name": "审计意见书", "is_required": True, "file_type_hints": ["pdf"]},
                {"name": "立项批复文件", "is_required": True, "file_type_hints": ["pdf"]},
            ]},
            {"name": "招标实施", "order": 3, "slots": [
                {"name": "邀请函", "is_required": True, "file_type_hints": ["docx", "pdf"]},
                {"name": "招标文件", "is_required": True, "file_type_hints": ["docx"]},
                {"name": "投标文件汇总", "is_required": True, "file_type_hints": ["zip"]},
                {"name": "评标报告", "is_required": True, "file_type_hints": ["docx"]},
                {"name": "中标通知书", "is_required": True, "file_type_hints": ["pdf"]},
            ]},
            {"name": "合同与实施", "order": 4, "slots": [
                {"name": "合同文本", "is_required": True, "file_type_hints": ["docx", "pdf"]},
                {"name": "合同审批表", "is_required": True, "file_type_hints": ["pdf"]},
            ]},
            {"name": "验收", "order": 5, "slots": [
                {"name": "验收申请", "is_required": True, "file_type_hints": ["docx"]},
                {"name": "验收报告", "is_required": True, "file_type_hints": ["pdf"]},
                {"name": "验收清单", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
            {"name": "请款与归档", "order": 6, "slots": [
                {"name": "发票", "is_required": True, "file_type_hints": ["pdf", "jpg"]},
                {"name": "付款申请单", "is_required": True, "file_type_hints": ["docx"]},
                {"name": "归档材料清单", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
        ]
    },
    {
        "name": "竞争性谈判",
        "category": "采购",
        "is_system": True,
        "description": "竞争性谈判采购流程 — 5 个阶段",
        "stages": [
            {"name": "预算与立项", "order": 1, "slots": [
                {"name": "采购预算", "is_required": True, "file_type_hints": ["xlsx", "pdf"]},
                {"name": "立项批复", "is_required": True, "file_type_hints": ["pdf"]},
            ]},
            {"name": "谈判准备", "order": 2, "slots": [
                {"name": "谈判文件", "is_required": True, "file_type_hints": ["docx"]},
                {"name": "邀请供应商名单", "is_required": True, "file_type_hints": ["xlsx"]},
                {"name": "谈判公告", "is_required": False, "file_type_hints": ["pdf"]},
            ]},
            {"name": "谈判实施", "order": 3, "slots": [
                {"name": "谈判记录", "is_required": True, "file_type_hints": ["docx"]},
                {"name": "评审意见", "is_required": True, "file_type_hints": ["docx", "pdf"]},
                {"name": "成交通知书", "is_required": True, "file_type_hints": ["pdf"]},
            ]},
            {"name": "合同与验收", "order": 4, "slots": [
                {"name": "合同文本", "is_required": True, "file_type_hints": ["docx", "pdf"]},
                {"name": "验收报告", "is_required": True, "file_type_hints": ["pdf"]},
                {"name": "发票", "is_required": True, "file_type_hints": ["pdf", "jpg"]},
            ]},
            {"name": "归档", "order": 5, "slots": [
                {"name": "归档清单", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
        ]
    },
    {
        "name": "询价",
        "category": "采购",
        "is_system": True,
        "description": "询价采购流程 — 4 个阶段",
        "stages": [
            {"name": "预算", "order": 1, "slots": [
                {"name": "采购预算", "is_required": True, "file_type_hints": ["xlsx", "pdf"]},
                {"name": "采购计划", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
            {"name": "询价", "order": 2, "slots": [
                {"name": "询价函", "is_required": True, "file_type_hints": ["docx", "pdf"]},
                {"name": "报价汇总表", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
            {"name": "实施", "order": 3, "slots": [
                {"name": "合同文本", "is_required": True, "file_type_hints": ["docx", "pdf"]},
                {"name": "发票", "is_required": True, "file_type_hints": ["pdf"]},
            ]},
            {"name": "验收", "order": 4, "slots": [
                {"name": "验收报告", "is_required": True, "file_type_hints": ["pdf"]},
                {"name": "归档清单", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
        ]
    },
    {
        "name": "单一来源",
        "category": "采购",
        "is_system": True,
        "description": "单一来源采购流程 — 4 个阶段",
        "stages": [
            {"name": "论证", "order": 1, "slots": [
                {"name": "单一来源论证报告", "is_required": True, "file_type_hints": ["docx", "pdf"]},
                {"name": "采购预算", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
            {"name": "审批", "order": 2, "slots": [
                {"name": "审批表", "is_required": True, "file_type_hints": ["pdf"]},
                {"name": "采购文件", "is_required": True, "file_type_hints": ["docx"]},
            ]},
            {"name": "合同与实施", "order": 3, "slots": [
                {"name": "合同文本", "is_required": True, "file_type_hints": ["docx", "pdf"]},
                {"name": "发票", "is_required": True, "file_type_hints": ["pdf"]},
            ]},
            {"name": "归档", "order": 4, "slots": [
                {"name": "归档清单", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
        ]
    },
    {
        "name": "协议供货",
        "category": "采购",
        "is_system": True,
        "description": "协议供货采购流程 — 4 个阶段",
        "stages": [
            {"name": "预算", "order": 1, "slots": [
                {"name": "采购预算", "is_required": True, "file_type_hints": ["xlsx"]},
                {"name": "协议供货目录", "is_required": True, "file_type_hints": ["pdf"]},
            ]},
            {"name": "下单", "order": 2, "slots": [
                {"name": "订单确认单", "is_required": True, "file_type_hints": ["pdf", "docx"]},
            ]},
            {"name": "验收", "order": 3, "slots": [
                {"name": "验收报告", "is_required": True, "file_type_hints": ["pdf"]},
                {"name": "发票", "is_required": True, "file_type_hints": ["pdf"]},
            ]},
            {"name": "归档", "order": 4, "slots": [
                {"name": "归档清单", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
        ]
    },
    {
        "name": "科研项目",
        "category": "通用",
        "is_system": True,
        "description": "科研项目管理流程 — 4 个阶段",
        "stages": [
            {"name": "立项", "order": 1, "slots": [
                {"name": "项目申请书", "is_required": True, "file_type_hints": ["docx"]},
                {"name": "立项批复", "is_required": True, "file_type_hints": ["pdf"]},
                {"name": "经费预算表", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
            {"name": "研究", "order": 2, "slots": [
                {"name": "中期报告", "is_required": True, "file_type_hints": ["docx", "pdf"]},
                {"name": "实验数据", "is_required": False, "file_type_hints": ["xlsx", "zip"]},
            ]},
            {"name": "结题", "order": 3, "slots": [
                {"name": "结题报告", "is_required": True, "file_type_hints": ["docx", "pdf"]},
                {"name": "成果材料", "is_required": True, "file_type_hints": ["zip", "pdf"]},
                {"name": "经费决算表", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
            {"name": "归档", "order": 4, "slots": [
                {"name": "归档清单", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
        ]
    },
    {
        "name": "人事入职",
        "category": "通用",
        "is_system": True,
        "description": "人事入职管理流程 — 4 个阶段",
        "stages": [
            {"name": "准备", "order": 1, "slots": [
                {"name": "录用通知", "is_required": True, "file_type_hints": ["pdf"]},
                {"name": "入职材料清单", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
            {"name": "入职", "order": 2, "slots": [
                {"name": "身份证复印件", "is_required": True, "file_type_hints": ["pdf", "jpg"]},
                {"name": "学历学位证书", "is_required": True, "file_type_hints": ["pdf", "jpg"]},
                {"name": "劳动合同", "is_required": True, "file_type_hints": ["pdf"]},
                {"name": "社保公积金表", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
            {"name": "试用", "order": 3, "slots": [
                {"name": "试用期考核表", "is_required": True, "file_type_hints": ["docx"]},
                {"name": "转正申请", "is_required": True, "file_type_hints": ["docx", "pdf"]},
            ]},
            {"name": "转正", "order": 4, "slots": [
                {"name": "转正审批表", "is_required": True, "file_type_hints": ["pdf"]},
                {"name": "归档清单", "is_required": True, "file_type_hints": ["xlsx"]},
            ]},
        ]
    },
    {
        "name": "自定义空白",
        "category": "通用",
        "is_system": True,
        "description": "空白模板，用户自由编排阶段和文档槽位",
        "stages": []
    },
]


async def seed_templates(db) -> int:
    """Seed preset templates if none exist. Returns count of created templates."""
    from app.models.task import TaskTemplate
    result = await db.execute(select(func.count(TaskTemplate.id)))
    count = result.scalar() or 0
    if count > 0:
        return 0

    from app.services.task_management_service import TaskTemplateService
    service = TaskTemplateService()
    created = 0
    for tpl_data in PRESET_TEMPLATES:
        await service.create_template(db, tpl_data)
        created += 1
    return created
