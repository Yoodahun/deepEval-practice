"""2주차 세션 1 메트릭 선택 실습의 참고 답안.

학생용 파일의 --check를 통과시킨 뒤 비교한다.

    python tests/evals/week2_session1_metric_selection_solution.py --check
    python tests/evals/week2_session1_metric_selection_solution.py --run

--run은 LLM judge API를 호출한다.
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


QUESTION: Final = "지난주에 산 상품을 환불하려면 어떻게 해야 하나요?"
CLEAN_RETRIEVAL_CONTEXT: Final = [
    (
        "구매 후 30일 이내에는 주문 번호와 함께 고객센터에 요청하면 "
        "전액 환불할 수 있습니다."
    )
]
NOISY_RETRIEVAL_CONTEXT: Final = [
    *CLEAN_RETRIEVAL_CONTEXT,
    "일반 배송은 결제 완료 후 평균 2~3일이 걸립니다.",
    "회원 등급은 최근 12개월의 구매 금액을 기준으로 산정합니다.",
    "선물 포장은 주문서의 옵션 메뉴에서 추가할 수 있습니다.",
]

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

SELECTED_METRICS: Final = {
    "off_topic_answer": "answer_relevancy",
    "unsupported_claim": "faithfulness",
    "noisy_retrieval": "contextual_relevancy",
}

FIX_ACTIONS: Final = {
    "answer_relevancy": (
        "generator prompt와 출력에서 질문에 무관한 설명을 줄인다."
    ),
    "faithfulness": (
        "generator가 retrieval_context 밖의 주장을 만들지 않도록 grounding 지시를 강화한다."
    ),
    "contextual_relevancy": (
        "retriever의 top-k나 검색 조건을 조정해 무관한 chunk를 줄인다."
    ),
}


def make_metric(metric_key: str) -> BaseMetric:
    if metric_key == "answer_relevancy":
        return AnswerRelevancyMetric(threshold=0.7, include_reason=True)
    if metric_key == "faithfulness":
        return FaithfulnessMetric(threshold=0.7, include_reason=True)
    if metric_key == "contextual_relevancy":
        return ContextualRelevancyMetric(threshold=0.7, include_reason=True)
    raise ValueError(f"지원하지 않는 metric key입니다: {metric_key}")


def check_solution() -> None:
    expected_types = {
        "answer_relevancy": AnswerRelevancyMetric,
        "faithfulness": FaithfulnessMetric,
        "contextual_relevancy": ContextualRelevancyMetric,
    }
    for metric_key, expected_type in expected_types.items():
        metric = make_metric(metric_key)
        assert isinstance(metric, expected_type)

    assert len(set(SELECTED_METRICS.values())) == 3
    assert all(action.strip() for action in FIX_ACTIONS.values())
    print("참고 답안 구조 검사 통과")


def run_evaluation() -> None:
    check_solution()
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
    parser = argparse.ArgumentParser(description="2주차 세션 1 참고 답안")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="API 호출 없는 구조 검사")
    mode.add_argument("--run", action="store_true", help="LLM judge 평가 실행")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.check:
        check_solution()
    else:
        run_evaluation()
