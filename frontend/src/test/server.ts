import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const API = "http://127.0.0.1:8000";

const category = {
  id: "00000000-0000-0000-0000-000000000010",
  code: "enterprise_ops",
  name: "企业运营",
  description: "内部流程与运营痛点",
};

const painPointSummary = {
  id: "00000000-0000-0000-0000-000000000001",
  canonical_statement: "财务团队每月手工合并多个表格，容易出错且无法及时完成关账。",
  user_segment: "中小企业财务团队",
  context: "月度关账与跨系统对账",
  status: "needs_review",
  category,
  evidence_confidence_score: 72.5,
  commercial_opportunity_score: 64,
  coverage_score: 38,
  score_version: "scores-v1",
  distinct_source_count: 3,
  payment_signal_summary: "已为电子表格自动化工具付费",
  created_from_job_id: "00000000-0000-0000-0000-000000000020",
  created_at: "2026-10-20T02:00:00Z",
  updated_at: "2026-10-21T03:30:00Z",
};

const painPointDetail = {
  ...painPointSummary,
  problem_detail: "团队需要从多个系统导出 CSV，再逐列核对并手工修正差异。",
  current_workaround: "使用共享电子表格和人工抽查。",
  current_solution_gap: "现有工具无法保留跨系统审计轨迹。",
  pain_type_tags: ["repetitive_manual_work"],
  distinct_thread_count: 2,
  root_cause_hypotheses: [],
  competitor_summary: [],
  validation_next_step: "访谈三位财务负责人并记录关账耗时。",
  merged_into_id: null,
  last_evidence_at: "2026-10-21T03:30:00Z",
  last_reviewed_at: null,
  evidences: [
    {
      id: "00000000-0000-0000-0000-000000000101",
      source_item_id: "00000000-0000-0000-0000-000000000201",
      evidence_quote: "We spend two days every month reconciling exports by hand.",
      evidence_quote_normalized: "we spend two days every month reconciling exports by hand",
      quote_match_status: "exact_match",
      evidence_type: "first_person_pain",
      evidence_role: "supporting",
      evidence_strength_score: 82,
      source_url_snapshot: "https://example.com/issues/1",
      target_url: "https://example.com/issues/1#comment",
      related_target_urls: [],
      source_published_at_snapshot: "2026-10-01T00:00:00Z",
      collected_at_snapshot: "2026-10-20T02:00:00Z",
      author_independence_key: "abc123",
      manual_verification_status: "unreviewed",
      manual_note: "",
      source_name: "Mock Search",
      source_title: "Monthly reconciliation is manual",
      content_completeness: "full_public_content",
      retrieval_method: "search_api",
      source_trust_tier: "A_primary_user_report",
    },
    {
      id: "00000000-0000-0000-0000-000000000102",
      source_item_id: "00000000-0000-0000-0000-000000000202",
      evidence_quote: "Export summaries are unreadable.",
      evidence_quote_normalized: "export summaries are unreadable",
      quote_match_status: "snippet_only",
      evidence_type: "other",
      evidence_role: "context",
      evidence_strength_score: 40,
      source_url_snapshot: "javascript:alert(1)",
      target_url: "",
      related_target_urls: [],
      source_published_at_snapshot: null,
      collected_at_snapshot: "2026-10-20T03:00:00Z",
      author_independence_key: null,
      manual_verification_status: "unreviewed",
      manual_note: "",
      source_name: "",
      source_title: "",
      content_completeness: "snippet_only",
      retrieval_method: "search_api",
      source_trust_tier: "D_search_snippet",
    },
  ],
  scores: [
    {
      id: "00000000-0000-0000-0000-000000000301",
      score_type: "evidence",
      scoring_version: "scores-v1",
      total_score: 72.5,
      dimension_scores: [
        {
          code: "source_traceability",
          weight: 0.2,
          raw_score: 4,
          rationale: "来源可以打开并定位到具体评论。",
        },
      ],
      calculation_details: {},
      rule_adjustments: [],
      scored_at: "2026-10-21T03:30:00Z",
    },
    {
      id: "00000000-0000-0000-0000-000000000302",
      score_type: "commercial",
      scoring_version: "scores-v1",
      total_score: 64,
      dimension_scores: [],
      calculation_details: {},
      rule_adjustments: [],
      scored_at: "2026-10-21T03:30:00Z",
    },
    {
      id: "00000000-0000-0000-0000-000000000303",
      score_type: "coverage",
      scoring_version: "scores-v1",
      total_score: 38,
      dimension_scores: [],
      calculation_details: {},
      rule_adjustments: [],
      scored_at: "2026-10-21T03:30:00Z",
    },
  ],
};

export const handlers = [
  http.get(`${API}/api/v1/pain-points`, () =>
    HttpResponse.json({
      items: [painPointSummary],
      page: 1,
      page_size: 20,
      total: 1,
      coverage_warning: "Sample coverage is low; do not over-interpret these scores.",
    }),
  ),
  http.get(`${API}/api/v1/pain-points/:painPointId`, () => HttpResponse.json(painPointDetail)),
  http.get(`${API}/api/v1/taxonomy/categories`, () =>
    HttpResponse.json({ items: [category] }),
  ),
  http.get(`${API}/api/v1/taxonomy/tags`, () =>
    HttpResponse.json({
      items: [
        {
          id: "00000000-0000-0000-0000-000000000011",
          code: "repetitive_manual_work",
          name: "重复手工工作",
          tag_group: "pain_type",
        },
      ],
    }),
  ),
];

export const server = setupServer(...handlers);
