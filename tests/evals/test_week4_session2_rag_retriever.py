"""4주차 세션 2: RAG retriever 평가 - 학생용 실습.

세션 1에서 발견한 최종 답변 실패의 원인을 바로 generator로 단정하지 않고,
retrieval만 격리해 누락, 잡음, 순위 문제를 구분한다. 모든 fixture는 같은
``input``과 ``expected_output``을 사용하고 ``retrieval_context``만 바꾼다.

진행 순서:

1. TODO 1에서 clean, missing, noisy, poorly-ranked retrieval을 구성한다.
2. TODO 2에서 각 fixture가 주로 자극할 metric 신호를 예측한다.
3. TODO 3에서 세 contextual metric 생성자를 완성한다.
4. API 호출 없는 구조 테스트로 fixture와 진단 가설을 확인한다.

   .venv/bin/python -m pytest \
       tests/evals/test_week4_session2_rag_retriever.py \
       -k "not judge" -v

5. 구조 테스트 통과 후 세 쌍의 점수와 reason을 judge로 비교한다.

   DEEPEVAL_WEEK4_SESSION2_RUN_JUDGE=1 \
       .venv/bin/deepeval test run \
       tests/evals/test_week4_session2_rag_retriever.py -v

마지막 명령은 6회의 LLM judge 평가를 실행하므로 ``OPENAI_API_KEY``와 비용이
필요하다. 절대 점수보다 어떤 fixture에서 어느 metric이 내려가는지와 reason이
의도한 결함을 언급하는지를 먼저 확인한다.

기능 구분:

- DeepEval 공식 제공: ``LLMTestCase``, ``ContextualRecallMetric``,
  ``ContextualRelevancyMetric``, ``ContextualPrecisionMetric``
- 학습용 커스텀: fixture 이름과 metric key 타입, retrieval fixture,
  ``MetricResult``, 진단 매핑. DeepEval이 제공하는 모델이나 진단 기능이 아니다.
- 예제 애플리케이션 코드: 이 파일은 실제 retriever 대신 통제된 문자열 목록을
  사용하므로 해당 코드가 없다.
"""

from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass
from typing import Final, Literal

import pytest
from deepeval.metrics import (
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
)
from deepeval.metrics.base_metric import BaseMetric
from deepeval.test_case import LLMTestCase


# 학습용 커스텀 타입 별칭: DeepEval 제공 기능 아님
FixtureName = Literal["clean", "missing", "noisy", "poorly_ranked"]
MetricKey = Literal[
    "contextual_recall",
    "contextual_relevancy",
    "contextual_precision",
]
PrimarySignal = Literal[
    "healthy",
    "contextual_recall",  # 필요한 근거를 빠짐없이 가져왔는가?
    "contextual_relevancy",  # 가져온 내용들이 다 관련이 있는가?
    "contextual_precision",  # 중요한 근거를 앞쪽에 배치했는가?
]

# 학습용 커스텀 실험 설정과 fixture 데이터: DeepEval 제공 기능 아님
PROVISIONAL_THRESHOLD: Final = 0.7
RUN_JUDGE: Final = os.getenv("DEEPEVAL_WEEK4_SESSION2_RUN_JUDGE") == "1"

QUESTION: Final = "지난주에 산 상품을 환불하려면 어떻게 해야 하나요?"
EXPECTED_OUTPUT: Final = (
    "구매 후 30일 이내에 주문 번호와 구매일을 준비해 고객센터로 "
    "환불을 요청할 수 있습니다."
)

WINDOW_POLICY: Final = "구매 후 30일 이내에는 전액 환불을 요청할 수 있습니다."
REQUIRED_INFO_POLICY: Final = (
    "환불 요청에는 주문 번호와 구매일이 필요합니다."
)
CHANNEL_POLICY: Final = "환불은 고객센터를 통해 요청해야 합니다."
SHIPPING_NOISE: Final = "일반 배송은 결제 완료 후 평균 2~3일이 걸립니다."
MEMBERSHIP_NOISE: Final = (
    "회원 등급은 최근 12개월의 구매 금액을 기준으로 산정합니다."
)

REQUIRED_POLICIES: Final = (
    WINDOW_POLICY,
    REQUIRED_INFO_POLICY,
    CHANNEL_POLICY,
)
NOISE_DOCUMENTS: Final = (SHIPPING_NOISE, MEMBERSHIP_NOISE)


# TODO 1: 아래 네 retrieval fixture를 list[str]으로 완성하세요.
# - clean: 필요한 정책 세 개만 올바른 순서로 포함
# - missing: clean에서 주문 번호/구매일 정책만 제외
# - noisy: clean의 정책을 앞에 유지하고 잡음 두 개를 뒤에 추가
# - poorly_ranked: noisy와 같은 문서를 사용하되 잡음 두 개를 맨 앞으로 이동
# noisy와 poorly_ranked의 문서 집합을 같게 해야 순서 효과를 격리할 수 있습니다.
# 학습용 커스텀 retrieval fixture: DeepEval 제공 기능 아님
RETRIEVAL_CONTEXTS: dict[FixtureName, list[str] | None] = {
    "clean": [WINDOW_POLICY, REQUIRED_INFO_POLICY, CHANNEL_POLICY],
    "missing": [WINDOW_POLICY, CHANNEL_POLICY],
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
# TODO 2: 각 fixture에서 가장 먼저 관찰할 신호 하나를 선택하세요.
# 사용할 수 있는 값: healthy, contextual_recall, contextual_relevancy,
# contextual_precision. 하나의 fixture가 다른 metric에도 영향을 줄 수 있지만,
# 여기서는 fixture를 만든 1차 목적만 기록합니다.
PRIMARY_SIGNAL_BY_FIXTURE: dict[FixtureName, PrimarySignal | None] = {
    "clean": "healthy",
    "missing": "contextual_recall",
    "noisy": "contextual_relevancy",
    "poorly_ranked": "contextual_precision",
}


# 학습용 커스텀 required-field 학습표: DeepEval 제공 기능 아님
METRIC_REQUIRED_FIELDS: Final[dict[MetricKey, frozenset[str]]] = {
    "contextual_relevancy": frozenset({"input", "retrieval_context"}),
    "contextual_recall": frozenset(
        {"input", "retrieval_context", "expected_output"}
    ),
    "contextual_precision": frozenset(
        {"input", "retrieval_context", "expected_output"}
    ),
}

# 학습용 커스텀 진단 매핑: DeepEval이 원인을 확정해 주는 기능이 아님
# 이 표는 metric 선택을 강제하는 설정이 아니라 낮은 점수를 읽는 방법이다.
# 낮은 score는 원인 확정이 아니라 먼저 조사할 retriever/reranker 가설을 준다.
DIAGNOSIS_BY_METRIC: Final[dict[MetricKey, str]] = {
    "contextual_recall": (
        "retriever의 query, index, chunk, top-k에서 필수 근거 누락을 확인한다."
    ),
    "contextual_relevancy": (
        "retriever의 filter, top-k, chunk에서 무관 문서 유입을 확인한다."
    ),
    "contextual_precision": (
        "reranker와 ranking에서 관련 근거가 뒤로 밀린 이유를 확인한다."
    ),
}


# 학습용 커스텀 관찰 결과 모델: DeepEval 제공 모델 아님
@dataclass(frozen=True)
class MetricResult:
    """fixture 하나에 대한 contextual metric 관찰 결과."""

    fixture_name: FixtureName
    metric_key: MetricKey
    score: float
    threshold: float
    reason: str


def retrieval_context_for(fixture_name: FixtureName) -> list[str]:
    """TODO가 끝난 fixture를 반환하고 미완성 상태에는 명확한 오류를 낸다."""
    retrieval_context = RETRIEVAL_CONTEXTS[fixture_name]
    if retrieval_context is None:
        raise NotImplementedError(
            f"TODO 1: {fixture_name} retrieval fixture를 완성하세요."
        )
    return retrieval_context


def make_retrieval_case(fixture_name: FixtureName) -> LLMTestCase:
    """동일한 질문/reference에 retrieval observation만 바꾼 사례를 만든다."""
    return LLMTestCase(
        name=f"retriever-{fixture_name}",
        input=QUESTION,
        expected_output=EXPECTED_OUTPUT,
        retrieval_context=retrieval_context_for(fixture_name),
        metadata={"fixture_name": fixture_name, "component_scope": "retriever"},
    )


def make_contextual_metric(metric_key: MetricKey) -> BaseMetric:
    """metric key에 맞는 DeepEval contextual metric을 만든다."""
    # TODO 3: 세 metric key에 해당하는 생성자를 반환하세요.
    # 공통 설정은 threshold=PROVISIONAL_THRESHOLD, include_reason=True,
    # async_mode=False입니다. 지원하지 않는 key에는 ValueError를 발생시키세요.
    if metric_key == "contextual_recall":
        # 검색 결과에 답변에 필요한 근거가 얼마나 누락되었는지
        return ContextualRecallMetric(
            threshold=PROVISIONAL_THRESHOLD,
            include_reason=True,
            async_mode=False
        )
    elif metric_key == "contextual_relevancy":
        # 검색 결과 전체에 무관한 내용이 얼마나 있는지
        return ContextualRelevancyMetric(
            threshold=PROVISIONAL_THRESHOLD,
            include_reason=True,
            async_mode=False
        )
    elif metric_key == "contextual_precision":
        # 관련 근거의 순위와 불필요한 결과가 얼마나 있는지
        return ContextualPrecisionMetric(
            threshold=PROVISIONAL_THRESHOLD,
            include_reason=True,
            async_mode=False
        )
    else:
        raise ValueError("지원하지 않는 key입니다.")


def metric_result_for(
    fixture_name: FixtureName,
    metric_key: MetricKey,
    metric: BaseMetric,
) -> MetricResult:
    """measure()가 끝난 metric을 비교 가능한 관찰값으로 변환한다."""
    assert isinstance(metric.score, (int, float))
    reason = metric.reason if isinstance(metric.reason, str) else "reason 없음"
    return MetricResult(
        fixture_name=fixture_name,
        metric_key=metric_key,
        score=float(metric.score),
        threshold=float(metric.threshold),
        reason=reason,
    )


def test_retrieval_fixtures_have_intended_missing_and_noise_defects() -> None:
    """네 fixture가 의도한 누락과 잡음 결함을 재현하는지 검사한다.

    확인 결과: clean에는 필수 정책만 있고, missing에는 한 정책이 누락되며,
    noisy 계열에는 필수 정책과 동일한 두 잡음 문서가 있음을 확인한다.
    실행 목적: metric 결과를 해석하기 전에 fixture 자체의 결함을 결정적으로
    검증하여 잘못 만든 학습 데이터로 retriever를 오진하지 않게 한다.
    """
    clean = retrieval_context_for("clean")
    missing = retrieval_context_for("missing")
    noisy = retrieval_context_for("noisy")
    poorly_ranked = retrieval_context_for("poorly_ranked")
    expected_noisy_documents = Counter((*REQUIRED_POLICIES, *NOISE_DOCUMENTS))

    assert clean == list(REQUIRED_POLICIES)
    assert missing == [WINDOW_POLICY, CHANNEL_POLICY]
    assert Counter(noisy) == expected_noisy_documents
    assert Counter(poorly_ranked) == expected_noisy_documents


def test_retriever_cases_change_only_retrieval_context() -> None:
    """네 사례에서 retrieval observation만 달라지는지 검사한다.

    확인 결과: 모든 사례의 질문과 기대 답변은 같고 ``retrieval_context``만
    다르며, generator의 ``actual_output``과 정적 ``context``는 없음을 확인한다.
    실행 목적: score 차이를 다른 입력이나 generator가 아닌 retriever fixture의
    차이에 연결할 수 있도록 컴포넌트 평가의 격리 조건을 보장한다.
    """
    # RETRIEVAL_CONTEXTS 는 4개다.
    # clean, missing, noisy, poorly_ranked
    cases = [
        make_retrieval_case(fixture_name)
        for fixture_name in RETRIEVAL_CONTEXTS
    ]

    # retreiver의 내용은 확인하지 않는다.
    assert {case.input for case in cases} == {QUESTION}
    assert {case.expected_output for case in cases} == {EXPECTED_OUTPUT}
    assert all(case.actual_output is None for case in cases)
    assert all(case.context is None for case in cases)
    assert len({tuple(case.retrieval_context or []) for case in cases}) == 4


def test_missing_fixture_is_relevant_but_incomplete() -> None:
    """관련 문서만 있는 검색 결과도 불완전할 수 있는지 검사한다.

    확인 결과: missing fixture에는 무관한 잡음은 없지만 주문 번호와 구매일
    정책이 빠져 있어 관련성과 필수 근거 충족이 서로 다른 조건임을 확인한다.
    실행 목적: 높은 Contextual Relevancy를 충분한 retrieval로 잘못 해석하지
    않고 Contextual Recall이 담당하는 누락 위험을 구분한다.
    """
    clean = retrieval_context_for("clean")
    missing = retrieval_context_for("missing")

    assert set(missing) < set(clean)
    assert REQUIRED_INFO_POLICY not in missing
    assert not set(missing).intersection(NOISE_DOCUMENTS)


def test_noisy_and_poorly_ranked_isolate_document_order() -> None:
    """noisy와 poorly-ranked fixture가 문서 순서만 다른지 검사한다.

    확인 결과: 두 fixture의 문서 multiset은 같고 noisy에는 관련 근거가 먼저,
    poorly-ranked에는 잡음이 먼저 배치되었음을 확인한다.
    실행 목적: Contextual Precision 점수 차이를 문서 수나 잡음 양이 아니라
    ranking 순서에 연결해 reranker 조사 가설을 세울 수 있게 한다.
    """
    noisy = retrieval_context_for("noisy")
    poorly_ranked = retrieval_context_for("poorly_ranked")

    assert Counter(noisy) == Counter(poorly_ranked)
    assert noisy[: len(REQUIRED_POLICIES)] == list(REQUIRED_POLICIES)
    assert poorly_ranked[: len(NOISE_DOCUMENTS)] == list(NOISE_DOCUMENTS)
    assert noisy != poorly_ranked


def test_primary_signal_predictions_distinguish_three_failure_modes() -> None:
    """fixture별 1차 관찰 신호가 세 실패 유형을 구분하는지 검사한다.

    확인 결과: clean은 기준선, missing은 recall, noisy는 relevancy,
    poorly-ranked는 precision의 대표 관찰 대상으로 예측했음을 확인한다.
    실행 목적: judge 결과를 보기 전에 가설을 고정하여 결과에 맞춰 설명을 바꾸는
    사후 해석을 피하고, 낮은 score를 서로 다른 첫 조사 지점에 연결한다.
    """
    assert PRIMARY_SIGNAL_BY_FIXTURE == {
        "clean": "healthy",
        "missing": "contextual_recall",
        "noisy": "contextual_relevancy",
        "poorly_ranked": "contextual_precision",
    }


def test_contextual_metrics_have_expected_types_and_common_settings() -> None:
    """세 metric이 공식 클래스와 공통 실험 설정으로 생성되는지 검사한다.

    확인 결과: metric key마다 올바른 DeepEval contextual metric을 만들고 동일한
    threshold, reason, async 설정을 사용하며 required field는 다름을 확인한다.
    실행 목적: fixture 비교 조건을 고정하여 설정 차이를 metric 책임 차이로
    오해하지 않고 각 공식 metric에 필요한 ``LLMTestCase`` field를 학습한다.
    """
    expected_types = {
        "contextual_recall": ContextualRecallMetric,
        "contextual_relevancy": ContextualRelevancyMetric,
        "contextual_precision": ContextualPrecisionMetric,
    }

    for metric_key, expected_type in expected_types.items():
        # 메트릭을 생성해서 리턴받는다.
        metric = make_contextual_metric(metric_key)
        assert isinstance(metric, expected_type)
        assert metric.threshold == PROVISIONAL_THRESHOLD
        assert metric.include_reason is True
        assert metric.async_mode is False

    assert METRIC_REQUIRED_FIELDS["contextual_relevancy"] == frozenset(
        {"input", "retrieval_context"}
    )
    assert "expected_output" in METRIC_REQUIRED_FIELDS["contextual_recall"]
    assert "expected_output" in METRIC_REQUIRED_FIELDS["contextual_precision"]


def test_low_scores_map_to_distinct_retriever_diagnoses() -> None:
    """세 낮은 score가 서로 다른 첫 조사 가설로 이어지는지 검사한다.

    확인 결과: 낮은 recall, relevancy, precision이 각각 근거 누락, 무관 문서
    유입, ranking 문제를 먼저 조사하도록 매핑되어 있음을 확인한다.
    실행 목적: contextual score를 확정 원인이 아니라 retriever 또는 reranker의
    다음 조사 행동을 선택하는 진단 가설로 사용하게 한다.
    """
    assert set(DIAGNOSIS_BY_METRIC) == set(METRIC_REQUIRED_FIELDS)

    recall_diagnosis = DIAGNOSIS_BY_METRIC["contextual_recall"]
    relevancy_diagnosis = DIAGNOSIS_BY_METRIC["contextual_relevancy"]
    precision_diagnosis = DIAGNOSIS_BY_METRIC["contextual_precision"]

    assert "누락" in recall_diagnosis and "retriever" in recall_diagnosis
    assert "무관 문서" in relevancy_diagnosis and "filter" in relevancy_diagnosis
    assert "뒤로" in precision_diagnosis and "reranker" in precision_diagnosis


@pytest.mark.skipif(
    not RUN_JUDGE,
    reason=(
        "DEEPEVAL_WEEK4_SESSION2_RUN_JUDGE=1일 때만 judge API를 호출합니다."
    ),
)
def test_judge_observes_expected_retriever_signal_directions() -> None:
    """명백한 fixture 쌍에서 contextual metric의 점수 방향을 검사한다.

    확인 결과: Recall은 clean보다 missing에서, Relevancy는 clean보다 noisy에서,
    Precision은 관련 문서가 앞선 noisy보다 poorly-ranked에서 낮은지 확인한다.
    실행 목적: 절대 threshold 통과 여부가 아니라 공식 metric이 의도한 retriever
    결함에 반응하는 sensitivity를 검증하고, 방향이 다르면 reason과 fixture를
    재검토한다.
    """
    experiments: tuple[
        tuple[MetricKey, FixtureName, FixtureName], ...
    ] = (
        ("contextual_recall", "clean", "missing"),
        ("contextual_relevancy", "clean", "noisy"),
        ("contextual_precision", "noisy", "poorly_ranked"),
    )
    unexpected_directions: list[str] = []

    for metric_key, healthier_fixture, defective_fixture in experiments:
        results: list[MetricResult] = []

        for fixture_name in (healthier_fixture, defective_fixture):
            metric = make_contextual_metric(metric_key)
            metric.measure(make_retrieval_case(fixture_name))
            results.append(metric_result_for(fixture_name, metric_key, metric))

        healthier_result, defective_result = results
        print(f"\n[{metric_key}]")
        for result in results:
            print(
                f"- {result.fixture_name}: {result.score:.2f} / "
                f"{result.threshold:.2f} | {result.reason}"
            )
        print(f"  첫 조사 가설: {DIAGNOSIS_BY_METRIC[metric_key]}")

        if healthier_result.score <= defective_result.score:
            unexpected_directions.append(
                f"{metric_key}: {healthier_fixture}={healthier_result.score:.2f}, "
                f"{defective_fixture}={defective_result.score:.2f}"
            )

    assert not unexpected_directions, (
        "예상과 다른 metric 방향이 있습니다. threshold를 바꾸기 전에 fixture와 "
        "reason을 확인하세요:\n" + "\n".join(unexpected_directions)
    )
