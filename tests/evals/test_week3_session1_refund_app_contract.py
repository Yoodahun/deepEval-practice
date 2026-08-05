"""3주차 세션 1 최소 고객지원 앱의 API 없는 계약 테스트.

학생용 ``app/refund_support.py``의 TODO를 완성하며 아래 테스트를 하나씩
통과시킨다. 이 세션에서는 DeepEval metric이나 외부 LLM judge를 호출하지 않는다.

    .venv/bin/python -m pytest \
        tests/evals/test_week3_session1_refund_app_contract.py -v
"""

from __future__ import annotations

from app.refund_support import (
    UNKNOWN_RESPONSE,
    answer_refund_question,
    generate_answer,
    retrieve_policy,
)


def test_retriever_returns_relevant_policy_documents() -> None:
    documents = retrieve_policy("지난주 구매한 상품은 언제까지 환불할 수 있나요?")

    assert isinstance(documents, list)
    assert documents
    assert all(isinstance(document, str) for document in documents)
    assert any("30일" in document for document in documents)
    assert any("고객센터" in document for document in documents)


def test_generator_uses_supplied_documents() -> None:
    documents = ["테스트 정책 A입니다.", "테스트 정책 B입니다."]

    actual_output = generate_answer("환불 방법을 알려 주세요.", documents)

    assert isinstance(actual_output, str)
    assert actual_output.strip()
    assert all(document in actual_output for document in documents)


def test_callback_returns_runtime_observation() -> None:
    actual_output, retrieval_context = answer_refund_question(
        "환불할 때 어떤 정보를 준비해야 하나요?"
    )

    assert isinstance(actual_output, str)
    assert actual_output.strip()
    assert isinstance(retrieval_context, list)
    assert retrieval_context
    assert all(isinstance(document, str) for document in retrieval_context)
    assert any("주문 번호" in document for document in retrieval_context)


def test_unknown_question_returns_explicit_unknown_response() -> None:
    actual_output, retrieval_context = answer_refund_question(
        "회원 등급은 어떻게 올라가나요?"
    )

    assert actual_output == UNKNOWN_RESPONSE
    assert retrieval_context == []


def test_empty_input_returns_defined_response() -> None:
    actual_output, retrieval_context = answer_refund_question("   ")

    assert actual_output == UNKNOWN_RESPONSE
    assert retrieval_context == []
