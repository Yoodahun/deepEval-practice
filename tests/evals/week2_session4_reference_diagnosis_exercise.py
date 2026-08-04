"""2주차 세션 4: reference 전략과 실패 진단 - 학생용 실습.

이 세션은 LLM judge를 실행하지 않는다. 대신 평가 field의 역할, reference
유무에 따른 운영 전략, metric별 수정 대상과 blind spot을 연결한다. 마지막에는
중요한 production 실패를 사람 검토 후 regression Golden으로 환류한다.

진행 순서:

1. TODO 1에서 DeepEval test-case field의 역할을 분류한다.
2. TODO 2에서 개발/production/review 완료 사례의 reference 전략을 고른다.
3. TODO 3에서 낮은 metric score를 수정 대상과 blind spot에 연결한다.
4. TODO 4에서 승인된 production 실패만 reviewed Golden으로 승격한다.
5. API 호출 없이 네 TODO를 검사한다.

   .venv/bin/python \
       tests/evals/week2_session4_reference_diagnosis_exercise.py --check

6. 완성한 진단표와 production feedback loop를 확인한다.

   .venv/bin/python \
       tests/evals/week2_session4_reference_diagnosis_exercise.py \
       --show-diagnosis
   .venv/bin/python \
       tests/evals/week2_session4_reference_diagnosis_exercise.py \
       --simulate-feedback-loop

결과는 ``evals/calibration/week2_reference_diagnosis.md``에 기록한다.
Agent trace와 tool 사용 품질은 이번 필수 실습에서 진단하지 않는다.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Callable, Final, Literal, Mapping


FieldRole = Literal["request", "reviewed_reference", "runtime_observation"]
ReferenceStrategy = Literal[
    "reference_based",
    "referenceless_then_review",
    "promote_to_regression",
]
ReferenceMode = Literal["reference_based", "referenceless"]
ReviewStatus = Literal["unreviewed", "approved", "rejected"]


@dataclass(frozen=True)
class DiagnosticRoute:
    """한 metric의 책임 범위와 낮은 score의 첫 진단 경로."""

    metric_name: str
    required_fields: frozenset[str]
    reference_mode: ReferenceMode
    suspected_component: str
    blind_spot: str


@dataclass(frozen=True)
class ProductionFailure:
    """아직 reference가 없을 수 있는 production 관측값."""

    sample_id: str
    input: str
    actual_output: str
    retrieval_context: tuple[str, ...]
    suspected_metric: str
    review_status: ReviewStatus
    reviewed_expected_output: str | None = None


@dataclass(frozen=True)
class ReviewedGolden:
    """사람이 승인한 다음 regression cycle의 정적 reference."""

    source_sample_id: str
    input: str
    expected_output: str


FIELD_NAMES: Final = (
    "input",
    "actual_output",
    "expected_output",
    "context",
    "retrieval_context",
    "expected_tools",
    "tools_called",
)

# TODO 1: 각 field를 request, reviewed_reference, runtime_observation 중 하나로
# 분류한다. input은 평가 대상 요청이며 그 자체가 정답 reference는 아니다.
FIELD_ROLES: dict[str, FieldRole | str] = {
    "input": "request",
    "actual_output": "runtime_observation",
    "expected_output": "reviewed_reference",
    "context": "reviewed_reference",
    "retrieval_context": "runtime_observation",
    "expected_tools": "reviewed_reference",
    "tools_called": "runtime_observation",
}


REFERENCE_SCENARIOS: Final = {
    "development_regression": (
        "사람이 검토한 expected_output이 있는 개발 회귀 테스트"
    ),
    "unreviewed_production_sample": (
        "input, actual_output, retrieval_context만 수집된 production 표본"
    ),
    "human_reviewed_production_failure": (
        "중요 실패를 사람이 검토하고 expected_output을 승인한 표본"
    ),
}

# TODO 2: 세 상황에 적용할 전략을 고른다.
# 사용할 값: reference_based, referenceless_then_review, promote_to_regression
REFERENCE_STRATEGIES: dict[str, ReferenceStrategy | str] = {
    "development_regression": "reference_based",
    "unreviewed_production_sample": "referenceless_then_review",
    "human_reviewed_production_failure": "promote_to_regression",
}


# TODO 3: 네 metric의 진단 경로를 완성한다.
# suspected_component에 사용할 값:
# generator, generator_grounding, retriever, answer_composition
# blind_spot에는 이 metric 하나로 확정할 수 없는 문제를 한 문장으로 적는다.
DIAGNOSTIC_ROUTES: dict[str, DiagnosticRoute | None] = {
    "answer_relevancy": DiagnosticRoute(
        metric_name="Answer Relevancy",
        required_fields=frozenset({"input", "actual_output"}),
        reference_mode="referenceless",
        suspected_component="generator",
        blind_spot="answer_relevancy는 input과 actual_output의 관련성을 평가합니다.",
    ),
    "faithfulness": DiagnosticRoute(
        metric_name="Faithfulness",
        required_fields=frozenset({"input", "actual_output", "retrieval_context"}),
        reference_mode="referenceless",
        suspected_component="generator_grounding",
        blind_spot="faithfulness는 input, actual_output, retrieval_context의 일관성을 평가합니다.",
    ),
    "contextual_relevancy": DiagnosticRoute(
        metric_name="Contextual Relevancy",
        required_fields=frozenset({"input", "retrieval_context"}),
        reference_mode="referenceless",
        suspected_component="retriever",
        blind_spot="contextual_relevancy는 input과 retrieval_context의 관련성을 평가합니다.",
    ),
    "refund_completeness": DiagnosticRoute(
        metric_name="Refund Completeness GEval",
        required_fields=frozenset({"actual_output", "expected_output"}),
        reference_mode="reference_based",
        suspected_component="answer_composition",
        blind_spot="refund_completeness는 actual_output과 expected_output의 완전성을 평가합니다.",
    ),
}


PRODUCTION_FAILURE: Final = ProductionFailure(
    sample_id="prod_refund_001",
    input="지난주에 산 상품을 환불하려면 어떻게 해야 하나요?",
    actual_output="구매 후 90일 이내에는 환불할 수 있습니다.",
    retrieval_context=(
        "구매 후 30일 이내에는 주문 번호와 함께 고객센터로 요청하면 "
        "전액 환불할 수 있습니다.",
    ),
    suspected_metric="faithfulness",
    review_status="unreviewed",
)

REVIEWED_FAILURE: Final = ProductionFailure(
    sample_id=PRODUCTION_FAILURE.sample_id,
    input=PRODUCTION_FAILURE.input,
    actual_output=PRODUCTION_FAILURE.actual_output,
    retrieval_context=PRODUCTION_FAILURE.retrieval_context,
    suspected_metric=PRODUCTION_FAILURE.suspected_metric,
    review_status="approved",
    reviewed_expected_output=(
        "구매 후 30일 이내에 주문 번호를 준비해 고객센터로 요청하면 "
        "전액 환불을 받을 수 있습니다."
    ),
)


def promote_to_reviewed_golden(failure: ProductionFailure) -> ReviewedGolden:
    """승인된 production 실패를 다음 회귀 테스트의 Golden으로 바꾼다."""
    # TODO 4: review_status가 approved가 아니거나 reviewed_expected_output이
    # 비어 있으면 ValueError를 발생시킨다. 승인된 경우 actual_output이 아니라
    # 사람이 작성한 reviewed_expected_output을 expected_output으로 사용한다.
    if failure.review_status != "approved" or failure.reviewed_expected_output is None:
        raise ValueError("승인된 경우 reviewed_expected_output이 필요합니다.")
    
    return ReviewedGolden(
        source_sample_id=failure.sample_id,
        input=failure.input,
        expected_output=failure.reviewed_expected_output,
    )


EXPECTED_FIELD_ROLES: Final[dict[str, FieldRole]] = {
    "input": "request",
    "actual_output": "runtime_observation",
    "expected_output": "reviewed_reference",
    "context": "reviewed_reference",
    "retrieval_context": "runtime_observation",
    "expected_tools": "reviewed_reference",
    "tools_called": "runtime_observation",
}

EXPECTED_REFERENCE_STRATEGIES: Final[dict[str, ReferenceStrategy]] = {
    "development_regression": "reference_based",
    "unreviewed_production_sample": "referenceless_then_review",
    "human_reviewed_production_failure": "promote_to_regression",
}

EXPECTED_ROUTE_CONTRACTS: Final = {
    "answer_relevancy": {
        "metric_name": "Answer Relevancy",
        "required_fields": frozenset({"input", "actual_output"}),
        "reference_mode": "referenceless",
        "suspected_component": "generator",
    },
    "faithfulness": {
        "metric_name": "Faithfulness",
        "required_fields": frozenset(
            {"input", "actual_output", "retrieval_context"}
        ),
        "reference_mode": "referenceless",
        "suspected_component": "generator_grounding",
    },
    "contextual_relevancy": {
        "metric_name": "Contextual Relevancy",
        "required_fields": frozenset({"input", "retrieval_context"}),
        "reference_mode": "referenceless",
        "suspected_component": "retriever",
    },
    "refund_completeness": {
        "metric_name": "Refund Completeness GEval",
        "required_fields": frozenset({"actual_output", "expected_output"}),
        "reference_mode": "reference_based",
        "suspected_component": "answer_composition",
    },
}


def _check_field_roles(
    errors: list[str], field_roles: Mapping[str, FieldRole | str]
) -> None:
    if set(field_roles) != set(FIELD_NAMES):
        errors.append("TODO 1: 일곱 field key를 추가하거나 삭제하지 마세요.")
        return
    for field_name, expected_role in EXPECTED_FIELD_ROLES.items():
        if field_roles[field_name] != expected_role:
            errors.append(
                f"TODO 1: {field_name}의 역할을 다시 확인하세요. "
                f"현재 값: {field_roles[field_name]!r}"
            )


def _check_reference_strategies(
    errors: list[str], strategies: Mapping[str, ReferenceStrategy | str]
) -> None:
    if set(strategies) != set(REFERENCE_SCENARIOS):
        errors.append("TODO 2: 세 reference scenario key를 변경하지 마세요.")
        return
    for scenario_id, expected_strategy in EXPECTED_REFERENCE_STRATEGIES.items():
        if strategies[scenario_id] != expected_strategy:
            errors.append(
                f"TODO 2: {scenario_id}의 reference 전략을 다시 확인하세요."
            )


def _check_diagnostic_routes(
    errors: list[str], routes: Mapping[str, DiagnosticRoute | None]
) -> None:
    if set(routes) != set(EXPECTED_ROUTE_CONTRACTS):
        errors.append("TODO 3: 네 metric key를 추가하거나 삭제하지 마세요.")
        return

    for metric_key, expected in EXPECTED_ROUTE_CONTRACTS.items():
        route = routes[metric_key]
        if not isinstance(route, DiagnosticRoute):
            errors.append(f"TODO 3: {metric_key}의 DiagnosticRoute를 작성하세요.")
            continue
        for attribute in (
            "metric_name",
            "required_fields",
            "reference_mode",
            "suspected_component",
        ):
            if getattr(route, attribute) != expected[attribute]:
                errors.append(
                    f"TODO 3: {metric_key}.{attribute} 값을 다시 확인하세요."
                )
        blind_spot = route.blind_spot.strip()
        if not blind_spot or blind_spot == "TODO" or len(blind_spot) < 10:
            errors.append(
                f"TODO 3: {metric_key}.blind_spot을 구체적으로 작성하세요."
            )


def _check_promoter(
    errors: list[str], promoter: Callable[[ProductionFailure], ReviewedGolden]
) -> None:
    try:
        promoter(PRODUCTION_FAILURE)
    except (ValueError, NotImplementedError) as error:
        if isinstance(error, NotImplementedError):
            errors.append("TODO 4: promote_to_reviewed_golden()을 구현하세요.")
            return
    except Exception as error:  # pragma: no cover - 학생 오류를 자세히 보여준다.
        errors.append(
            "TODO 4: 미검토 표본은 ValueError로 거부해야 합니다. "
            f"현재 오류: {type(error).__name__}"
        )
        return
    else:
        errors.append("TODO 4: 미검토 production 표본을 바로 승격하면 안 됩니다.")

    approved_without_reference = ProductionFailure(
        sample_id=PRODUCTION_FAILURE.sample_id,
        input=PRODUCTION_FAILURE.input,
        actual_output=PRODUCTION_FAILURE.actual_output,
        retrieval_context=PRODUCTION_FAILURE.retrieval_context,
        suspected_metric=PRODUCTION_FAILURE.suspected_metric,
        review_status="approved",
    )
    try:
        promoter(approved_without_reference)
    except ValueError:
        pass
    except Exception as error:  # pragma: no cover - 학생 오류를 자세히 보여준다.
        errors.append(
            "TODO 4: expected_output 없는 승인 표본은 ValueError로 거부해야 "
            f"합니다. 현재 오류: {type(error).__name__}"
        )
    else:
        errors.append(
            "TODO 4: approved 상태만으로는 부족하며 reviewed_expected_output이 "
            "필요합니다."
        )

    try:
        golden = promoter(REVIEWED_FAILURE)
    except Exception as error:  # pragma: no cover - 학생 오류를 자세히 보여준다.
        errors.append(
            "TODO 4: 승인된 표본은 ReviewedGolden으로 승격해야 합니다. "
            f"현재 오류: {type(error).__name__}: {error}"
        )
        return

    if not isinstance(golden, ReviewedGolden):
        errors.append("TODO 4: ReviewedGolden 인스턴스를 반환하세요.")
        return
    if golden.source_sample_id != REVIEWED_FAILURE.sample_id:
        errors.append("TODO 4: 원본 production sample ID를 보존하세요.")
    if golden.input != REVIEWED_FAILURE.input:
        errors.append("TODO 4: 사용자의 input을 회귀 테스트 입력으로 보존하세요.")
    if golden.expected_output != REVIEWED_FAILURE.reviewed_expected_output:
        errors.append(
            "TODO 4: actual_output이 아니라 reviewed_expected_output을 사용하세요."
        )


def check_materials(
    *,
    field_roles: Mapping[str, FieldRole | str],
    strategies: Mapping[str, ReferenceStrategy | str],
    routes: Mapping[str, DiagnosticRoute | None],
    promoter: Callable[[ProductionFailure], ReviewedGolden],
) -> None:
    """주입한 답안을 API 호출 없이 검사한다."""
    errors: list[str] = []
    _check_field_roles(errors, field_roles)
    _check_reference_strategies(errors, strategies)
    _check_diagnostic_routes(errors, routes)
    _check_promoter(errors, promoter)
    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise SystemExit(f"아직 완료되지 않은 항목이 있습니다:\n{details}")

    print("구조 검사 통과: reference 전략과 네 metric의 진단 경로가 일관됩니다.")
    print("이번 세션의 명령은 LLM judge나 외부 API를 호출하지 않습니다.")


def check_exercise() -> None:
    check_materials(
        field_roles=FIELD_ROLES,
        strategies=REFERENCE_STRATEGIES,
        routes=DIAGNOSTIC_ROUTES,
        promoter=promote_to_reviewed_golden,
    )


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def print_diagnosis_table(routes: Mapping[str, DiagnosticRoute | None]) -> None:
    """작성 템플릿에 옮겨 적기 쉬운 Markdown 진단표를 출력한다."""
    print(
        "\n| metric | required fields | reference | suspected component | blind spot |"
    )
    print("| --- | --- | --- | --- | --- |")
    for metric_key, route in routes.items():
        if route is None:
            raise RuntimeError(f"{metric_key}: DiagnosticRoute가 없습니다.")
        fields = ", ".join(sorted(route.required_fields))
        print(
            f"| {_markdown_cell(route.metric_name)} | {_markdown_cell(fields)} | "
            f"{route.reference_mode} | {route.suspected_component} | "
            f"{_markdown_cell(route.blind_spot)} |"
        )


def simulate_feedback_loop(
    strategies: Mapping[str, ReferenceStrategy | str],
    routes: Mapping[str, DiagnosticRoute | None],
    promoter: Callable[[ProductionFailure], ReviewedGolden],
) -> None:
    """reference 없는 표본이 reviewed Golden이 되는 경계를 보여준다."""
    route = routes[PRODUCTION_FAILURE.suspected_metric]
    if route is None:
        raise RuntimeError("production 실패에 연결된 DiagnosticRoute가 없습니다.")
    golden = promoter(REVIEWED_FAILURE)

    print("\n1. production에서 reference 없는 실패 후보를 관찰")
    print(
        "   전략: "
        f"{strategies['unreviewed_production_sample']} / "
        f"의심 컴포넌트: {route.suspected_component}"
    )
    print("2. 원문과 근거를 사람이 검토하고 expected_output을 승인")
    print("3. 다음 regression dataset에 reviewed Golden으로 추가")
    print(f"   source_sample_id: {golden.source_sample_id}")
    print(f"   input: {golden.input}")
    print(f"   expected_output: {golden.expected_output}")
    print(
        "4. 이후 전략: "
        f"{strategies['human_reviewed_production_failure']}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="2주차 세션 4 reference/진단 실습")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="TODO 1~4 구조 검사")
    mode.add_argument(
        "--show-diagnosis", action="store_true", help="완성한 Markdown 진단표 출력"
    )
    mode.add_argument(
        "--simulate-feedback-loop",
        action="store_true",
        help="production 실패의 reviewed Golden 환류 시뮬레이션",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    check_exercise()
    if args.show_diagnosis:
        print_diagnosis_table(DIAGNOSTIC_ROUTES)
    elif args.simulate_feedback_loop:
        simulate_feedback_loop(
            REFERENCE_STRATEGIES,
            DIAGNOSTIC_ROUTES,
            promote_to_reviewed_golden,
        )
