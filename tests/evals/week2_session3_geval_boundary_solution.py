"""2주차 세션 3 GEval 경계 사례 실습의 참고 답안.

학생용 파일에서 baseline 관찰을 마치고 TODO 4까지 직접 작성한 뒤 비교한다.
이 답안의 사람 판정과 rubric 수정은 유일한 정답이 아니라, 일관된 평가
계약을 작성한 한 가지 예시다.

    .venv/bin/python \
        tests/evals/week2_session3_geval_boundary_solution.py --check
    .venv/bin/python \
        tests/evals/week2_session3_geval_boundary_solution.py --run-baseline
    .venv/bin/python \
        tests/evals/week2_session3_geval_boundary_solution.py --run-revised

두 ``--run`` 명령은 LLM judge API를 호출한다.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from typing import Final

from deepeval.metrics import GEval
from deepeval.test_case import SingleTurnParams

from week2_session3_geval_boundary_exercise import (
    BASELINE_CRITERIA,
    PROVISIONAL_THRESHOLD,
    SCENARIOS as EXERCISE_SCENARIOS,
    HumanLabel,
    Scenario,
    evaluate_scenarios,
    print_observations,
)


SCENARIOS: Final = {
    **EXERCISE_SCENARIOS,
    "boundary_missing_order_id": replace(
        EXERCISE_SCENARIOS["boundary_missing_order_id"],
        human_expected="fail",
        human_rationale=(
            "주문을 특정할 필수 정보가 없어 사용자가 바로 환불을 접수할 수 없다."
        ),
    ),
    "boundary_vague_channel": replace(
        EXERCISE_SCENARIOS["boundary_vague_channel"],
        human_expected="fail",
        human_rationale=(
            "'문의 창구'가 고객센터를 뜻하는지 불명확해 요청 채널이 충분하지 않다."
        ),
    ),
}

REVISED_CRITERIA: Final = """
Evaluate only refund-guide completeness by comparing the actual output with the
expected output. Check these three independently required elements: (1) the
refund window, (2) the order number the user must prepare, and (3) an explicit
instruction to submit the request through customer support. An answer that
omits or contradicts any one of these required elements is incomplete and must
receive at most 0.6. Treat a vague phrase such as "an inquiry channel" as
missing unless it clearly identifies customer support. Do not evaluate tone,
sentence length, JSON format, or retrieval quality.
"""


def make_refund_completeness_metric(
    criteria: str, *, name: str = "Refund Completeness"
) -> GEval:
    """주어진 rubric으로 환불 안내 완전성 metric을 만든다."""
    return GEval(
        name=name,
        criteria=criteria,
        evaluation_params=[
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        threshold=PROVISIONAL_THRESHOLD,
        async_mode=False,
    )


def label_from_score(score: float, threshold: float) -> HumanLabel:
    """DeepEval의 ``score >= threshold`` 판정 규칙을 그대로 사용한다."""
    return "pass" if score >= threshold else "fail"


def check_solution() -> None:
    assert len(SCENARIOS) == 6
    assert all(
        scenario.human_expected in {"pass", "fail"}
        for scenario in SCENARIOS.values()
    )
    assert all(
        scenario.human_rationale.strip() for scenario in SCENARIOS.values()
    )
    assert REVISED_CRITERIA.strip() != BASELINE_CRITERIA.strip()

    metric = make_refund_completeness_metric(BASELINE_CRITERIA)
    assert metric.evaluation_params == [
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.EXPECTED_OUTPUT,
    ]
    assert metric.threshold == PROVISIONAL_THRESHOLD
    assert metric.async_mode is False
    assert label_from_score(0.69, 0.7) == "fail"
    assert label_from_score(0.7, 0.7) == "pass"
    print(f"참고 답안 구조 검사 통과: 현재 기본 judge는 {metric.evaluation_model}입니다.")


def run_batch(*, revised: bool) -> None:
    check_solution()
    criteria = REVISED_CRITERIA if revised else BASELINE_CRITERIA
    phase = "수정 rubric" if revised else "baseline"
    metric = make_refund_completeness_metric(
        criteria,
        name=f"Refund Completeness {phase}",
    )
    observations = evaluate_scenarios(SCENARIOS, metric, label_from_score)
    print(f"\n{phase} 참고 관찰 결과")
    print_observations(observations)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="2주차 세션 3 참고 답안")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="API 호출 없는 검사")
    mode.add_argument("--run-baseline", action="store_true")
    mode.add_argument("--run-revised", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.check:
        check_solution()
    else:
        run_batch(revised=args.run_revised)
