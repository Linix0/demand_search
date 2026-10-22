"""Import persisted models so Alembic and metadata discovery see every table."""

from app.models.pain_point import (
    Annotation,
    EvidenceRole,
    EvidenceType,
    ManualVerificationStatus,
    PainPoint,
    PainPointEvidence,
    PainPointScore,
    PainPointStatus,
    QuoteMatchStatus,
    ScoreType,
)
from app.models.provider import ProviderHealth, SourceProvider
from app.models.research import AuditLog, QueryStatus, ResearchJobLog, SearchQuery
from app.models.research_job import JobStage, JobStatus, ResearchJob
from app.models.research_job_source import ResearchJobSource
from app.models.source import (
    ContentCompleteness,
    RetrievalMethod,
    SourceItem,
    SourceTrustTier,
    UrlStatus,
)
from app.models.taxonomy import TaxonomyCategory, TaxonomyTag
from app.models.workspace import Workspace

__all__ = [
    "Annotation",
    "AuditLog",
    "ContentCompleteness",
    "EvidenceRole",
    "EvidenceType",
    "JobStage",
    "JobStatus",
    "ManualVerificationStatus",
    "PainPoint",
    "PainPointEvidence",
    "PainPointScore",
    "PainPointStatus",
    "ProviderHealth",
    "QueryStatus",
    "QuoteMatchStatus",
    "ResearchJob",
    "ResearchJobLog",
    "ResearchJobSource",
    "RetrievalMethod",
    "ScoreType",
    "SearchQuery",
    "SourceItem",
    "SourceProvider",
    "SourceTrustTier",
    "TaxonomyCategory",
    "TaxonomyTag",
    "UrlStatus",
    "Workspace",
]
