"""3주차 세션 2 reviewed Golden 설계 실습의 참고 답안.

학생용 파일의 ``--check``를 통과시킨 뒤 비교한다.

    .venv/bin/python \
        tests/evals/week3_session2_golden_design_solution.py --check
    .venv/bin/python \
        tests/evals/week3_session2_golden_design_solution.py --show-coverage

이 파일도 LLM judge나 외부 API를 호출하지 않는다.
"""

from __future__ import annotations

import argparse
from typing import Final

from week3_session2_golden_design_exercise import (
    COVERAGE_TARGETS as EXERCISE_COVERAGE_TARGETS,
    GOLDEN_PLAN as EXERCISE_GOLDEN_PLAN,
    GoldenMetadata,
    ReferenceCandidate,
    ReviewedGolden,
    RUNTIME_FIELDS,
    check_materials,
    show_coverage,
)


GOLDEN_PLAN: Final = {
    "refund-known-bug-001": GoldenMetadata(
        case_id="refund-known-bug-001",
        category="known_bug",
        protected_risk="unsupported_refund_window",
        suspected_component="generator_grounding",
        suite="smoke",
        review_status="approved",
        bug_status="fixed",
    ),
    "refund-normal-001": GoldenMetadata(
        case_id="refund-normal-001",
        category="normal",
        protected_risk="wrong_refund_channel",
        suspected_component="generator",
        suite="smoke",
        review_status="approved",
        bug_status="not_applicable",
    ),
    "refund-boundary-001": GoldenMetadata(
        case_id="refund-boundary-001",
        category="boundary",
        protected_risk="exclusive_thirty_day_boundary",
        suspected_component="generator_grounding",
        suite="smoke",
        review_status="approved",
        bug_status="not_applicable",
    ),
    "refund-unknown-001": GoldenMetadata(
        case_id="refund-unknown-001",
        category="unknown_or_invalid_input",
        protected_risk="invented_unknown_policy",
        suspected_component="generator",
        suite="smoke",
        review_status="approved",
        bug_status="not_applicable",
    ),
    "refund-safety-001": GoldenMetadata(
        case_id="refund-safety-001",
        category="safety_policy",
        protected_risk="unnecessary_payment_credentials",
        suspected_component="generator",
        suite="smoke",
        review_status="approved",
        bug_status="not_applicable",
    ),
    "refund-normal-002": GoldenMetadata(
        case_id="refund-normal-002",
        category="normal",
        protected_risk="missed_refund_window_paraphrase",
        suspected_component="retriever",
        suite="full",
        review_status="approved",
        bug_status="not_applicable",
    ),
    "refund-boundary-002": GoldenMetadata(
        case_id="refund-boundary-002",
        category="boundary",
        protected_risk="eligibility_claim_without_purchase_date",
        suspected_component="answer_composition",
        suite="full",
        review_status="approved",
        bug_status="not_applicable",
    ),
    "refund-boundary-003": GoldenMetadata(
        case_id="refund-boundary-003",
        category="boundary",
        protected_risk="incomplete_multi_intent_answer",
        suspected_component="answer_composition",
        suite="full",
        review_status="approved",
        bug_status="not_applicable",
    ),
    "refund-known-bug-002": GoldenMetadata(
        case_id="refund-known-bug-002",
        category="known_bug",
        protected_risk="off_topic_shipping_claim",
        suspected_component="generator",
        suite="full",
        review_status="approved",
        bug_status="fixed",
    ),
    "refund-invalid-001": GoldenMetadata(
        case_id="refund-invalid-001",
        category="unknown_or_invalid_input",
        protected_risk="invented_answer_for_empty_input",
        suspected_component="generator",
        suite="full",
        review_status="approved",
        bug_status="not_applicable",
    ),
}

COVERAGE_TARGETS: Final = {
    "normal": 6,
    "boundary": 4,
    "known_bug": 4,
    "safety_policy": 3,
    "unknown_or_invalid_input": 3,
}


def promote_to_reviewed_golden(
    candidate: ReferenceCandidate,
    metadata: GoldenMetadata,
) -> ReviewedGolden:
    if candidate.review_status != "approved" or metadata.review_status != "approved":
        raise ValueError("candidate와 metadata가 모두 approved여야 합니다.")

    mixed_runtime_fields = candidate.stored_runtime_fields & RUNTIME_FIELDS
    if mixed_runtime_fields:
        raise ValueError(
            f"Golden에 runtime field를 저장할 수 없습니다: "
            f"{sorted(mixed_runtime_fields)}"
        )

    return ReviewedGolden(
        input=candidate.input,
        expected_output=candidate.expected_output,
        context=candidate.context,
        metadata=metadata,
        source_sample_id=candidate.source_sample_id,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="3주차 세션 2 참고 답안")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="API 호출 없는 검사")
    mode.add_argument("--show-coverage", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    goldens = check_materials(
        GOLDEN_PLAN,
        COVERAGE_TARGETS,
        promote_to_reviewed_golden,
    )
    if args.show_coverage:
        show_coverage(goldens, COVERAGE_TARGETS)

    # 학생용 상수를 실수로 답안에서 검사하지 않도록 이름을 명시적으로 남긴다.
    assert EXERCISE_GOLDEN_PLAN is not GOLDEN_PLAN
    assert EXERCISE_COVERAGE_TARGETS is not COVERAGE_TARGETS
