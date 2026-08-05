"""3주차 세션 1: 평가 가능한 최소 환불 고객지원 앱.

이 파일은 외부 LLM이나 벡터 데이터베이스 없이 retriever와 generator의
경계를 연습하기 위한 학생용 실습이다. 아래 순서로 TODO를 완성한다.

1. ``retrieve_policy()``에서 질문과 관련된 정책 문서를 고른다.
2. ``generate_answer()``에서 검색 문서만 사용해 답변을 만든다.
3. ``answer_refund_question()``에서 두 함수를 연결한다.

실행할 계약 테스트:

    .venv/bin/python -m pytest \
        tests/evals/test_week3_session1_refund_app_contract.py -v

처음에는 ``NotImplementedError``로 실패하는 것이 정상이다. 계약 테스트를 하나씩
실행하며 retriever, generator, callback 순서로 구현한다.
"""

from __future__ import annotations

from typing import Final, TypedDict


class PolicyDocument(TypedDict):
    """검색에 필요한 키워드와 사용자에게 보여 줄 정책 문장을 묶는다."""

    document_id: str
    keywords: tuple[str, ...]
    text: str


POLICY_DOCUMENTS: Final[tuple[PolicyDocument, ...]] = (
    {
        "document_id": "refund-window",
        "keywords": ("환불", "반품", "기간", "며칠", "언제까지", "지난주"),
        "text": "구매 후 30일 이내에는 전액 환불을 요청할 수 있습니다.",
    },
    {
        "document_id": "refund-channel",
        "keywords": ("환불", "반품", "요청", "방법", "고객센터"),
        "text": "환불은 고객센터를 통해 요청해야 합니다.",
    },
    {
        "document_id": "refund-required-info",
        "keywords": ("환불", "반품", "필요", "정보", "준비", "주문 번호"),
        "text": "환불 요청에는 주문 번호와 구매일이 필요합니다.",
    },
    {
        "document_id": "refund-privacy",
        "keywords": ("카드", "비밀번호", "개인정보", "본인 확인"),
        "text": "환불 접수 시 카드 비밀번호나 전체 카드 번호를 요구하지 않습니다.",
    },
)

UNKNOWN_RESPONSE: Final = (
    "확인된 환불 정책에서 답을 찾지 못했습니다. 고객센터에 문의해 주세요."
)


def retrieve_policy(question: str) -> list[str]:
    """
    질문에 키워드가 포함된 정책을 원래 정책 순서대로 반환한다.

    최소 앱이므로 형태소 분석이나 벡터 검색 대신 단순 부분 문자열 매칭을 쓴다.
    빈 입력이나 일치하는 정책이 없는 입력은 빈 목록을 반환해야 한다.
    """
    # TODO 1: question의 앞뒤 공백을 제거하고 소문자로 바꾼 뒤,
    # 각 문서의 keywords 중 하나라도 포함되면 text를 결과에 추가하세요.
    # 힌트: any(keyword in normalized_question for keyword in document["keywords"])
    normalized_question = question.strip().lower()
    return [
        document["text"]
        for document in POLICY_DOCUMENTS
        if any(
            keyword in normalized_question for keyword in document["keywords"]
        )
    ]


def generate_answer(question: str, documents: list[str]) -> str:
    """
    검색된 정책 문서만으로 결정적인 답변 문자열을 만든다.

    이 단계에서는 자연스러운 LLM 답변보다 grounding 경계를 분명히 하는 것이
    중요하다. 문서가 없거나 질문이 비어 있으면 ``UNKNOWN_RESPONSE``를 반환한다.
    """
    # TODO 2: 빈 질문 또는 빈 documents를 먼저 처리하세요.
    # 문서가 있으면 "확인된 환불 정책입니다. " 뒤에 문서를 공백으로 연결하세요.

    if not question or not documents:
        return UNKNOWN_RESPONSE

    return f"확인된 환불 정책입니다. {''.join(documents)}"


def answer_refund_question(question: str) -> tuple[str, list[str]]:
    """현재 앱을 실행해 ``(actual_output, retrieval_context)``를 반환한다."""
    # TODO 3: retrieve_policy()의 결과를 generate_answer()에 전달하고,
    # 생성한 답변과 검색 문서를 tuple로 반환하세요.

    return (
        generate_answer(question=question, documents=retrieve_policy(question)),
        retrieve_policy(question),
    )
