"""3주차 세션 4 parameterized dataset regression의 참고 답안.

학생용 파일의 TODO 1~5를 완성한 뒤 비교한다. 외부 API나 judge를 호출하지 않는다.

    .venv/bin/python -m pytest \
        tests/evals/week3_session4_dataset_regression_solution.py -v
"""

from __future__ import annotations

import re
from typing import Any, Final

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
    metadata = golden.additional_metadata
    assert isinstance(metadata, dict)
    case_id = metadata.get("case_id")
    assert isinstance(case_id, str) and case_id.strip()
    return case_id


def marks_for(golden: Golden) -> list[Any]:
    metadata = golden.additional_metadata
    assert isinstance(metadata, dict)

    marks: list[Any] = [pytest.mark.full]
    if metadata.get("suite") == "smoke":
        marks.append(pytest.mark.smoke)
    if metadata.get("category") == "known_bug":
        marks.append(pytest.mark.known_bug)
    if metadata.get("bug_status") == "active":
        marks.append(
            pytest.mark.xfail(
                reason="아직 수정되지 않은 known bug",
                strict=False,
            )
        )
    return marks


def make_golden_params(goldens: list[Golden]) -> list[Any]:
    return [
        pytest.param(
            golden,
            id=case_id_for(golden),
            marks=marks_for(golden),
        )
        for golden in goldens
    ]


GOLDEN_PARAMS: Final = make_golden_params(GOLDENS)


def make_runtime_test_case(golden: Golden) -> LLMTestCase:
    actual_output, retrieval_context = answer_refund_question(golden.input)
    return LLMTestCase(
        input=golden.input,
        actual_output=actual_output,
        expected_output=golden.expected_output,
        context=golden.context,
        retrieval_context=retrieval_context,
        metadata=golden.additional_metadata,
    )


def assert_runtime_contract(golden: Golden, test_case: LLMTestCase) -> None:
    assert test_case.input == golden.input
    assert test_case.expected_output == golden.expected_output
    assert test_case.context == golden.context
    assert test_case.metadata == golden.additional_metadata

    assert isinstance(test_case.actual_output, str)
    assert test_case.actual_output.strip()
    assert isinstance(test_case.retrieval_context, list)
    assert all(
        isinstance(document, str) and document.strip()
        for document in test_case.retrieval_context
    )
    assert all(
        pattern.search(test_case.actual_output) is None
        for pattern in SENSITIVE_VALUE_PATTERNS
    )


def assert_parameter_contract(golden: Golden, request: pytest.FixtureRequest) -> None:
    metadata = golden.additional_metadata
    assert isinstance(metadata, dict)
    assert request.node.callspec.id == metadata["case_id"]

    marker_names = {marker.name for marker in request.node.iter_markers()}
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
    assert_parameter_contract(golden, request)
    test_case = make_runtime_test_case(golden)
    assert_runtime_contract(golden, test_case)


def test_active_known_bug_is_non_blocking_until_fixed() -> None:
    source = next(
        golden
        for golden in GOLDENS
        if golden.additional_metadata["category"] == "known_bug"
    )
    active_golden = source.model_copy(deep=True)
    active_golden.additional_metadata["bug_status"] = "active"

    marker_names = {mark.name for mark in marks_for(active_golden)}

    assert {"full", "known_bug", "xfail"} <= marker_names
