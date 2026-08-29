"""4주차 세션 3: RAG generator 평가 - 학생용 실습.

RAG의 generator는 사용자 질문과 retriever가 찾은 문서를 읽고 최종 답변을
만드는 컴포넌트다. field 흐름은 다음과 같다.

``input`` + ``retrieval_context`` -> generator -> ``actual_output``

이번 실습에서는 정상 ``retrieval_context``를 고정하고 ``actual_output``만
바꾼다. 실제 LLM generator 대신 미리 작성한 답변 문자열을 사용해 생성 모델의
무작위성 없이 세 품질 축을 비교한다.

- Answer Relevancy: 질문에 직접 답하는가?
- Faithfulness: 답변의 주장이 검색 근거에 의해 뒷받침되는가?
- Refund Completeness: 다음 행동에 필요한 정보를 빠뜨리지 않았는가?

진행 순서:

1. TODO 1에서 네 generator 출력을 fixture 이름과 연결한다.
2. TODO 2에서 동일한 질문·근거와 선택한 답변으로 ``LLMTestCase``를 만든다.
3. TODO 3에서 세 품질 축에 대응하는 metric factory를 완성한다.
4. TODO 4에서 정상 답변과 대표 결함 답변의 비교 쌍을 정한다.
5. judge 실행 전에 각 비교의 예상 방향과 이유를 커리큘럼에 기록한다.

먼저 외부 API 없이 구문 오류만 확인한다.

    .venv/bin/python -m py_compile \
        tests/evals/test_week4_session3_rag_generator.py

그다음 세 metric을 두 사례씩 총 6회 평가한다.

    DEEPEVAL_WEEK4_SESSION3_RUN_JUDGE=1 \
        .venv/bin/deepeval test run \
        tests/evals/test_week4_session3_rag_generator.py -v

judge 실행에는 ``OPENAI_API_KEY``와 비용이 필요하다. ``measure()`` 한 번도
내부적으로 주장 추출, 판정과 reason 생성 등 여러 모델 호출을 만들 수 있다.

기능 구분:

- DeepEval 공식 제공: ``LLMTestCase``, ``AnswerRelevancyMetric``,
  ``FaithfulnessMetric``
- 저장소 재사용 metric: 환불 안내 완전성을 평가하는 custom ``GEval``
- 학습용 커스텀: fixture/metric key 타입, 답변 fixture와 비교 실험 목록
"""

from __future__ import annotations

import os
from typing import Final, Literal

import pytest
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.metrics.base_metric import BaseMetric
from deepeval.test_case import LLMTestCase

from evals.metrics.refund_completeness import (
    make_refund_completeness_metric,
)


# 학습용 커스텀: DeepEval 제공 기능 아님
FixtureName = Literal[
    "good",
    "off_topic",
    "hallucinated_window",
    "incomplete",
]
MetricKey = Literal[
    "answer_relevancy",
    "faithfulness",
    "refund_completeness",
]
Experiment = tuple[MetricKey, FixtureName, FixtureName]

PROVISIONAL_THRESHOLD: Final = 0.7
RUN_JUDGE: Final = os.getenv("DEEPEVAL_WEEK4_SESSION3_RUN_JUDGE") == "1"

QUESTION: Final = "지난주에 산 상품을 환불하려면 어떻게 해야 하나요?"
EXPECTED_OUTPUT: Final = (
    "구매 후 30일 이내에 주문 번호와 구매일을 준비해 고객센터로 "
    "환불을 요청할 수 있습니다."
)

# reviewer가 정상이라고 확인한 clean retrieval이다.
WINDOW_POLICY: Final = "구매 후 30일 이내에는 전액 환불을 요청할 수 있습니다."
REQUIRED_INFO_POLICY: Final = (
    "환불 요청에는 주문 번호와 구매일이 필요합니다."
)
CHANNEL_POLICY: Final = "환불은 고객센터를 통해 요청해야 합니다."
CLEAN_RETRIEVAL_CONTEXT: Final[tuple[str, ...]] = (
    WINDOW_POLICY,
    REQUIRED_INFO_POLICY,
    CHANNEL_POLICY,
)

# 네 답변은 generator 결함만 통제하기 위한 학습용 fixture다.
GOOD_OUTPUT: Final = (
    "지난주 구매한 상품은 30일 이내이므로 주문 번호와 구매일을 준비해 "
    "고객센터로 전액 환불을 요청해 주세요."
)
OFF_TOPIC_OUTPUT: Final = (
    "일반 배송은 보통 결제 완료 후 2~3일 안에 도착합니다."
)
HALLUCINATED_WINDOW_OUTPUT: Final = (
    "구매 후 90일 이내에 주문 번호와 구매일을 준비해 고객센터로 "
    "전액 환불을 요청할 수 있습니다."
)
INCOMPLETE_OUTPUT: Final = "구매 후 30일 이내에는 전액 환불할 수 있습니다."


# TODO 1: 각 fixture 이름에 위 답변 상수를 연결하세요.
# 새 문장을 만들지 말고 제공된 상수를 사용해 비교 조건을 유지합니다.
GENERATOR_OUTPUTS: dict[FixtureName, str | None] = {
    "good": None,
    "off_topic": None,
    "hallucinated_window": None,
    "incomplete": None,
}


def generator_output_for(fixture_name: FixtureName) -> str:
    """완성된 fixture의 답변을 반환하고 미완성 TODO를 명확히 알린다."""
    actual_output = GENERATOR_OUTPUTS[fixture_name]
    if actual_output is None:
        raise NotImplementedError(
            f"TODO 1: {fixture_name} generator 출력을 연결하세요."
        )
    return actual_output


def make_generator_case(fixture_name: FixtureName) -> LLMTestCase:
    """답변만 달라지는 generator 평가 사례를 만든다.

    TODO 2: 다음 field를 사용해 ``LLMTestCase``를 반환하세요.

    - ``name``: ``generator-{fixture_name}``
    - ``input``: ``QUESTION``
    - ``actual_output``: ``generator_output_for(fixture_name)``
    - ``expected_output``: ``EXPECTED_OUTPUT``
    - ``retrieval_context``: ``list(CLEAN_RETRIEVAL_CONTEXT)``
    - ``metadata``: fixture, generator scope, clean retrieval을 추적할 값

    ``expected_output``은 완전성 reference이고 ``retrieval_context``는
    Faithfulness가 답변 주장을 대조하는 runtime 근거다.
    """
    raise NotImplementedError("TODO 2: generator LLMTestCase를 만드세요.")


def make_generator_metric(metric_key: MetricKey) -> BaseMetric:
    """generator의 품질 축에 해당하는 metric을 만든다.

    TODO 3: 아래 연결을 구현하세요.

    - ``answer_relevancy`` -> ``AnswerRelevancyMetric``
    - ``faithfulness`` -> ``FaithfulnessMetric``
    - ``refund_completeness`` -> ``make_refund_completeness_metric``

    세 metric 모두 ``threshold=PROVISIONAL_THRESHOLD``와
    ``async_mode=False``를 사용한다. 표준 metric에는 ``include_reason=True``도
    전달한다. 지원하지 않는 key에는 ``ValueError``를 발생시킨다.
    """
    raise NotImplementedError("TODO 3: generator metric factory를 완성하세요.")


# TODO 4: (metric, 정상 fixture, 대표 결함 fixture) 세 쌍을 작성하세요.
# 각 metric이 가장 직접적으로 반응해야 하는 결함 하나를 선택합니다.
EXPERIMENTS: tuple[Experiment, ...] | None = None


@pytest.mark.skipif(
    not RUN_JUDGE,
    reason=(
        "DEEPEVAL_WEEK4_SESSION3_RUN_JUDGE=1일 때만 judge API를 호출합니다."
    ),
)
def test_judge_observes_expected_generator_signal_directions() -> None:
    """정상 답변과 대표 결함 답변의 metric 방향을 관찰한다.

    확인 결과: 질문 이탈은 Answer Relevancy, 근거 없는 주장은 Faithfulness,
    절차 누락은 custom completeness에서 정상 답변보다 낮은지 확인한다.
    실행 목적: metric이 의도한 generator 결함에 반응하는지 score와 reason으로
    확인하고, 예상과 다르면 threshold보다 사례와 평가 기준을 먼저 재검토한다.
    """
    if EXPERIMENTS is None:
        raise NotImplementedError("TODO 4: 비교 실험 세 쌍을 작성하세요.")

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

    assert not unexpected_directions, (
        "예상과 다른 metric 방향이 있습니다. threshold를 바꾸기 전에 답변 "
        "fixture와 reason을 확인하세요:\n" + "\n".join(unexpected_directions)
    )
