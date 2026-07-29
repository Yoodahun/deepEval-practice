"""1주차 세션 4: 결정적 assertion과 의미 기반 eval 분리 실습.

고객지원 앱이 JSON 문자열을 반환한다고 가정한다. 응답 형식처럼 정답이
명확한 조건은 pytest로 검사하고, 문장의 의미와 품질은 LLM judge로 검사한다.

실행 방법:

    # API 호출 없이 결정적 계약만 검사
    pytest tests/evals/test_week1_session4_deterministic_vs_semantic.py::\
        test_deterministic_response_contract -v

    # parse, key, length 중 하나가 실패하는 모습을 확인
    DEEPEVAL_SESSION4_CONTRACT_FAIL=parse pytest \
        tests/evals/test_week1_session4_deterministic_vs_semantic.py::\
        test_deterministic_response_contract -v

    # 결정적 검사와 의미 기반 검사 모두 실행(LLM judge API 호출)
    deepeval test run \
        tests/evals/test_week1_session4_deterministic_vs_semantic.py -v

    # 형식은 정상이지만 의미 품질이 나쁜 답변을 judge가 잡는지 확인
    DEEPEVAL_SESSION4_SEMANTIC_FAIL=1 deepeval test run \
        tests/evals/test_week1_session4_deterministic_vs_semantic.py -v
"""

import json
import os
from json import JSONDecodeError
from typing import Any

import pytest
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams


QUESTION = "지난주에 구매한 상품을 환불하고 싶어요. 어떻게 해야 하나요?"
POLICY_CONTEXT = (
    "구매 후 30일 이내에는 주문 번호와 함께 고객센터에 요청하면 전액 환불할 "
    "수 있습니다. 환불 처리에는 영업일 기준 3~5일이 걸립니다."
)
EXPECTED_OUTPUT = (
    "구매 후 30일 이내이므로 주문 번호를 준비해 고객센터에 환불을 요청하세요. "
    "처리는 영업일 기준 3~5일 걸립니다."
)
MAX_ANSWER_LENGTH = 200
REQUIRED_KEYS = {"answer", "source", "escalate"}


VALID_RESPONSE = json.dumps(
    {
        "answer": (
            "지난주 구매 건은 30일 이내이므로 환불할 수 있습니다. 주문 번호를 "
            "준비해 고객센터에 요청해 주세요. 처리는 영업일 기준 3~5일 걸립니다."
        ),
        "source": "환불 정책",
        "escalate": False,
    },
    ensure_ascii=False,
)

# 세 출력 모두 '의미를 평가하기 전에' 코드만으로 실패를 확정할 수 있다.
INVALID_CONTRACT_RESPONSES = {
    "parse": '{"answer": "닫는 중괄호가 없는 JSON"',
    "key": json.dumps(
        {"answer": "환불할 수 있습니다.", "source": "환불 정책"},
        ensure_ascii=False,
    ),
    "length": json.dumps(
        {
            "answer": "가" * (MAX_ANSWER_LENGTH + 1),
            "source": "환불 정책",
            "escalate": False,
        },
        ensure_ascii=False,
    ),
}

# JSON 형식, 필수 key, 길이는 모두 정상이지만 질문과 정책에는 어긋난다.
SEMANTICALLY_BAD_RESPONSE = json.dumps(
    {
        "answer": "환불은 절대 불가능합니다. 다른 질문을 해 주세요.",
        "source": "환불 정책",
        "escalate": False,
    },
    ensure_ascii=False,
)


def parse_json_object(raw_response: str) -> dict[str, Any]:
    """파싱 실패를 judge 점수가 아닌 명확한 테스트 실패로 보고한다."""
    try:
        payload = json.loads(raw_response)
    except JSONDecodeError as error:
        pytest.fail(f"응답이 유효한 JSON이 아닙니다: {error.msg}")

    assert isinstance(payload, dict), "최상위 JSON 값은 object여야 합니다."
    return payload


def assert_deterministic_contract(raw_response: str) -> dict[str, Any]:
    """코드로 정확히 판정할 수 있는 세 가지 제품 계약을 검증한다."""
    # 1. JSON 파싱이 가능해야 한다.
    payload = parse_json_object(raw_response)

    # 2. 소비자가 의존하는 필수 key가 모두 있어야 한다.
    missing_keys = REQUIRED_KEYS - payload.keys()
    assert not missing_keys, f"필수 key가 없습니다: {sorted(missing_keys)}"

    # 3. UI에 표시할 답변은 정해진 길이를 넘지 않아야 한다.
    answer = payload["answer"]
    assert isinstance(answer, str), "answer는 문자열이어야 합니다."
    assert len(answer) <= MAX_ANSWER_LENGTH, (
        f"answer가 {MAX_ANSWER_LENGTH}자를 초과했습니다: {len(answer)}자"
    )
    return payload


def make_semantic_metrics() -> list[GEval]:
    """품질 차원마다 이유와 threshold를 따로 관찰할 수 있게 분리한다."""

    # 관련성
    relevance = GEval(
        name="Question relevance",
        criteria=(
            "Evaluate whether the actual output directly addresses the user's "
            "refund question without irrelevant content."
        ),
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
        ],
        threshold=0.7,
    )

    # 도움성
    helpfulness = GEval(
        name="Actionable helpfulness",
        criteria=(
            "Evaluate whether the actual output gives the user clear, useful next "
            "steps and communicates the important processing time. Use the expected "
            "output as a reference; exact wording is not required."
        ),
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        threshold=0.7,
    )

    # 근거 성
    groundedness = GEval(
        name="Policy groundedness",
        criteria=(
            "Evaluate whether every factual claim in the actual output is supported "
            "by the provided context and does not contradict it."
        ),
        evaluation_params=[
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.CONTEXT,
        ],
        threshold=0.7,
    )
    return [relevance, helpfulness, groundedness]


def test_deterministic_response_contract() -> None:
    """빠르고 재현 가능한 형식 검사는 일반 pytest assertion이 담당한다."""
    failure_kind = os.getenv("DEEPEVAL_SESSION4_CONTRACT_FAIL")
    raw_response = INVALID_CONTRACT_RESPONSES.get(failure_kind, VALID_RESPONSE)

    assert_deterministic_contract(raw_response)


def test_semantic_answer_quality() -> None:
    """표현이 달라도 의미상 합격할 수 있는 조건만 LLM judge에 맡긴다."""
    should_fail = os.getenv("DEEPEVAL_SESSION4_SEMANTIC_FAIL") == "1"
    raw_response = SEMANTICALLY_BAD_RESPONSE if should_fail else VALID_RESPONSE

    # judge에게 JSON 직렬화 방식까지 평가시키지 않고 사용자에게 보이는 답변만 준다.
    payload = assert_deterministic_contract(raw_response)
    test_case = LLMTestCase(
        name="refund-support-semantic-quality",
        input=QUESTION,
        actual_output=payload["answer"],
        expected_output=EXPECTED_OUTPUT,
        context=[POLICY_CONTEXT],
    )

    assert_test(test_case, make_semantic_metrics())
