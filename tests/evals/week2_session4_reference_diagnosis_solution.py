"""2주차 세션 4 reference 전략과 실패 진단 실습의 참고 답안.

학생용 파일의 TODO를 모두 완성하고 작성 템플릿에 자신의 원칙을 기록한 뒤
비교한다. blind spot 문장은 같은 의미를 명확하게 표현했다면 달라도 된다.

    .venv/bin/python \
        tests/evals/week2_session4_reference_diagnosis_solution.py --check
    .venv/bin/python \
        tests/evals/week2_session4_reference_diagnosis_solution.py \
        --show-diagnosis
    .venv/bin/python \
        tests/evals/week2_session4_reference_diagnosis_solution.py \
        --simulate-feedback-loop

모든 명령은 LLM judge와 외부 API를 호출하지 않는다.
"""

from __future__ import annotations

import argparse
from typing import Final

from week2_session4_reference_diagnosis_exercise import (
    DiagnosticRoute,
    FieldRole,
    ProductionFailure,
    ReferenceStrategy,
    ReviewedGolden,
    check_materials,
    print_diagnosis_table,
    simulate_feedback_loop,
)


FIELD_ROLES: Final[dict[str, FieldRole]] = {
    "input": "request",
    "actual_output": "runtime_observation",
    "expected_output": "reviewed_reference",
    "context": "reviewed_reference",
    "retrieval_context": "runtime_observation",
    "expected_tools": "reviewed_reference",
    "tools_called": "runtime_observation",
}

REFERENCE_STRATEGIES: Final[dict[str, ReferenceStrategy]] = {
    "development_regression": "reference_based",
    "unreviewed_production_sample": "referenceless_then_review",
    "human_reviewed_production_failure": "promote_to_regression",
}

DIAGNOSTIC_ROUTES: Final = {
    "answer_relevancy": DiagnosticRoute(
        metric_name="Answer Relevancy",
        required_fields=frozenset({"input", "actual_output"}),
        reference_mode="referenceless",
        suspected_component="generator",
        blind_spot="답변의 주장이 검색 근거에 충실한지는 알 수 없다.",
    ),
    "faithfulness": DiagnosticRoute(
        metric_name="Faithfulness",
        required_fields=frozenset(
            {"input", "actual_output", "retrieval_context"}
        ),
        reference_mode="referenceless",
        suspected_component="generator_grounding",
        blind_spot="검색된 근거가 질문에 필요하고 충분한지는 알 수 없다.",
    ),
    "contextual_relevancy": DiagnosticRoute(
        metric_name="Contextual Relevancy",
        required_fields=frozenset({"input", "retrieval_context"}),
        reference_mode="referenceless",
        suspected_component="retriever",
        blind_spot="필요한 근거의 누락이나 최종 답변의 품질은 알 수 없다.",
    ),
    "refund_completeness": DiagnosticRoute(
        metric_name="Refund Completeness GEval",
        required_fields=frozenset({"actual_output", "expected_output"}),
        reference_mode="reference_based",
        suspected_component="answer_composition",
        blind_spot="불완전성의 원인이 retriever인지 직접 확정할 수 없다.",
    ),
}


def promote_to_reviewed_golden(failure: ProductionFailure) -> ReviewedGolden:
    """사람 검토가 승인된 표본만 정적 reference로 승격한다."""
    expected_output = (failure.reviewed_expected_output or "").strip()
    if failure.review_status != "approved" or not expected_output:
        raise ValueError("승인된 reviewed_expected_output이 필요합니다.")
    return ReviewedGolden(
        source_sample_id=failure.sample_id,
        input=failure.input,
        expected_output=expected_output,
    )


def check_solution() -> None:
    check_materials(
        field_roles=FIELD_ROLES,
        strategies=REFERENCE_STRATEGIES,
        routes=DIAGNOSTIC_ROUTES,
        promoter=promote_to_reviewed_golden,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="2주차 세션 4 참고 답안")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="API 호출 없는 검사")
    mode.add_argument("--show-diagnosis", action="store_true")
    mode.add_argument("--simulate-feedback-loop", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    check_solution()
    if args.show_diagnosis:
        print_diagnosis_table(DIAGNOSTIC_ROUTES)
    elif args.simulate_feedback_loop:
        simulate_feedback_loop(
            REFERENCE_STRATEGIES,
            DIAGNOSTIC_ROUTES,
            promote_to_reviewed_golden,
        )
