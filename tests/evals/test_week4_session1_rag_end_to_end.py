"""4주차 세션 1: tracing 없는 RAG end-to-end 평가 - 학생용 실습.

사용자가 보는 최종 답변을 black-box로 먼저 평가한다. 이 결과만으로 retriever와
generator 중 어느 쪽이 원인인지는 확정할 수 없다는 한계도 관찰한다.

진행 순서:

1. TODO 1에서 reviewed dataset의 smoke Golden 5개를 선택한다.
2. TODO 2에서 Golden과 현재 앱 실행 결과를 ``LLMTestCase``로 결합한다.
3. TODO 3에서 ``AnswerRelevancyMetric`` 생성자를 완성한다.
4. TODO 4에서 실패 metric의 reason과 사용자 영향을 함께 기록한다.
5. API 호출 없는 구조 테스트를 먼저 실행한다.

   .venv/bin/python -m pytest \
       tests/evals/test_week4_session1_rag_end_to_end.py \
       -k "not judge" -v

6. 구조 테스트 통과 후 smoke 5개와 의도적 실패 사례를 judge로
   관찰한다.

   DEEPEVAL_WEEK4_SESSION1_RUN_JUDGE=1 \
       .venv/bin/deepeval test run \
       tests/evals/test_week4_session1_rag_end_to_end.py -v

마지막 명령은 LLM judge API를 호출하므로 ``OPENAI_API_KEY``와 비용이
필요하다. threshold는 5주차에서 보정하기 전인 학습용 임시 값이다. 참고
답안은 네 TODO를 직접 완성한 뒤
``week4_session1_rag_end_to_end_solution.py``와 비교한다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final, Sequence

import pytest
from deepeval.dataset import Golden
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.metrics.base_metric import BaseMetric
from deepeval.test_case import LLMTestCase, SingleTurnParams

from app.refund_support import answer_refund_question
from evals.metrics.refund_completeness import make_refund_completeness_metric
from tests.evals.test_week3_session3_local_dataset import load_dataset


PROVISIONAL_THRESHOLD: Final = 0.7
RUN_JUDGE: Final = os.getenv("DEEPEVAL_WEEK4_SESSION1_RUN_JUDGE") == "1"
ALL_GOLDENS: Final[list[Golden]] = load_dataset().goldens

USER_IMPACTS: Final = {
    "refund-known-bug-001": (
        "잘못된 환불 기간이나 절차 때문에 환불 기회를 놓칠 수 있다."
    ),
    "refund-normal-001": (
        "요청 채널을 찾지 못해 환불 접수가 지연될 수 있다."
    ),
    "refund-boundary-001": (
        "30일 경계의 자격을 오해해 유효한 요청을 포기할 수 있다."
    ),
    "refund-unknown-001": (
        "확인되지 않은 회원 정책을 사실로 믿을 수 있다."
    ),
    "refund-safety-001": "불필요한 결제 인증 정보를 노출할 수 있다.",
    "intentional-wrong-window": (
        "90일이라는 잘못된 안내를 믿고 환불 가능 기간을 넘길 수 있다."
    ),
}


@dataclass(frozen=True)
class MetricResult:
    """한 metric 실행 결과를 외부 API 객체와 분리해 기록한다."""

    name: str
    score: float
    threshold: float
    reason: str

    @property
    def failed(self) -> bool:
        return self.score < self.threshold


@dataclass(frozen=True)
class FailureObservation:
    """score를 사용자 위험과 연결하는 end-to-end 실패 기록."""

    case_id: str
    failed_metrics: tuple[str, ...]
    reason: str
    user_impact: str
    first_investigation_target: str = "unknown"


def case_id_for(golden: Golden) -> str:
    metadata = golden.additional_metadata
    assert isinstance(metadata, dict)
    case_id = metadata.get("case_id")
    assert isinstance(case_id, str) and case_id.strip()
    return case_id


def select_smoke_goldens(goldens: Sequence[Golden]) -> list[Golden]:
    """reviewed dataset에서 핵심 smoke Golden 5개를 선택한다."""
    # TODO 1: additional_metadata의 suite가 "smoke"인 Golden만 반환하세요.
    # 힌트: 입력 순서를 유지하고, 이 함수 안에서 개수를 억지로 5개로
    # 자르지 않습니다.
    return [golden for golden in goldens if golden.additional_metadata["suite"] == "smoke"]



def make_runtime_test_case(golden: Golden) -> LLMTestCase:
    """정적 reference와 현재 앱의 runtime observation을 결합한다."""
    # TODO 2:
    # 1. golden.input으로 answer_refund_question()을 한 번 호출하세요.
    # 2. Golden의 expected_output/context는 정적 reference로 전달하세요.
    # 3. callback의 답변/문서는 actual_output/retrieval_context에
    #    전달하세요.
    # 4. Golden metadata도 추적을 위해 전달하세요.
    # context와 retrieval_context가 우연히 같아도 서로 바꾸면 안 됩니다.
    answer, retreival_context = answer_refund_question(question=golden.input)

    return LLMTestCase(
        input=golden.input,
        actual_output=answer,
        expected_output=golden.expected_output,
        context=golden.context,
        retrieval_context=retreival_context,
        metadata=golden.additional_metadata
    )


def make_answer_relevancy_metric() -> AnswerRelevancyMetric:
    """질문에 직접 답하는지를 보는 black-box 표준 metric을 만든다."""
    # TODO 3: threshold=PROVISIONAL_THRESHOLD, include_reason=True,
    # async_mode=False인 AnswerRelevancyMetric을 반환하세요.
    return AnswerRelevancyMetric(
        threshold=PROVISIONAL_THRESHOLD,
        include_reason=True,
        async_mode=False
    )


def record_failure(
    case_id: str,
    metric_results: Sequence[MetricResult],
) -> FailureObservation | None:
    """실패가 있으면 judge reason과 사용자 영향을 한 기록으로 묶는다."""
    # TODO 4:
    # 1. result.failed가 True인 결과만 고르세요.
    # 2. 실패가 없으면 None을 반환하세요.
    # 3. 실패 metric 이름과 reason을 보존하고 USER_IMPACTS를 연결하세요.
    # black-box score만으로 내부 원인을 확정할 수 없으므로
    # first_investigation_target은 기본값 "unknown"으로 두세요.
    for result in metric_results:
        if result.failed == True:
            return FailureObservation(
                case_id=case_id,
                failed_metrics=result.name,
                reason=result.reason,
                user_impact=USER_IMPACTS[case_id]
            )

    return None

### ----------------------- ###

def make_end_to_end_metrics() -> list[BaseMetric]:
    """서로 다른 사용자 품질 축 두 개를 만든다."""
    return [
        make_answer_relevancy_metric(),
        make_refund_completeness_metric(threshold=PROVISIONAL_THRESHOLD),
    ]


def metric_result_for(metric: BaseMetric) -> MetricResult:
    """measure()가 끝난 DeepEval metric에서 기록용 값을 꺼낸다."""
    assert isinstance(metric.score, (int, float))
    reason = metric.reason if isinstance(metric.reason, str) else "reason 없음"
    return MetricResult(
        name=metric.__name__,
        score=float(metric.score),
        threshold=float(metric.threshold),
        reason=reason,
    )


REFERENCE_CASE: Final = LLMTestCase(
    name="clean retrieval과 좋은 최종 답변",
    input="지난주에 산 상품을 환불하려면 어떻게 해야 하나요?",
    actual_output=(
        "구매 후 30일 이내에 주문 번호와 구매일을 준비해 고객센터로 "
        "환불을 요청할 수 있습니다."
    ),
    expected_output=(
        "구매 후 30일 이내에 주문 번호와 구매일을 준비해 고객센터로 "
        "환불을 요청할 수 있습니다."
    ),
    retrieval_context=[
        "구매 후 30일 이내에는 전액 환불을 요청할 수 있습니다.",
        "환불은 고객센터를 통해 요청해야 합니다.",
        "환불 요청에는 주문 번호와 구매일이 필요합니다.",
    ],
)

NOISY_RETRIEVAL_CASE: Final = LLMTestCase(
    name="noisy retrieval이지만 좋은 최종 답변",
    input=REFERENCE_CASE.input,
    actual_output=REFERENCE_CASE.actual_output,
    expected_output=REFERENCE_CASE.expected_output,
    retrieval_context=[
        *REFERENCE_CASE.retrieval_context,
        "일반 배송은 결제 완료 후 평균 2~3일이 걸립니다.",
        "회원 등급은 최근 12개월의 구매 금액을 기준으로 산정합니다.",
    ],
)

INTENTIONAL_FAILURE_CASE: Final = LLMTestCase(
    name="잘못된 90일 환불 안내",
    input=REFERENCE_CASE.input,
    actual_output=(
        "구매 후 90일 이내에 주문 번호와 구매일을 준비해 고객센터로 "
        "환불을 요청할 수 있습니다."
    ),
    expected_output=REFERENCE_CASE.expected_output,
    metadata={"case_id": "intentional-wrong-window"},
)


def black_box_projection(test_case: LLMTestCase) -> tuple[str, str, str | None]:
    """두 end-to-end metric이 읽는 최종 결과 field만 반환한다."""
    return test_case.input, test_case.actual_output, test_case.expected_output


def test_smoke_suite_has_five_reviewed_goldens() -> None:
    """평가 대상이 승인된 smoke Golden 5개로 정확히 제한되는지 확인한다.

    잘못된 subset이나 미승인 reference를 평가하면 metric 결과보다 입력 데이터가
    실패 원인이 될 수 있다. 따라서 judge를 호출하기 전에 사례 수, 고유 case ID,
    review 상태를 검증해 black-box 평가의 출발점을 신뢰할 수 있게 한다.
    """
    smoke_goldens = select_smoke_goldens(ALL_GOLDENS)

    assert len(smoke_goldens) == 5
    assert len({case_id_for(golden) for golden in smoke_goldens}) == 5
    assert all(
        golden.additional_metadata["suite"] == "smoke"
        and golden.additional_metadata["review_status"] == "approved"
        for golden in smoke_goldens
    )


def test_smoke_goldens_become_runtime_test_cases() -> None:
    """Golden reference와 현재 앱의 실행 결과가 올바른 field에 연결되는지 확인한다.

    ``expected_output``과 ``context``는 사람이 승인한 정적 기준이어야 하고,
    ``actual_output``과 ``retrieval_context``는 매 테스트 실행에서 앱이 만든
    관측값이어야 한다. 이 계약이 깨지면 저장된 답변을 재평가하거나 reference와
    runtime 값을 뒤섞게 되므로 end-to-end 결과를 현재 앱 품질로 해석할 수 없다.
    """
    for golden in select_smoke_goldens(ALL_GOLDENS):
        test_case = make_runtime_test_case(golden)

        assert test_case.input == golden.input
        assert test_case.expected_output == golden.expected_output
        assert test_case.context == golden.context
        assert test_case.metadata == golden.additional_metadata
        assert isinstance(test_case.actual_output, str)
        assert test_case.actual_output.strip()
        assert isinstance(test_case.retrieval_context, list)


def test_end_to_end_metrics_have_distinct_minimum_fields() -> None:
    """두 end-to-end metric이 서로 다른 사용자 품질 축만 읽는지 확인한다.

    Answer Relevancy는 질문과 최종 답변의 직접성을 보고, Refund Completeness는
    실제 답변과 기대 답변의 필수 정보 차이를 본다. 이 테스트는 설정 오류로 두
    metric의 책임을 섞거나, 이 단계에서 ``retrieval_context``까지 평가해
    black-box 범위를 벗어나는 것을 막기 위해 필요하다.
    """
    answer_relevancy = make_answer_relevancy_metric()
    completeness = make_refund_completeness_metric(
        threshold=PROVISIONAL_THRESHOLD
    )

    assert isinstance(answer_relevancy, AnswerRelevancyMetric)
    assert answer_relevancy.threshold == PROVISIONAL_THRESHOLD
    assert answer_relevancy.include_reason is True
    assert answer_relevancy.async_mode is False
    assert completeness.evaluation_params == [
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.EXPECTED_OUTPUT,
    ]


def test_failure_record_keeps_reason_impact_and_unknown_cause() -> None:
    """낮은 score를 judge reason과 사용자 영향으로 기록하되 원인은 유보한다.

    세션 1의 black-box 결과는 최종 답변의 실패 증상은 보여 주지만 retriever와
    generator 중 원인을 확정하지 못한다. 따라서 실패 metric과 reason은 보존하고
    사용자 위험을 연결하면서도 첫 조사 대상을 ``unknown``으로 남기는지 확인한다.
    """
    results = [
        MetricResult("Answer Relevancy", 0.9, 0.7, "질문에 직접 답했다."),
        MetricResult("Refund Completeness", 0.4, 0.7, "환불 기간이 틀렸다."),
    ]

    observation = record_failure("intentional-wrong-window", results)

    assert observation is not None
    assert observation.failed_metrics == "Refund Completeness"
    assert "환불 기간이 틀렸다." in observation.reason
    assert observation.user_impact == USER_IMPACTS["intentional-wrong-window"]
    assert observation.first_investigation_target == "unknown"

def test_black_box_pass_cannot_prove_retriever_is_clean() -> None:
    """동일한 최종 답변만으로 retrieval의 clean/noisy 여부를 구분할 수 없음을 확인한다.

    두 사례는 사용자 질문, 최종 답변, 기대 답변이 같지만 검색 문서의 잡음은
    다르다. 현재 end-to-end metric이 읽는 black-box projection이 동일하므로,
    최종 답변의 통과를 retriever 정상으로 해석하면 안 되며 세션 2의 별도
    retriever 평가가 필요하다는 한계를 재현한다.
    """
    assert black_box_projection(REFERENCE_CASE) == black_box_projection(
        NOISY_RETRIEVAL_CASE
    )
    assert REFERENCE_CASE.retrieval_context != NOISY_RETRIEVAL_CASE.retrieval_context


### ------------------- ########

@pytest.mark.skipif(
    not RUN_JUDGE,
    reason=(
        "DEEPEVAL_WEEK4_SESSION1_RUN_JUDGE=1일 때만 judge API를 호출합니다."
    ),
)
def test_judge_observes_smoke_and_intentional_failure() -> None:
    """실제 smoke 답변을 평가하고 의도적인 90일 오류를 탐지하는지 확인한다.

    이 테스트는 현재 앱의 사용자 관점 score와 reason을 관찰하는 동시에, 명백히
    잘못된 답변에서 하나 이상의 metric이 threshold 아래로 내려가는지 검사한다.
    의도적 오류의 낮은 score는 평가기가 결함을 감지했다는 뜻이므로 pytest는
    통과한다. 현재 assertion은 모든 smoke 실패를 차단하는 품질 gate가 아니라
    negative-control 탐지 능력을 확인하기 위한 것이다.
    """
    runtime_cases = [
        (case_id_for(golden), make_runtime_test_case(golden))
        for golden in select_smoke_goldens(ALL_GOLDENS)
    ]
    runtime_cases.append(("intentional-wrong-window", INTENTIONAL_FAILURE_CASE))

    observations: list[FailureObservation] = []
    intentional_results: list[MetricResult] = []

    for case_id, test_case in runtime_cases:
        results: list[MetricResult] = []
        for metric in make_end_to_end_metrics():
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
            observations.append(observation)
            print(f"  사용자 영향: {observation.user_impact}")
            print(
                "  첫 조사 대상: unknown (black-box만으로 원인 확정 불가)"
            )

        if case_id == "intentional-wrong-window":
            intentional_results = results

    assert any(result.failed for result in intentional_results), (
        "의도적인 90일 오류를 두 metric이 모두 놓쳤습니다. score와 reason을 "
        "기록하고 "
        "5주차 threshold/rubric 보정 후보로 남기세요."
    )
    assert any(
        observation.case_id == "intentional-wrong-window"
        for observation in observations
    )
