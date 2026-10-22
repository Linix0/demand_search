"""Default taxonomy initialization and read helpers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.taxonomy import TaxonomyCategory, TaxonomyTag

DEFAULT_CATEGORIES = (
    ("developer_tools", "开发者与 IT 工具", "编程、调试、测试、CI/CD、代码审查、IDE、DevOps"),
    ("ai_workflow", "AI / Agent 工作流", "Agent 可靠性、RAG、模型评估、知识库与成本控制"),
    ("enterprise_ops", "企业办公与业务流程", "审批、CRM、ERP、表格、内部流程、报表与协同"),
    ("content_creation", "内容创作与运营", "文章、视频、图片、跨平台发布与素材管理"),
    ("marketing_sales", "营销与销售", "获客、SEO、客户支持、潜客管理与运营自动化"),
    ("ecommerce", "电商与商家运营", "商品信息、库存、订单、客服与售后"),
    ("education_learning", "教育与个人学习", "学习计划、练习、反馈、知识管理与培训工具"),
    ("personal_productivity", "个人效率", "任务管理、文件处理、个人知识库与跨设备协作"),
    ("finance_admin", "财务与行政", "票据、对账、报销、预算与合规文档"),
    ("customer_support", "客服与客户成功", "工单归类、重复问题、质检与客户反馈"),
    ("creative_entertainment", "创意与娱乐", "游戏创作、互动叙事、创作工具与社区体验"),
    ("industry_specific", "行业垂直需求", "医疗、法律、制造、物流等受监管行业需求"),
    ("other", "其他", "暂不能归类的需求"),
)

DEFAULT_TAGS = (
    ("repetitive_manual_work", "重复劳动", "pain_type"),
    ("workflow_fragmentation", "工具割裂", "pain_type"),
    ("high_cost", "成本过高", "pain_type"),
    ("low_quality", "质量不佳", "pain_type"),
    ("slow_process", "流程过慢", "pain_type"),
    ("integration_gap", "集成缺口", "pain_type"),
    ("missing_feature", "缺少功能", "pain_type"),
    ("complex_setup", "配置复杂", "pain_type"),
    ("reliability", "不稳定", "pain_type"),
    ("data_access", "数据获取", "pain_type"),
    ("collaboration", "协作", "pain_type"),
    ("compliance", "合规压力", "pain_type"),
    ("accessibility", "易用性/无障碍", "pain_type"),
    ("privacy_security", "隐私安全", "pain_type"),
    ("indie_developer", "独立开发者", "user_type"),
    ("developer_team", "开发团队", "user_type"),
    ("small_business", "小微企业", "user_type"),
    ("enterprise", "企业", "user_type"),
    ("spreadsheet", "电子表格", "workaround"),
    ("manual_copy_paste", "手工复制粘贴", "workaround"),
    ("multiple_tools", "多工具拼凑", "workaround"),
    ("unknown", "未知", "workaround"),
)


def ensure_taxonomy(session: Session) -> None:
    """Idempotently insert the default taxonomy as editable database rows."""

    existing_codes = set(session.scalars(select(TaxonomyCategory.code)))
    for order, (code, name, description) in enumerate(DEFAULT_CATEGORIES):
        if code not in existing_codes:
            session.add(
                TaxonomyCategory(
                    code=code,
                    name=name,
                    description=description,
                    sort_order=order,
                    enabled=True,
                    is_system=True,
                )
            )

    existing_tags = set(session.scalars(select(TaxonomyTag.code)))
    for code, name, group in DEFAULT_TAGS:
        if code not in existing_tags:
            session.add(TaxonomyTag(code=code, name=name, tag_group=group, enabled=True))


def list_categories(session: Session) -> list[TaxonomyCategory]:
    return list(
        session.scalars(
            select(TaxonomyCategory)
            .where(TaxonomyCategory.enabled.is_(True))
            .order_by(TaxonomyCategory.sort_order, TaxonomyCategory.code)
        )
    )


def list_tags(session: Session) -> list[TaxonomyTag]:
    return list(
        session.scalars(
            select(TaxonomyTag)
            .where(TaxonomyTag.enabled.is_(True))
            .order_by(TaxonomyTag.tag_group, TaxonomyTag.code)
        )
    )
