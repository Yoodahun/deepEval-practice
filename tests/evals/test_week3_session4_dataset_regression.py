"""3주차 세션 4: parameterized dataset regression - 학생용 실습.

세션 3의 JSONL을 현재 앱 callback에 연결한다. TODO 1~5를 순서대로 완성하면
외부 API나 LLM judge 없이 10개 Golden의 runtime 계약을 검사할 수 있다.

실행 순서:

    # TODO를 시작하기 전 수집 결과와 ID를 관찰한다.
    .venv/bin/python -m pytest \
        tests/evals/test_week3_session4_dataset_regression.py --collect-only -q

    # TODO 1~3: case_id와 marker 배선(10개 ID와 subset 개수 확인)
    .venv/bin/python -m pytest \
        tests/evals/test_week3_session4_dataset_regression.py -m full --collect-only -q

    .venv/bin/python -m pytest \
        tests/evals/test_week3_session4_dataset_regression.py -m smoke --collect-only -q

    # TODO 4~5: 앱 실행 결과를 LLMTestCase로 만들고 결정적으로 검사
    .venv/bin/python -m pytest \
        tests/evals/test_week3_session4_dataset_regression.py -v

    # subset 수집: smoke 5개, known_bug 2개, full 10개
    .venv/bin/python -m pytest \
        tests/evals/test_week3_session4_dataset_regression.py -m smoke --collect-only -q

참고 답안은 직접 완성한 뒤 비교한다.

    .venv/bin/python -m pytest \
        tests/evals/week3_session4_dataset_regression_solution.py -v
"""

from __future__ import annotations

import re
from typing import Any, Final, List

import pytest
from deepeval.dataset import Golden
from deepeval.test_case import LLMTestCase

from app.refund_support import answer_refund_question
from tests.evals.test_week3_session3_local_dataset import load_dataset


GOLDENS: Final[list[Golden]] = load_dataset().goldens
SENSITIVE_VALUE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b01[016789][ -]?\d{3,4}[ -]?\d{4}\b"),
    re.compile(r"(?<!\d)(?:\d[ -]?){15,16}(?!\d)"),
)


def case_id_for(golden: Golden) -> str:
    """pytest 리포트와 JSONL 행을 연결할 안정적인 ID를 반환한다."""
    # TODO 1: golden.additional_metadata에서 case_id를 꺼내 반환하세요.
    # 힌트: metadata가 dict인지, case_id가 비어 있지 않은 str인지 assert하면
    # 잘못된 데이터가 pytest의 숫자 ID로 조용히 넘어가는 것을 막을 수 있습니다.

    return golden.additional_metadata["case_id"]


def marks_for(golden: Golden) -> list[Any]:
    """Golden metadata를 실제 pytest marker로 변환한다."""
    # TODO 2: 아래 규칙으로 marker 목록을 만드세요.
    # - 모든 Golden: pytest.mark.full
    # - suite == "smoke": pytest.mark.smoke 추가
    # - category == "known_bug": pytest.mark.known_bug 추가
    # - bug_status == "active": strict=False인 pytest.mark.xfail 추가
    # fixed known bug는 재발을 막아야 하므로 xfail로 만들면 안 됩니다.
    marker_list: list[Any] = [pytest.mark.full]

    if golden.additional_metadata["suite"] == "smoke":
        marker_list.append(pytest.mark.smoke)
    if golden.additional_metadata["category"] == "known_bug":
        marker_list.append(pytest.mark.known_bug)
    if golden.additional_metadata["bug_status"] == "active":
        marker_list.append(pytest.mark.xfail(strict=False))

    return marker_list


def make_golden_params(goldens: list[Golden]) -> list[Any]:
    """Golden을 안정적인 ID와 marker가 달린 pytest parameter로 바꾼다."""
    # TODO 3: 각 Golden을 pytest.param으로 감싸세요.
    # 힌트: pytest.param(golden, id=case_id_for(golden), marks=marks_for(golden))
    # 숫자 index나 Golden의 긴 repr를 ID로 사용하지 않습니다.
    return [pytest.param(golden, id=case_id_for(golden=golden), marks=marks_for(golden=golden)) for golden in goldens]


GOLDEN_PARAMS: Final = make_golden_params(GOLDENS)


def make_runtime_test_case(golden: Golden) -> LLMTestCase:
    """
    정적 Golden과 현재 앱의 runtime observation을 결합한다.
    런타임으로 테스트케이스를 생성한다.
    Golden reference로 부터 input / expected_output / context / metadata 를 받고
    실제 앱을 실행하여  actual_output / retrieval_context 를 받아
    이것을 하나의 테스트케이스로 생성한다.
    """
    # TODO 4:
    # 1. golden.input으로 answer_refund_question()을 호출하세요.
    # 2. callback의 답변과 문서를 actual_output, retrieval_context에 넣으세요.
    # 3. expected_output과 context는 Golden의 정적 reference를 그대로 넣으세요.
    # 4. 추적을 위해 additional_metadata를 LLMTestCase.metadata에 전달하세요.
    actual_ouput, retrieve_context = answer_refund_question(question=golden.input)


    return LLMTestCase(
        input=golden.input,
        actual_output=actual_ouput,
        retrieval_context=retrieve_context,
        expected_output=golden.expected_output,
        context=golden.context,
        metadata=golden.additional_metadata,
    )





def assert_runtime_contract(golden: Golden, test_case: LLMTestCase) -> None:
    """judge 전에 모든 Golden에 적용할 싸고 결정적인 계약을 검사한다."""
    # TODO 5: 아래 계약을 일반 pytest assert로 작성하세요.
    # - input/expected_output/context/metadata가 Golden에서 그대로 전달되었다.
    # - actual_output은 공백이 아닌 str이다.
    # - retrieval_context는 list[str]이다(빈 목록은 unknown 입력에서 허용).
    # - actual_output에 SENSITIVE_VALUE_PATTERNS와 일치하는 값이 없다.
    assert test_case.input == golden.input
    assert test_case.expected_output == golden.expected_output
    assert test_case.context == golden.context
    assert test_case.metadata == golden.additional_metadata

    assert isinstance(test_case.actual_output, str)
    assert test_case.actual_output.strip()
    assert isinstance(test_case.retrieval_context, list)
    assert all(isinstance(document, str) and document.strip() for document in test_case.retrieval_context)


    assert all(pattern.search(test_case.actual_output) is None for pattern in SENSITIVE_VALUE_PATTERNS)


def assert_parameter_contract(golden: Golden, request: pytest.FixtureRequest) -> None:
    """TODO 1~3의 ID와 marker 변환 결과를 검증한다."""
    metadata = golden.additional_metadata
    assert isinstance(metadata, dict)

    assert request.node.callspec.id == metadata["case_id"]

    marker_names = {marker.name for marker in request.node.iter_markers()}
    print(marker_names)
    assert "full" in marker_names
    if metadata["suite"] == "smoke":
        assert "smoke" in marker_names
    if metadata["category"] == "known_bug":
        assert "known_bug" in marker_names
    if metadata["bug_status"] == "fixed":
        assert "xfail" not in marker_names


@pytest.mark.parametrize("golden", GOLDEN_PARAMS)
def test_refund_dataset_runtime_contract(
    golden: Golden,
    request: pytest.FixtureRequest,
) -> None:
    """같은 평가 절차를 모든 reviewed Golden에 적용한다."""
    assert_parameter_contract(golden, request)
    test_case = make_runtime_test_case(golden)
    assert_runtime_contract(golden, test_case)


def test_active_known_bug_is_non_blocking_until_fixed() -> None:
    """active known bug만 xfail이고 fixed regression은 blocking인지 확인한다."""
    source = next(
        golden
        for golden in GOLDENS
        if golden.additional_metadata["category"] == "known_bug"
    )
    active_golden = source.model_copy(deep=True)
    active_golden.additional_metadata["bug_status"] = "active"

    marker_names = {mark.name for mark in marks_for(active_golden)}

    assert {"full", "known_bug", "xfail"} <= marker_names
