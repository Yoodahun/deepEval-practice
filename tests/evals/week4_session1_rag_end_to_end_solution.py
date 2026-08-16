"""4주차 세션 1 RAG end-to-end 실습의 참고 답안.

학생용 파일의 TODO 1~4를 완성한 뒤 비교한다. ``--check``는 API를 호출하지
않는다. ``--run``은 smoke 5개와 의도적 실패 사례를 실제 judge로 평가한다.

    .venv/bin/python -m \
        tests.evals.week4_session1_rag_end_to_end_solution --check

    .venv/bin/python -m \
        tests.evals.week4_session1_rag_end_to_end_solution --run
"""

from __future__ import annotations

import argparse
from typing import Sequence

from deepeval.dataset import Golden
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase, SingleTurnParams

from app.refund_support import answer_refund_question
from evals.metrics.refund_completeness import make_refund_completeness_metric
from tests.evals.test_week4_session1_rag_end_to_end import (
    ALL_GOLDENS,
    INTENTIONAL_FAILURE_CASE,
    PROVISIONAL_THRESHOLD,
    USER_IMPACTS,
    FailureObservation,
    MetricResult,
    black_box_projection,
    case_id_for,
    metric_result_for,
    NOISY_RETRIEVAL_CASE,
    REFERENCE_CASE,
)


def select_smoke_goldens(goldens: Sequence[Golden]) -> list[Golden]:
    return [
        golden
        for golden in goldens
        if golden.additional_metadata.get("suite") == "smoke"
    ]


def make_runtime_test_case(golden: Golden) -> LLMTestCase:
    actual_output, retrieval_context = answer_refund_question(golden.input)
    return LLMTestCase(
        input=golden.input,
        actual_output=actual_output,
        expected_output=golden.expected_output,
        context=golden.context,
        retrieval_context=retrieval_context,
        metadata=golden.additional_metadata,
    )


def make_answer_relevancy_metric() -> AnswerRelevancyMetric:
    return AnswerRelevancyMetric(
        threshold=PROVISIONAL_THRESHOLD,
        include_reason=True,
        async_mode=False,
    )


def record_failure(
    case_id: str,
    metric_results: Sequence[MetricResult],
) -> FailureObservation | None:
    failed_results = [result for result in metric_results if result.failed]
    if not failed_results:
        return None

    return FailureObservation(
        case_id=case_id,
        failed_metrics=tuple(result.name for result in failed_results),
        reason=" | ".join(
            f"{result.name}: {result.reason}" for result in failed_results
        ),
        user_impact=USER_IMPACTS[case_id],
    )


def check_solution() -> None:
    smoke_goldens = select_smoke_goldens(ALL_GOLDENS)
    assert len(smoke_goldens) == 5
    assert all(
        golden.additional_metadata["review_status"] == "approved"
        for golden in smoke_goldens
    )

    for golden in smoke_goldens:
        test_case = make_runtime_test_case(golden)
        assert test_case.input == golden.input
        assert test_case.expected_output == golden.expected_output
        assert test_case.context == golden.context
        assert test_case.metadata == golden.additional_metadata
        assert isinstance(test_case.actual_output, str)
        assert test_case.actual_output.strip()
        assert isinstance(test_case.retrieval_context, list)

    answer_relevancy = make_answer_relevancy_metric()
    assert answer_relevancy.threshold == PROVISIONAL_THRESHOLD
    assert answer_relevancy.include_reason is True
    assert answer_relevancy.async_mode is False

    completeness = make_refund_completeness_metric(
        threshold=PROVISIONAL_THRESHOLD
    )
    assert completeness.evaluation_params == [
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.EXPECTED_OUTPUT,
    ]

    observation = record_failure(
        "intentional-wrong-window",
        [
            MetricResult("Answer Relevancy", 0.9, 0.7, "질문에 직접 답했다."),
            MetricResult(
                "Refund Completeness",
                0.4,
                0.7,
                "환불 기간이 틀렸다.",
            ),
        ],
    )
    assert observation is not None
    assert observation.failed_metrics == ("Refund Completeness",)
    assert observation.first_investigation_target == "unknown"

    assert black_box_projection(REFERENCE_CASE) == black_box_projection(
        NOISY_RETRIEVAL_CASE
    )
    assert REFERENCE_CASE.retrieval_context != NOISY_RETRIEVAL_CASE.retrieval_context
    print(
        "참고 답안 구조 검사 통과: "
        "smoke Golden 5개와 black-box 한계를 확인했습니다."
    )


def run_evaluation() -> None:
    check_solution()
    runtime_cases = [
        (case_id_for(golden), make_runtime_test_case(golden))
        for golden in select_smoke_goldens(ALL_GOLDENS)
    ]
    runtime_cases.append(("intentional-wrong-window", INTENTIONAL_FAILURE_CASE))

    for case_id, test_case in runtime_cases:
        metrics = [
            make_answer_relevancy_metric(),
            make_refund_completeness_metric(threshold=PROVISIONAL_THRESHOLD),
        ]
        results: list[MetricResult] = []
        for metric in metrics:
            metric.measure(test_case)
            results.append(metric_result_for(metric))

        print(f"\n[{case_id}]")
        for result in results:
            print(
                f"- {result.name}: {result.score:.2f} / "
                f"{result.threshold:.2f} | {result.reason}"
            )

        observation = record_failure(case_id, results)
        if observation is not None:
            print(f"  실패 reason: {observation.reason}")
            print(f"  사용자 영향: {observation.user_impact}")
            print(
                "  첫 조사 대상: unknown "
                "(다음 세션에서 component를 분리)"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4주차 세션 1 참고 답안")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="API 호출 없는 검사")
    mode.add_argument("--run", action="store_true", help="LLM judge 평가")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.check:
        check_solution()
    else:
        run_evaluation()
