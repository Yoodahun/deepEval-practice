"""3주차 세션 3: ``EvaluationDataset``과 JSONL의 API 없는 검증.

이 파일은 앱 답변 품질이나 LLM judge를 검사하지 않는다. JSONL을 읽어 정적
reference의 신뢰 조건을 먼저 검사하고, 같은 파일에서 DeepEval dataset을
재구성한다.

실행 순서:

1. 경로와 JSONL 구조만 확인한다.

   .venv/bin/python -m pytest \
       tests/evals/test_week3_session3_local_dataset.py::test_jsonl_has_one_golden_per_line -v

2. 데이터 계약을 확인한다.

   .venv/bin/python -m pytest \
       tests/evals/test_week3_session3_local_dataset.py -k "reference or metadata or runtime or sensitive" -v

3. DeepEval loader와 single-turn 제약까지 전체 검사한다.

   .venv/bin/python -m pytest \
       tests/evals/test_week3_session3_local_dataset.py -v

외부 API와 LLM judge는 호출하지 않는다.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Final

from deepeval.dataset import EvaluationDataset, Golden
from deepeval.dataset.golden import ConversationalGolden


PROJECT_ROOT: Final = Path(__file__).resolve().parents[2]
DATASET_PATH: Final = PROJECT_ROOT / "evals" / "data" / "refund_goldens.jsonl"

REQUIRED_METADATA: Final = frozenset(
    {
        "case_id",
        "category",
        "protected_risk",
        "suspected_component",
        "suite",
        "review_status",
        "bug_status",
    }
)
RUNTIME_FIELDS: Final = frozenset(
    {"actual_output", "retrieval_context", "tools_called"}
)
CONVERSATIONAL_FIELDS: Final = frozenset(
    {"turns", "scenario", "expected_outcome", "user_description"}
)
SENSITIVE_VALUE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b01[016789][ -]?\d{3,4}[ -]?\d{4}\b"),
    re.compile(r"(?<!\d)(?:\d[ -]?){15,16}(?!\d)"),
)


def iter_jsonl(path: Path = DATASET_PATH) -> Iterator[dict[str, Any]]:
    """빈 줄을 허용하지 않고 JSONL의 각 행을 object로 읽는다."""
    with path.open(encoding="utf-8") as dataset_file:
        for line_number, line in enumerate(dataset_file, start=1):
            if not line.strip():
                raise ValueError(f"{line_number}행이 비어 있습니다.")

            row = json.loads(line)
            if not isinstance(row, dict):
                raise TypeError(f"{line_number}행은 JSON object여야 합니다.")
            yield row


def load_dataset(path: Path = DATASET_PATH) -> EvaluationDataset:
    """현재 작업 디렉터리와 무관하게 로컬 JSONL을 DeepEval로 로드한다."""
    dataset = EvaluationDataset()
    dataset.add_goldens_from_jsonl_file(file_path=str(path))
    return dataset


def make_dataset(rows: list[dict[str, Any]]) -> EvaluationDataset:
    """JSON object를 명시적으로 ``Golden`` 목록으로 바꿔 dataset을 만든다."""
    golden_list = [
        Golden(
            input=row["input"],
            expected_output=row["expected_output"],
            context=row["context"],
            additional_metadata=row["additional_metadata"]
        )
        for row in rows
    ]

    return EvaluationDataset(goldens=golden_list)


def non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def test_dataset_path_is_resolved_from_project_root(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    assert DATASET_PATH.is_file()
    assert len(list(iter_jsonl())) == 10


def test_jsonl_has_one_golden_per_line() -> None:
    raw_lines = DATASET_PATH.read_text(encoding="utf-8").splitlines()
    rows = list(iter_jsonl())

    assert len(raw_lines) == len(rows) == 10
    assert all(isinstance(row, dict) for row in rows)


def test_reference_fields_are_present_and_non_empty() -> None:
    for row in iter_jsonl():
        case_id = row.get("additional_metadata", {}).get("case_id", "unknown")

        # 빈 입력 자체를 보호하는 Golden은 허용하지만 key와 타입은 필수다.
        assert isinstance(row.get("input"), str), f"{case_id}: input"
        assert non_empty_string(row.get("expected_output")), (
            f"{case_id}: expected_output"
        )
        assert isinstance(row.get("context"), list) and row["context"], (
            f"{case_id}: context"
        )
        assert all(non_empty_string(item) for item in row["context"]), (
            f"{case_id}: context item"
        )


def test_metadata_is_complete_approved_and_unique() -> None:
    case_ids: list[str] = []

    for row in iter_jsonl():
        metadata = row.get("additional_metadata")
        assert isinstance(metadata, dict)
        assert REQUIRED_METADATA <= metadata.keys()
        assert all(non_empty_string(metadata[key]) for key in REQUIRED_METADATA)
        assert metadata["review_status"] == "approved"
        case_ids.append(metadata["case_id"])

    assert len(case_ids) == len(set(case_ids))


def test_runtime_observations_are_not_stored_in_goldens() -> None:
    for row in iter_jsonl():
        assert RUNTIME_FIELDS.isdisjoint(row)


def test_dataset_contains_only_single_turn_goldens() -> None:
    rows = list(iter_jsonl())
    dataset = load_dataset()

    assert all(CONVERSATIONAL_FIELDS.isdisjoint(row) for row in rows)
    assert len(dataset.goldens) == len(rows)
    assert all(isinstance(golden, Golden) for golden in dataset.goldens)
    assert not any(
        isinstance(golden, ConversationalGolden) for golden in dataset.goldens
    )


def test_deepeval_dataset_preserves_reference_and_case_ids() -> None:
    rows = list(iter_jsonl())
    constructed_dataset = make_dataset(rows)
    loaded_dataset = load_dataset()

    expected_case_ids = [row["additional_metadata"]["case_id"] for row in rows]
    constructed_case_ids = [
        golden.additional_metadata["case_id"]
        for golden in constructed_dataset.goldens
    ]
    loaded_case_ids = [
        golden.additional_metadata["case_id"]
        for golden in loaded_dataset.goldens
    ]

    assert constructed_case_ids == loaded_case_ids == expected_case_ids
    assert all(golden.expected_output for golden in loaded_dataset.goldens)
    assert all(golden.context for golden in loaded_dataset.goldens)


def test_dataset_has_no_obvious_sensitive_values() -> None:
    serialized_rows = "\n".join(
        json.dumps(row, ensure_ascii=False) for row in iter_jsonl()
    )

    for pattern in SENSITIVE_VALUE_PATTERNS:
        assert pattern.search(serialized_rows) is None
