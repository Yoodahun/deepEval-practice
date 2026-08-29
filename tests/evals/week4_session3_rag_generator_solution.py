"""4주차 세션 3 RAG generator 평가 실습의 참고 답안.

학생용 파일의 TODO 1~4를 직접 완성하고 비교한 뒤 실행한다.

    .venv/bin/python -m \
        tests.evals.week4_session3_rag_generator_solution --run

``--run``은 세 metric을 두 사례씩 평가하므로 ``OPENAI_API_KEY``와 비용이
필요하다. 이 파일은 pytest 수집 대상이 아니며 별도의 자기검증 ``--check``를
두지 않는다. 핵심 학습 결과는 실제 metric score와 reason이다.
"""

from __future__ import annotations

import argparse

from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.metrics.base_metric import BaseMetric
from deepeval.test_case import LLMTestCase

from evals.metrics.refund_completeness import (
    make_refund_completeness_metric,
)
from tests.evals.test_week4_session3_rag_generator import (
    CLEAN_RETRIEVAL_CONTEXT,
    EXPECTED_OUTPUT,
    GOOD_OUTPUT,
    HALLUCINATED_WINDOW_OUTPUT,
    INCOMPLETE_OUTPUT,
    OFF_TOPIC_OUTPUT,
    PROVISIONAL_THRESHOLD,
    QUESTION,
    Experiment,
    FixtureName,
    MetricKey,
)


# 학습용 커스텀: DeepEval 제공 기능 아님
GENERATOR_OUTPUTS: dict[FixtureName, str] = {
    "good": GOOD_OUTPUT,
    "off_topic": OFF_TOPIC_OUTPUT,
    "hallucinated_window": HALLUCINATED_WINDOW_OUTPUT,
    "incomplete": INCOMPLETE_OUTPUT,
}

EXPERIMENTS: tuple[Experiment, ...] = (
    ("answer_relevancy", "good", "off_topic"),
    ("faithfulness", "good", "hallucinated_window"),
    ("refund_completeness", "good", "incomplete"),
)


def make_generator_case(fixture_name: FixtureName) -> LLMTestCase:
    """같은 질문·근거에 선택한 generator 출력만 연결한다."""
    return LLMTestCase(
        name=f"generator-{fixture_name}",
        input=QUESTION,
        actual_output=GENERATOR_OUTPUTS[fixture_name],
        expected_output=EXPECTED_OUTPUT,
        retrieval_context=list(CLEAN_RETRIEVAL_CONTEXT),
        metadata={
            "fixture_name": fixture_name,
            "component_scope": "generator",
            "retrieval_fixture": "clean",
        },
    )


def make_generator_metric(metric_key: MetricKey) -> BaseMetric:
    """세 generator 품질 축을 공통 임시 threshold로 생성한다."""
    if metric_key == "answer_relevancy":
        return AnswerRelevancyMetric(
            threshold=PROVISIONAL_THRESHOLD,
            include_reason=True,
            async_mode=False,
        )
    if metric_key == "faithfulness":
        return FaithfulnessMetric(
            threshold=PROVISIONAL_THRESHOLD,
            include_reason=True,
            async_mode=False,
        )
    if metric_key == "refund_completeness":
        return make_refund_completeness_metric(
            threshold=PROVISIONAL_THRESHOLD
        )
    raise ValueError(f"지원하지 않는 metric key입니다: {metric_key}")


def run_evaluation() -> None:
    """정상 답변과 대표 결함 답변의 score와 reason을 비교한다."""
    unexpected_directions: list[str] = []

    for metric_key, healthier_fixture, defective_fixture in EXPERIMENTS:
        observations: list[tuple[FixtureName, float, str]] = []

        for fixture_name in (healthier_fixture, defective_fixture):
            metric = make_generator_metric(metric_key)
            score = float(metric.measure(make_generator_case(fixture_name)))
            reason = (
                metric.reason
                if isinstance(metric.reason, str)
                else "reason 없음"
            )
            observations.append((fixture_name, score, reason))

        healthier, defective = observations
        print(f"\n[{metric_key}]")
        for fixture_name, score, reason in observations:
            print(f"- {fixture_name}: {score:.2f} | {reason}")

        if healthier[1] <= defective[1]:
            unexpected_directions.append(
                f"{metric_key}: {healthier[0]}={healthier[1]:.2f}, "
                f"{defective[0]}={defective[1]:.2f}"
            )

    if unexpected_directions:
        print(
            "\n예상과 다른 방향입니다. "
            "threshold보다 답변 fixture와 reason을 먼저 봅니다."
        )
        for observation in unexpected_directions:
            print(f"- {observation}")


def parse_args() -> argparse.Namespace:
    """비용이 드는 judge 실행을 명시적인 옵션으로만 허용한다."""
    parser = argparse.ArgumentParser(description="4주차 세션 3 참고 답안")
    parser.add_argument(
        "--run",
        action="store_true",
        required=True,
        help="LLM judge 평가 실행",
    )
    return parser.parse_args()


if __name__ == "__main__":
    parse_args()
    run_evaluation()
