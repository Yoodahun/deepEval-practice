"""4주차 세션 2 RAG retriever 평가 실습의 참고 답안.

학생용 파일의 TODO 1~3을 완성한 뒤 비교한다. ``--check``는 외부 API를 호출하지
않고, ``--run``은 세 fixture 쌍에 contextual metric을 총 6회 실행한다.

    .venv/bin/python -m \
        tests.evals.week4_session2_rag_retriever_solution --check

    .venv/bin/python -m \
        tests.evals.week4_session2_rag_retriever_solution --run

기능 구분:

- DeepEval 공식 제공: ``LLMTestCase``와 세 ``Contextual*Metric`` 클래스
- 학습용 커스텀: 아래 retrieval fixture, primary-signal 매핑, 실행 helper.
  DeepEval이 제공하는 모델이나 진단 기능이 아니다.
- 예제 애플리케이션 코드: 실제 retriever 대신 통제된 문자열 목록을 사용한다.
"""

from __future__ import annotations

import argparse
from collections import Counter
from typing import Sequence

from deepeval.metrics import (
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
)
from deepeval.metrics.base_metric import BaseMetric
from deepeval.test_case import LLMTestCase

from tests.evals.test_week4_session2_rag_retriever import (
    CHANNEL_POLICY,
    DIAGNOSIS_BY_METRIC,
    EXPECTED_OUTPUT,
    MEMBERSHIP_NOISE,
    METRIC_REQUIRED_FIELDS,
    NOISE_DOCUMENTS,
    PROVISIONAL_THRESHOLD,
    QUESTION,
    REQUIRED_INFO_POLICY,
    REQUIRED_POLICIES,
    SHIPPING_NOISE,
    WINDOW_POLICY,
    FixtureName,
    MetricKey,
    MetricResult,
    metric_result_for,
)


# 학습용 커스텀 참고 답안 fixture: DeepEval 제공 기능 아님
RETRIEVAL_CONTEXTS: dict[FixtureName, list[str]] = {
    "clean": [
        WINDOW_POLICY,
        REQUIRED_INFO_POLICY,
        CHANNEL_POLICY,
    ],
    "missing": [
        WINDOW_POLICY,
        CHANNEL_POLICY,
    ],
    "noisy": [
        WINDOW_POLICY,
        REQUIRED_INFO_POLICY,
        CHANNEL_POLICY,
        SHIPPING_NOISE,
        MEMBERSHIP_NOISE,
    ],
    "poorly_ranked": [
        SHIPPING_NOISE,
        MEMBERSHIP_NOISE,
        WINDOW_POLICY,
        REQUIRED_INFO_POLICY,
        CHANNEL_POLICY,
    ],
}

# 학습용 커스텀 예측 매핑: DeepEval 제공 기능 아님
PRIMARY_SIGNAL_BY_FIXTURE = {
    "clean": "healthy",
    "missing": "contextual_recall",
    "noisy": "contextual_relevancy",
    "poorly_ranked": "contextual_precision",
}


def make_retrieval_case(fixture_name: FixtureName) -> LLMTestCase:
    return LLMTestCase(
        name=f"retriever-{fixture_name}",
        input=QUESTION,
        expected_output=EXPECTED_OUTPUT,
        retrieval_context=RETRIEVAL_CONTEXTS[fixture_name],
        metadata={"fixture_name": fixture_name, "component_scope": "retriever"},
    )


def make_contextual_metric(metric_key: MetricKey) -> BaseMetric:
    common_options = {
        "threshold": PROVISIONAL_THRESHOLD,
        "include_reason": True,
        "async_mode": False,
    }
    if metric_key == "contextual_recall":
        return ContextualRecallMetric(**common_options)
    if metric_key == "contextual_relevancy":
        return ContextualRelevancyMetric(**common_options)
    if metric_key == "contextual_precision":
        return ContextualPrecisionMetric(**common_options)
    raise ValueError(f"지원하지 않는 metric key입니다: {metric_key}")


def check_solution() -> None:
    clean = RETRIEVAL_CONTEXTS["clean"]
    missing = RETRIEVAL_CONTEXTS["missing"]
    noisy = RETRIEVAL_CONTEXTS["noisy"]
    poorly_ranked = RETRIEVAL_CONTEXTS["poorly_ranked"]

    assert clean == list(REQUIRED_POLICIES)
    assert missing == [WINDOW_POLICY, CHANNEL_POLICY]
    assert REQUIRED_INFO_POLICY not in missing
    assert not set(missing).intersection(NOISE_DOCUMENTS)
    expected_noisy_documents = Counter((*REQUIRED_POLICIES, *NOISE_DOCUMENTS))
    assert Counter(noisy) == Counter(poorly_ranked) == expected_noisy_documents
    assert noisy[: len(REQUIRED_POLICIES)] == list(REQUIRED_POLICIES)
    assert poorly_ranked[: len(NOISE_DOCUMENTS)] == list(NOISE_DOCUMENTS)

    cases = [make_retrieval_case(name) for name in RETRIEVAL_CONTEXTS]
    assert {case.input for case in cases} == {QUESTION}
    assert {case.expected_output for case in cases} == {EXPECTED_OUTPUT}
    assert all(case.actual_output is None for case in cases)

    assert PRIMARY_SIGNAL_BY_FIXTURE == {
        "clean": "healthy",
        "missing": "contextual_recall",
        "noisy": "contextual_relevancy",
        "poorly_ranked": "contextual_precision",
    }

    expected_types = {
        "contextual_recall": ContextualRecallMetric,
        "contextual_relevancy": ContextualRelevancyMetric,
        "contextual_precision": ContextualPrecisionMetric,
    }
    for metric_key, expected_type in expected_types.items():
        metric = make_contextual_metric(metric_key)
        assert isinstance(metric, expected_type)
        assert metric.threshold == PROVISIONAL_THRESHOLD
        assert metric.include_reason is True
        assert metric.async_mode is False

    assert set(DIAGNOSIS_BY_METRIC) == set(METRIC_REQUIRED_FIELDS)
    assert "누락" in DIAGNOSIS_BY_METRIC["contextual_recall"]
    assert "무관 문서" in DIAGNOSIS_BY_METRIC["contextual_relevancy"]
    assert "reranker" in DIAGNOSIS_BY_METRIC["contextual_precision"]

    print(
        "참고 답안 구조 검사 통과: "
        "누락·잡음·순위 fixture와 metric 책임을 확인했습니다."
    )


def evaluate_fixture(
    fixture_name: FixtureName,
    metric_key: MetricKey,
) -> MetricResult:
    metric = make_contextual_metric(metric_key)
    metric.measure(make_retrieval_case(fixture_name))
    return metric_result_for(fixture_name, metric_key, metric)


def run_evaluation() -> None:
    check_solution()
    experiments: Sequence[tuple[MetricKey, FixtureName, FixtureName]] = (
        ("contextual_recall", "clean", "missing"),
        ("contextual_relevancy", "clean", "noisy"),
        ("contextual_precision", "noisy", "poorly_ranked"),
    )

    unexpected_directions: list[str] = []
    for metric_key, healthier_fixture, defective_fixture in experiments:
        healthier = evaluate_fixture(healthier_fixture, metric_key)
        defective = evaluate_fixture(defective_fixture, metric_key)

        print(f"\n[{metric_key}]")
        for result in (healthier, defective):
            print(
                f"- {result.fixture_name}: {result.score:.2f} / "
                f"{result.threshold:.2f} | {result.reason}"
            )
        print(f"  첫 조사 가설: {DIAGNOSIS_BY_METRIC[metric_key]}")

        if healthier.score <= defective.score:
            unexpected_directions.append(
                f"{metric_key}: {healthier_fixture}={healthier.score:.2f}, "
                f"{defective_fixture}={defective.score:.2f}"
            )

    if unexpected_directions:
        print(
            "\n예상과 다른 방향입니다. "
            "threshold보다 fixture와 reason을 먼저 봅니다."
        )
        for observation in unexpected_directions:
            print(f"- {observation}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4주차 세션 2 참고 답안")
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
