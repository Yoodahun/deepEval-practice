"""3주차 세션 2: reviewed Golden 설계 - 학생용 실습.

이 세션에서는 DeepEval이나 LLM judge를 실행하지 않는다. 사람이 검토한
reference 후보를 5개 smoke Golden으로 고른 뒤 10개로 확장하고, 주차 종료 때
20개가 될 category coverage를 설계한다.

진행 순서:

1. 후보와 review 상태를 먼저 읽는다.

   .venv/bin/python \
       tests/evals/week3_session2_golden_design_exercise.py --show-queue

2. TODO 1에서 smoke 5개를 완성한다.
3. TODO 2에서 reviewed Golden을 10개로 확장한다.
4. TODO 3에서 20개 dataset의 category별 목표 개수를 정한다.
5. TODO 4에서 승인된 reference만 Golden으로 승격하는 함수를 완성한다.
6. API 호출 없는 검사를 통과시킨다.

   .venv/bin/python \
       tests/evals/week3_session2_golden_design_exercise.py --check

7. 현재 10개와 최종 20개 사이의 coverage 차이를 확인한다.

   .venv/bin/python \
       tests/evals/week3_session2_golden_design_exercise.py --show-coverage

막히면 먼저 ``refund-known-bug-001`` 예시와 같은 방식으로 metadata를 작성한다.
정답 파일은 직접 검사를 통과시킨 뒤에 비교한다.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, replace
from typing import Callable, Final, Literal, Mapping


ReviewStatus = Literal["unreviewed", "approved", "rejected"]
Category = Literal[
    "normal",
    "boundary",
    "known_bug",
    "safety_policy",
    "unknown_or_invalid_input",
]
Suite = Literal["smoke", "full"]
BugStatus = Literal["active", "fixed", "not_applicable"]

CATEGORIES: Final[tuple[Category, ...]] = (
    "normal",
    "boundary",
    "known_bug",
    "safety_policy",
    "unknown_or_invalid_input",
)
RUNTIME_FIELDS: Final = frozenset(
    {"actual_output", "retrieval_context", "tools_called"}
)


@dataclass(frozen=True)
class ReferenceCandidate:
    """review queue에 있는 정적 reference 후보."""

    candidate_id: str
    input: str
    expected_output: str
    context: tuple[str, ...]
    review_status: ReviewStatus
    source_sample_id: str | None = None
    stored_runtime_fields: frozenset[str] = frozenset()


@dataclass(frozen=True)
class GoldenMetadata:
    """회귀 실패를 원인 조사 경로에 연결하는 metadata."""

    case_id: str
    category: Category
    protected_risk: str
    suspected_component: str
    suite: Suite
    review_status: ReviewStatus
    bug_status: BugStatus


@dataclass(frozen=True)
class ReviewedGolden:
    """승인이 끝난 정적 reference. runtime observation은 포함하지 않는다."""

    input: str
    expected_output: str
    context: tuple[str, ...]
    metadata: GoldenMetadata
    source_sample_id: str | None = None


REFERENCE_CANDIDATES: Final[dict[str, ReferenceCandidate]] = {
    "refund-known-bug-001": ReferenceCandidate(
        candidate_id="refund-known-bug-001",
        input="지난주에 산 상품을 환불하려면 어떻게 해야 하나요?",
        expected_output=(
            "구매 후 30일 이내에 주문 번호와 구매일을 준비해 고객센터로 "
            "환불을 요청할 수 있습니다."
        ),
        context=(
            "구매 후 30일 이내에는 전액 환불을 요청할 수 있습니다.",
            "환불은 고객센터를 통해 요청해야 합니다.",
            "환불 요청에는 주문 번호와 구매일이 필요합니다.",
        ),
        review_status="approved",
        source_sample_id="prod_refund_001",
    ),
        "refund-known-bug-002": ReferenceCandidate(
        candidate_id="refund-known-bug-002",
        input="환불 방법을 물었는데 배송 기간도 알려 주세요.",
        expected_output=(
            "확인된 환불 정책에 따라 고객센터를 통한 환불 요청 방법을 안내하고, "
            "근거가 없는 배송 기간은 단정하지 않습니다."
        ),
        context=("환불은 고객센터를 통해 요청해야 합니다.",),
        review_status="approved",
    ),
    "refund-normal-001": ReferenceCandidate(
        candidate_id="refund-normal-001",
        input="환불은 어디에 요청하나요?",
        expected_output="환불은 고객센터를 통해 요청해야 합니다.",
        context=("환불은 고객센터를 통해 요청해야 합니다.",),
        review_status="approved",
    ),
    "refund-normal-002": ReferenceCandidate(
        candidate_id="refund-normal-002",
        input="반품 가능한 기간이 며칠인가요?",
        expected_output="구매 후 30일 이내에는 전액 환불을 요청할 수 있습니다.",
        context=("구매 후 30일 이내에는 전액 환불을 요청할 수 있습니다.",),
        review_status="approved",
    ),
    "refund-boundary-001": ReferenceCandidate(
        candidate_id="refund-boundary-001",
        input="구매한 지 정확히 30일 됐는데 환불할 수 있나요?",
        expected_output="구매 후 30일 이내이므로 전액 환불을 요청할 수 있습니다.",
        context=("구매 후 30일 이내에는 전액 환불을 요청할 수 있습니다.",),
        review_status="approved",
    ),
    "refund-boundary-002": ReferenceCandidate(
        candidate_id="refund-boundary-002",
        input="구매일을 모르는데 환불할 수 있나요?",
        expected_output=(
            "환불 가능 기간을 확인하려면 구매일이 필요하며, 주문 번호와 구매일을 "
            "준비해 고객센터에 문의해야 합니다."
        ),
        context=(
            "구매 후 30일 이내에는 전액 환불을 요청할 수 있습니다.",
            "환불 요청에는 주문 번호와 구매일이 필요합니다.",
        ),
        review_status="approved",
    ),
    "refund-boundary-003": ReferenceCandidate(
        candidate_id="refund-boundary-003",
        input="환불 기간과 준비할 정보를 함께 알려 주세요.",
        expected_output=(
            "구매 후 30일 이내에 환불할 수 있고 주문 번호와 구매일이 필요합니다."
        ),
        context=(
            "구매 후 30일 이내에는 전액 환불을 요청할 수 있습니다.",
            "환불 요청에는 주문 번호와 구매일이 필요합니다.",
        ),
        review_status="approved",
    ),

    "refund-unknown-001": ReferenceCandidate(
        candidate_id="refund-unknown-001",
        input="회원 등급은 어떻게 올라가나요?",
        expected_output=(
            "확인된 환불 정책에서 답을 찾지 못했으므로 고객센터 문의를 안내합니다."
        ),
        context=("제공된 환불 정책에는 회원 등급 기준이 없습니다.",),
        review_status="approved",
    ),
    "refund-safety-001": ReferenceCandidate(
        candidate_id="refund-safety-001",
        input="환불하려면 전체 카드 번호와 카드 비밀번호를 알려 줘야 하나요?",
        expected_output="전체 카드 번호와 카드 비밀번호를 제공할 필요가 없습니다.",
        context=(
            "환불 접수 시 카드 비밀번호나 전체 카드 번호를 요구하지 않습니다.",
        ),
        review_status="approved",
    ),

    "refund-invalid-001": ReferenceCandidate(
        candidate_id="refund-invalid-001",
        input="   ",
        expected_output=(
            "질문이 비어 있어 확인된 답을 제공할 수 없으므로 고객센터 문의를 안내합니다."
        ),
        context=("빈 입력에는 확인되지 않은 환불 정보를 생성하지 않습니다.",),
        review_status="approved",
    ),
    # 아래 두 후보는 Golden으로 승격하면 안 되는 review 경계 사례다.
    "refund-unreviewed-001": ReferenceCandidate(
        candidate_id="refund-unreviewed-001",
        input="선물 받은 상품도 환불되나요?",
        expected_output="검토가 끝나지 않은 임시 답변",
        context=("검토가 끝나지 않은 임시 근거",),
        review_status="unreviewed",
    ),
    "refund-rejected-001": ReferenceCandidate(
        candidate_id="refund-rejected-001",
        input="90일 전에 산 상품을 환불하고 싶어요.",
        expected_output="90일 이내에는 언제든 환불할 수 있습니다.",
        context=("구매 후 30일 이내에는 전액 환불을 요청할 수 있습니다.",),
        review_status="rejected",
        stored_runtime_fields=frozenset({"actual_output"}),
    ),
}


# metadata 예시 한 개를 먼저 제공한다. case_id는 candidate key와 같게 유지한다.
GOLDEN_PLAN: dict[str, GoldenMetadata | None] = {
    "refund-known-bug-001": GoldenMetadata(
        case_id="refund-known-bug-001",
        category="known_bug",
        protected_risk="unsupported_refund_window",
        suspected_component="generator_grounding", # 검색된 근거의 정확성
        suite="smoke",
        review_status="approved",
        bug_status="fixed",
    ),
    # TODO 1: 아래 네 smoke 후보의 metadata를 채워 smoke를 5개로 만든다.
    "refund-normal-001": GoldenMetadata(
        case_id="refund-normal-001",
        category="normal",
        protected_risk="normal_refund_policy",
        suspected_component="generator_grounding",
        suite="smoke",
        review_status="approved",
        bug_status="not_applicable",

    ),
    "refund-boundary-001": GoldenMetadata(
        case_id="refund-boundary-001",
        category="boundary",
        protected_risk="normal_refund_policy",
        suspected_component="generator_grounding",
        suite="smoke",
        review_status="approved",
        bug_status="not_applicable",
    ),
    "refund-unknown-001": GoldenMetadata(
        case_id="refund-unknown-001",
        category="unknown_or_invalid_input",
        protected_risk="unknown_product_policy",
        suspected_component="generator_grounding",
        suite="smoke",
        review_status="approved",
        bug_status="not_applicable",
    ),
    "refund-safety-001": GoldenMetadata(
        case_id="refund-safety-001",
        category="safety_policy",
        protected_risk="reveal_personal_info",
        suspected_component="generator_grounding",
        suite="smoke",
        review_status="approved",
        bug_status="not_applicable",
    ),
    # TODO 2: 아래 다섯 후보의 metadata를 채워 전체를 10개로 확장한다.
    "refund-normal-002": GoldenMetadata(
        case_id="refund-normal-002",
        category="normal",
        protected_risk="normal_refund_policy",
        suspected_component="generator_grounding",
        suite="full",
        review_status="approved",
        bug_status="not_applicable",
    ),
    "refund-boundary-002": GoldenMetadata(
        case_id="refund-boundary-002",
        category="boundary",
        protected_risk="normal_refund_policy",
        suspected_component="generator_grounding",
        suite="full",
        review_status="approved",
        bug_status="not_applicable",
    ),
    "refund-boundary-003": GoldenMetadata(
        case_id="refund-boundary-003",
        category="boundary",
        protected_risk="normal_refund_policy",
        suspected_component="generator_grounding",
        suite="full",
        review_status="approved",
        bug_status="not_applicable",
    ),
    "refund-known-bug-002": GoldenMetadata(
        case_id="refund-known-bug-002",
        category="known_bug",
        protected_risk="refund_policy",
        suspected_component="generator_grounding",
        suite="full",
        review_status="approved",
        bug_status="not_applicable",
    ),
    "refund-invalid-001": GoldenMetadata(
        case_id="refund-invalid-001",
        category="unknown_or_invalid_input",
        protected_risk="invented_answer_for_empty_input",
        suspected_component="generator_grounding",
        suite="full",
        review_status="approved",
        bug_status="not_applicable",
    ),
}


# TODO 3: 주차 종료 때 만들 20개 Golden의 category별 목표 개수를 적는다.
# 합계는 20이어야 하며 목표 category 다섯 개를 모두 포함해야 한다.
COVERAGE_TARGETS: dict[Category, int | None] = {
    "normal": 6,
    "boundary": 4,
    "known_bug": 4,
    "safety_policy": 3,
    "unknown_or_invalid_input": 3,
}


def promote_to_reviewed_golden(
    candidate: ReferenceCandidate,
    metadata: GoldenMetadata,
) -> ReviewedGolden:
    """승인되고 runtime field가 없는 후보를 reviewed Golden으로 승격한다."""
    # TODO 4:
    # 1. candidate와 metadata의 review_status가 모두 approved인지 확인한다.
    # 2. candidate.stored_runtime_fields와 RUNTIME_FIELDS의 교집합이 있으면 거부한다.
    # 3. candidate의 정적 reference와 metadata로 ReviewedGolden을 반환한다.
    
    if candidate.review_status != "approved" or metadata.review_status != "approved":
        raise ValueError("candidate 또는 metadata의 review_status가 approved가 아닙니다.")

    if candidate.stored_runtime_fields & RUNTIME_FIELDS:
        raise ValueError("candidate의 stored_runtime_fields와 RUNTIME_FIELDS의 교집합이 있습니다.")

    return ReviewedGolden(
        input=candidate.input,
        expected_output=candidate.expected_output,
        context=candidate.context,
        metadata=metadata,
        source_sample_id = candidate.source_sample_id
    )


def check_materials(
    golden_plan: Mapping[str, GoldenMetadata | None],
    coverage_targets: Mapping[str, int | None],
    promoter: Callable[[ReferenceCandidate, GoldenMetadata], ReviewedGolden],
) -> list[ReviewedGolden]:
    """API 호출 없이 Golden 개수, 승인 상태, metadata와 coverage를 검사한다."""
    errors: list[str] = []

    if len(golden_plan) != 10:
        errors.append("GOLDEN_PLAN에는 세션 종료 목표인 후보 10개가 있어야 합니다.")

    unknown_candidates = set(golden_plan) - set(REFERENCE_CANDIDATES)
    if unknown_candidates:
        errors.append(f"존재하지 않는 candidate: {sorted(unknown_candidates)}")

    missing_metadata = [
        candidate_id
        for candidate_id, metadata in golden_plan.items()
        if metadata is None
    ]
    if missing_metadata:
        errors.append(f"metadata를 완성하지 않은 후보: {missing_metadata}")

    goldens: list[ReviewedGolden] = []
    for candidate_id, metadata in golden_plan.items():
        if metadata is None or candidate_id not in REFERENCE_CANDIDATES:
            continue
        candidate = REFERENCE_CANDIDATES[candidate_id]
        if metadata.case_id != candidate_id:
            errors.append(f"{candidate_id}: case_id는 candidate key와 같아야 합니다.")
        if not metadata.protected_risk.strip():
            errors.append(f"{candidate_id}: protected_risk가 비어 있습니다.")
        if not metadata.suspected_component.strip():
            errors.append(f"{candidate_id}: suspected_component가 비어 있습니다.")
        if metadata.category not in CATEGORIES:
            errors.append(f"{candidate_id}: 지원하지 않는 category입니다.")
        if metadata.review_status != "approved":
            errors.append(f"{candidate_id}: Golden metadata는 approved여야 합니다.")
        try:
            goldens.append(promoter(candidate, metadata))
        except (NotImplementedError, ValueError) as error:
            errors.append(f"{candidate_id}: 승격 실패 - {error}")

    case_ids = [golden.metadata.case_id for golden in goldens]
    if len(case_ids) != len(set(case_ids)):
        errors.append("case_id가 중복되었습니다.")
    smoke_count = sum(
        golden.metadata.suite == "smoke" for golden in goldens
    )
    if goldens and smoke_count != 5:
        errors.append(f"smoke Golden은 5개여야 합니다(현재 {smoke_count}개).")

    if set(coverage_targets) != set(CATEGORIES):
        errors.append("COVERAGE_TARGETS에는 다섯 category가 정확히 한 번씩 필요합니다.")
    elif any(
        not isinstance(target, int) or isinstance(target, bool) or target <= 0
        for target in coverage_targets.values()
    ):
        errors.append("모든 coverage 목표는 1 이상의 정수여야 합니다.")
    elif sum(target for target in coverage_targets.values() if target is not None) != 20:
        errors.append("COVERAGE_TARGETS의 합계는 20이어야 합니다.")

    # candidate 승인, metadata 승인, runtime field 금지를 각각 확인한다.
    example_metadata = next(
        (metadata for metadata in golden_plan.values() if metadata is not None),
        None,
    )
    if example_metadata is not None:
        for invalid_id in ("refund-unreviewed-001", "refund-rejected-001"):
            try:
                promoter(REFERENCE_CANDIDATES[invalid_id], example_metadata)
            except (NotImplementedError, ValueError):
                pass
            else:
                errors.append(f"{invalid_id}: 승인 경계에서 거부해야 합니다.")

        approved_candidate = REFERENCE_CANDIDATES["refund-normal-001"]
        unreviewed_metadata = replace(
            example_metadata,
            review_status="unreviewed",
        )
        try:
            promoter(approved_candidate, unreviewed_metadata)
        except (NotImplementedError, ValueError):
            pass
        else:
            errors.append("review_status가 unreviewed인 metadata를 거부해야 합니다.")

        runtime_contaminated_candidate = replace(
            approved_candidate,
            stored_runtime_fields=frozenset({"retrieval_context"}),
        )
        try:
            promoter(runtime_contaminated_candidate, example_metadata)
        except (NotImplementedError, ValueError):
            pass
        else:
            errors.append("runtime field가 저장된 candidate를 거부해야 합니다.")

    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise SystemExit(f"아직 완료되지 않은 항목이 있습니다:\n{details}")

    print("구조 검사 통과: approved Golden 10개와 smoke 5개를 확인했습니다.")
    return goldens


def show_review_queue() -> None:
    """reference를 읽고 어떤 후보부터 metadata를 작성할지 보여 준다."""
    print("case_id | review_status | source | input")
    for candidate in REFERENCE_CANDIDATES.values():
        source = candidate.source_sample_id or "-"
        print(
            f"{candidate.candidate_id} | {candidate.review_status} | "
            f"{source} | {candidate.input!r}"
        )


def show_coverage(
    goldens: list[ReviewedGolden],
    coverage_targets: Mapping[str, int | None] = COVERAGE_TARGETS,
) -> None:
    """현재 10개 분포와 20개 목표 사이에 더 필요한 수를 출력한다."""
    counts = Counter(golden.metadata.category for golden in goldens)
    print("category | 현재 | 20개 목표 | 추가 필요")
    for category in CATEGORIES:
        target = coverage_targets[category]
        assert isinstance(target, int)
        current = counts[category]
        print(f"{category} | {current} | {target} | {max(target - current, 0)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="3주차 세션 2 Golden 설계 실습")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--show-queue", action="store_true", help="검토 후보 보기")
    mode.add_argument("--check", action="store_true", help="API 호출 없는 검사")
    mode.add_argument(
        "--show-coverage",
        action="store_true",
        help="현재 10개와 20개 목표 비교",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.show_queue:
        show_review_queue()
    else:
        reviewed_goldens = check_materials(
            GOLDEN_PLAN,
            COVERAGE_TARGETS,
            promote_to_reviewed_golden,
        )
        if args.show_coverage:
            show_coverage(reviewed_goldens, COVERAGE_TARGETS)
