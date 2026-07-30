"""2주차 세션 1: 메트릭 선택법 - 학생용 실습.

목표는 "점수가 낮으면 무엇을 고칠 것인가?"를 먼저 정한 뒤 메트릭을
선택하는 것이다. 한 RAG 고객지원 시스템에 서로 다른 결함 세 개가 있다.

진행 순서:

1. TODO 1에서 각 결함을 가장 직접적으로 진단하는 메트릭을 고른다.
2. TODO 2에서 선택 가능한 메트릭 생성자를 완성한다.
3. TODO 3에서 낮은 점수일 때의 수정 행동을 한 줄씩 적는다.
4. API 호출 없이 답안의 구조를 검사한다.

   python tests/evals/week2_session1_metric_selection_exercise.py --check

5. 검사 통과 후 실제 judge 점수와 이유를 관찰한다.

   python tests/evals/week2_session1_metric_selection_exercise.py --run

정답을 보기 전 세 결함을 각각 generator, grounding, retriever 문제 중
하나로 분류해 보는 것을 권장한다. --run은 LLM judge API를 호출하므로
OPENAI_API_KEY와 소량의 비용이 필요하다.
"""

from __future__ import annotations

import argparse
from typing import Final

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
)
from deepeval.metrics.base_metric import BaseMetric
from deepeval.test_case import LLMTestCase


# input
QUESTION: Final = "지난주에 산 상품을 환불하려면 어떻게 해야 하나요?"

# 근거
CLEAN_RETRIEVAL_CONTEXT: Final = [
    (
        "구매 후 30일 이내에는 주문 번호와 함께 고객센터에 요청하면 "
        "전액 환불할 수 있습니다."
    )
]

# 불필요한 근거들
NOISY_RETRIEVAL_CONTEXT: Final = [
    *CLEAN_RETRIEVAL_CONTEXT,
    "일반 배송은 결제 완료 후 평균 2~3일이 걸립니다.",
    "회원 등급은 최근 12개월의 구매 금액을 기준으로 산정합니다.",
    "선물 포장은 주문서의 옵션 메뉴에서 추가할 수 있습니다.",
]

# 각 사례에는 의도적으로 한 가지 주요 결함만 넣었다.
SCENARIOS: Final = {
    "off_topic_answer": LLMTestCase(
        name="질문과 무관한 최종 답변",
        input=QUESTION,
        actual_output="일반 배송은 결제 후 평균 2~3일이 걸립니다.",
    ),
    "unsupported_claim": LLMTestCase(
        name="검색 근거와 모순되는 주장",
        input=QUESTION,
        actual_output=(
            "구매 후 90일 이내에 주문 번호와 함께 고객센터에 요청하면 "
            "전액 환불할 수 있습니다."
        ),
        retrieval_context=CLEAN_RETRIEVAL_CONTEXT,
    ),
    "noisy_retrieval": LLMTestCase(
        name="정답 문서와 잡음이 함께 검색됨",
        input=QUESTION,
        actual_output=(
            "지난주 구매 건은 30일 이내이므로 주문 번호와 함께 고객센터에 "
            "전액 환불을 요청할 수 있습니다."
        ),
        retrieval_context=NOISY_RETRIEVAL_CONTEXT,
    ),
}

METRIC_KEYS: Final = {
    "answer_relevancy", #질문 관련성
    "faithfulness", #근거 신뢰성
    "contextual_relevancy", #컨텍스트 관련성
}

# TODO 1: 각 결함을 가장 직접적으로 진단하는 metric key를 하나씩 적는다.
# 사용할 수 있는 값: answer_relevancy, faithfulness, contextual_relevancy
SELECTED_METRICS = {
    "off_topic_answer": "answer_relevancy",
    "unsupported_claim": "faithfulness",
    "noisy_retrieval": "contextual_relevancy",
}

# TODO 3: 해당 점수가 낮을 때 담당자가 취할 구체적인 수정 행동을 적는다.
# 예: "generator prompt에서 질문에 직접 답하도록 지시를 강화한다."
FIX_ACTIONS = {
    "answer_relevancy": "질문과 무관한 설명을 줄인다.",
    "faithfulness": "제대로 된 근거를 참조한다.",
    "contextual_relevancy": "컨텍스트와 관련된 답을 한다.",
}


def make_metric(metric_key: str) -> BaseMetric:
    """metric key에 맞는 DeepEval 표준 메트릭을 만든다."""
    if metric_key == "answer_relevancy":
        # 첫 생성자는 예제로 제공한다.
        # 답변이 질문에 관련 있는가?
        return AnswerRelevancyMetric(threshold=0.7, include_reason=True)

    # TODO 2: 나머지 두 metric key의 생성자를 완성한다.
    # 힌트: 위에서 import한 클래스와 같은 threshold/include_reason을 사용한다.
    if metric_key == "contextual_relevancy":
        # 검색결과에 불필요한 내용이 많은가?
        return ContextualRelevancyMetric(threshold=0.7, include_reason=True)
    if metric_key == "faithfulness":
        # 답변의 주장이 검색 문서에 근거하는가?
        return FaithfulnessMetric(threshold=0.7, include_reason=True)

    raise NotImplementedError(f"아직 구현하지 않은 metric입니다: {metric_key}")


def check_exercise() -> None:
    """judge를 호출하지 않고 선택과 test-case field를 점검한다."""
    errors: list[str] = []
    expected_scenarios = set(SCENARIOS)

    if set(SELECTED_METRICS) != expected_scenarios:
        errors.append("SELECTED_METRICS의 scenario key를 변경하지 마세요.")

    selected_values = set(SELECTED_METRICS.values())
    invalid_metric_keys = selected_values - METRIC_KEYS
    if invalid_metric_keys:
        errors.append(f"유효하지 않은 metric key: {sorted(invalid_metric_keys)}")
    if selected_values != METRIC_KEYS:
        errors.append("세 표준 메트릭을 각각 정확히 한 번 선택하세요.")

    for metric_key in METRIC_KEYS:
        action = FIX_ACTIONS.get(metric_key, "")
        if not action or action == "TODO":
            errors.append(f"{metric_key}의 FIX_ACTIONS를 작성하세요.")
        try:
            make_metric(metric_key)
        except NotImplementedError:
            errors.append(f"make_metric()에 {metric_key} 생성자를 구현하세요.")

    for scenario_key, metric_key in SELECTED_METRICS.items():
        case = SCENARIOS[scenario_key]
        if metric_key == "answer_relevancy" and not case.actual_output:
            errors.append(f"{scenario_key}: actual_output이 필요합니다.")
        if metric_key in {"faithfulness", "contextual_relevancy"}:
            if not case.actual_output or not case.retrieval_context:
                errors.append(
                    f"{scenario_key}: actual_output과 retrieval_context가 필요합니다."
                )

    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise SystemExit(f"아직 완료되지 않은 항목이 있습니다:\n{details}")

    print("구조 검사 통과: 이제 --run으로 점수와 reason을 관찰하세요.")


def run_evaluation() -> None:
    """결함마다 선택한 메트릭 하나만 실행해 진단 신호를 관찰한다."""
    check_exercise()

    for scenario_key, test_case in SCENARIOS.items():
        metric_key = SELECTED_METRICS[scenario_key]
        metric = make_metric(metric_key)
        metric.measure(test_case)

        print(f"\n[{scenario_key}] {test_case.name}")
        print(f"선택 metric: {metric_key}")
        print(f"score: {metric.score} / threshold: {metric.threshold}")
        print(f"reason: {metric.reason}")
        print(f"낮을 때 수정 행동: {FIX_ACTIONS[metric_key]}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="2주차 세션 1 메트릭 선택 실습")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="API 호출 없는 구조 검사")
    mode.add_argument("--run", action="store_true", help="LLM judge 평가 실행")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.check:
        check_exercise()
    else:
        run_evaluation()
