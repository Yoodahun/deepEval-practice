"""2주차 세션 3: 경계 사례로 GEval rubric 검증하기 - 학생용 실습.

이 세션에서는 threshold를 보정하지 않는다. judge를 실행하기 전에 사람
판정을 먼저 적고, 같은 여섯 사례에서 baseline과 수정 rubric의 score와
reason이 어떻게 달라지는지 관찰한다.

진행 순서:

1. TODO 1에서 두 경계 사례의 ``human_expected``와 근거를 채운다.
2. TODO 2에서 baseline ``GEval`` 생성 함수를 구현한다.
3. TODO 3에서 score를 임시 threshold 기준 판정으로 바꾸는 함수를 구현한다.
4. API 호출 없이 1~3번을 검사한다.

   .venv/bin/python \
       tests/evals/week2_session3_geval_boundary_exercise.py --check

5. 사례 하나를 ``metric.measure()``로 디버깅한다.

   .venv/bin/python \
       tests/evals/week2_session3_geval_boundary_exercise.py \
       --debug-one boundary_missing_order_id

6. ``evaluate()``로 baseline 여섯 사례를 실행하고 관찰 문서에 기록한다.

   .venv/bin/python \
       tests/evals/week2_session3_geval_boundary_exercise.py --run-baseline

7. 가장 명확한 불일치 하나를 고른 뒤 TODO 4의 rubric만 한 번 수정한다.
8. 수정 구조를 검사하고 같은 여섯 사례를 다시 실행한다.

   .venv/bin/python \
       tests/evals/week2_session3_geval_boundary_exercise.py --check-revision
   .venv/bin/python \
       tests/evals/week2_session3_geval_boundary_exercise.py --run-revised

``--debug-one``, ``--run-baseline``, ``--run-revised``는 LLM judge API를
호출한다. score가 마음에 들지 않는다는 이유로 ``PROVISIONAL_THRESHOLD``를
바꾸지 않는다. threshold 보정은 더 많은 사람 라벨을 사용하는 5주차의
학습 목표다.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Callable, Final, Literal, Sequence

from deepeval import evaluate
from deepeval.evaluate import AsyncConfig, DisplayConfig
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams


HumanLabel = Literal["pass", "fail"]

QUESTION: Final = "지난주에 산 상품을 환불하려면 어떻게 해야 하나요?"
EXPECTED_OUTPUT: Final = (
    "구매 후 30일 이내에 주문 번호를 준비해 고객센터로 요청하면 "
    "전액 환불을 받을 수 있습니다."
)
PROVISIONAL_THRESHOLD: Final = 0.7

BASELINE_CRITERIA: Final = """
Evaluate whether the actual output gives the user a complete refund guide when
compared with the expected output. Lower the score when important information
needed to request a refund is missing. Do not evaluate tone, sentence length,
JSON format, or retrieval quality.
"""

# TODO 4: baseline 결과에서 가장 명확한 문제 하나를 고른 뒤 이 문자열을
# 수정한다. 품질 축은 계속 "환불 안내 완전성" 하나여야 한다. threshold,
# 사람 라벨, 사례의 답변을 rubric에 맞추려고 바꾸면 안 된다.
REVISED_CRITERIA = """
Evaluate whether the actual output gives the user a complete refund guide when
compared with the expected output. Lower the score when important information
needed to request a refund is missing.

Important information is below:
- 주문번호
- 고객센터
- 환불안내

Do not evaluate tone, sentence length,
JSON format, or retrieval quality.
"""


@dataclass(frozen=True)
class Scenario:
    """judge 실행 전에 사람이 판정한 평가 사례."""

    test_case: LLMTestCase
    human_expected: str
    human_rationale: str


@dataclass(frozen=True)
class Observation:
    """한 사례에서 얻은 사람 판정과 judge 관찰."""

    scenario_id: str
    human_expected: str
    judge_observed: HumanLabel
    score: float
    reason: str


SCENARIOS: Final = {
    "clear_pass_001": Scenario(
        test_case=LLMTestCase(
            name="clear_pass_001",
            input=QUESTION,
            actual_output=(
                "구매 후 30일 안에 주문 번호를 준비해 고객센터로 "
                "전액 환불을 요청해 주세요."
            ),
            expected_output=EXPECTED_OUTPUT,
        ),
        human_expected="pass",
        human_rationale="기간, 필요 정보, 요청 채널을 모두 안내한다.",
    ),
    "clear_pass_002": Scenario(
        test_case=LLMTestCase(
            name="clear_pass_002",
            input=QUESTION,
            actual_output=(
                "주문 번호와 함께 고객센터에 접수해 주세요. 구매일로부터 "
                "30일 이내라면 전액 환불 대상입니다."
            ),
            expected_output=EXPECTED_OUTPUT,
        ),
        human_expected="pass",
        human_rationale="표현 순서는 다르지만 세 필수 요소가 모두 있다.",
    ),
    "clear_fail_001": Scenario(
        test_case=LLMTestCase(
            name="clear_fail_001",
            input=QUESTION,
            actual_output="구매 후 30일 이내에는 환불할 수 있습니다.",
            expected_output=EXPECTED_OUTPUT,
        ),
        human_expected="fail",
        human_rationale="주문 번호와 고객센터 접수 방법이 모두 빠졌다.",
    ),
    "clear_fail_002": Scenario(
        test_case=LLMTestCase(
            name="clear_fail_002",
            input=QUESTION,
            actual_output=(
                "구매 후 90일 이내에 주문 번호를 준비해 고객센터로 "
                "환불을 요청해 주세요."
            ),
            expected_output=EXPECTED_OUTPUT,
        ),
        human_expected="fail",
        human_rationale="핵심 정책인 환불 가능 기간이 reference와 모순된다.",
    ),
    "boundary_missing_order_id": Scenario(
        test_case=LLMTestCase(
            name="boundary_missing_order_id",
            input=QUESTION,
            actual_output=(
                "구매 후 30일 안에 고객센터로 전액 환불을 요청해 주세요."
            ),
            expected_output=EXPECTED_OUTPUT,
        ),
        # TODO 1-A: judge를 실행하기 전에 pass 또는 fail을 적고 근거를 쓴다.
        human_expected="pass",
        human_rationale=(
            "주문번호는 포함되어 있지 않으나 환불 방법은 안내하므로 "
            "이어서 진행할 수 있다."
        ),
    ),
    "boundary_vague_channel": Scenario(
        test_case=LLMTestCase(
            name="boundary_vague_channel",
            input=QUESTION,
            actual_output=(
                "구매 후 30일 이내에 주문 번호를 준비해 문의 창구로 "
                "전액 환불을 요청해 주세요."
            ),
            expected_output=EXPECTED_OUTPUT,
        ),
        # TODO 1-B: "문의 창구"를 충분한 요청 방법으로 볼지 먼저 결정한다.
        human_expected="fail",
        human_rationale="문의 창구와 고객센터는 다른 채널일 수 있기 때문에 실패할 수 있다.",
    ),
}


def make_refund_completeness_metric(
    criteria: str, *, name: str = "Refund Completeness"
) -> GEval:
    """주어진 rubric으로 환불 안내 완전성 metric을 만든다."""
    # TODO 2: 다음 설정을 사용한 GEval을 반환한다.
    # - name=name
    # - criteria=criteria
    # - evaluation_params=[ACTUAL_OUTPUT, EXPECTED_OUTPUT]
    # - threshold=PROVISIONAL_THRESHOLD
    # - async_mode=False
    # model은 생략해 현재 설치 버전의 기본 judge를 관찰한다.
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
    """DeepEval과 같은 경계 규칙으로 score를 pass/fail로 바꾼다."""
    # TODO 3: score가 threshold 이상이면 pass, 그렇지 않으면 fail을 반환한다.
    return "pass" if score >= threshold else "fail"


def _check_scenarios(errors: list[str]) -> None:
    expected_ids = {
        "clear_pass_001",
        "clear_pass_002",
        "clear_fail_001",
        "clear_fail_002",
        "boundary_missing_order_id",
        "boundary_vague_channel",
    }
    if set(SCENARIOS) != expected_ids:
        errors.append("여섯 scenario ID를 추가하거나 삭제하지 마세요.")

    for scenario_id, scenario in SCENARIOS.items():
        if scenario.test_case.name != scenario_id:
            errors.append(f"{scenario_id}: test_case.name을 stable ID와 맞추세요.")
        if scenario.human_expected not in {"pass", "fail"}:
            errors.append(f"{scenario_id}: human_expected를 먼저 판정하세요.")
        rationale = scenario.human_rationale.strip()
        if not rationale or rationale == "TODO":
            errors.append(f"{scenario_id}: 사람 판정의 한 줄 근거를 작성하세요.")


def _check_metric(errors: list[str]) -> None:
    try:
        metric = make_refund_completeness_metric(BASELINE_CRITERIA)
    except NotImplementedError:
        errors.append("TODO 2: make_refund_completeness_metric()을 구현하세요.")
        return
    except Exception as error:  # pragma: no cover - 학생 오류를 자세히 보여준다.
        errors.append(
            "TODO 2: GEval 생성 중 오류가 발생했습니다: "
            f"{type(error).__name__}: {error}"
        )
        return

    expected_params = [
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.EXPECTED_OUTPUT,
    ]
    if not isinstance(metric, GEval):
        errors.append("TODO 2: GEval 인스턴스를 반환하세요.")
        return
    if metric.criteria != BASELINE_CRITERIA:
        errors.append("TODO 2: 함수로 받은 criteria를 GEval에 전달하세요.")
    if metric.evaluation_params != expected_params:
        errors.append("TODO 2: ACTUAL_OUTPUT과 EXPECTED_OUTPUT만 사용하세요.")
    if metric.threshold != PROVISIONAL_THRESHOLD:
        errors.append("TODO 2: 임시 threshold를 변경하지 마세요.")
    if metric.async_mode is not False:
        errors.append("TODO 2: 이번 실습에서는 async_mode=False를 사용하세요.")


def _check_labeler(errors: list[str]) -> None:
    try:
        observed = (
            label_from_score(0.69, 0.7),
            label_from_score(0.7, 0.7),
            label_from_score(0.71, 0.7),
        )
    except NotImplementedError:
        errors.append("TODO 3: label_from_score()를 구현하세요.")
        return

    if observed != ("fail", "pass", "pass"):
        errors.append("TODO 3: threshold와 같은 score도 pass여야 합니다.")


def check_foundations() -> None:
    """TODO 1~3을 API 호출 없이 검사한다."""
    errors: list[str] = []
    _check_scenarios(errors)
    _check_metric(errors)
    _check_labeler(errors)
    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise SystemExit(f"아직 완료되지 않은 항목이 있습니다:\n{details}")

    metric = make_refund_completeness_metric(BASELINE_CRITERIA)
    print(f"기초 구조 검사 통과: 현재 기본 judge는 {metric.evaluation_model}입니다.")
    print("사람 라벨을 바꾸지 말고 --debug-one 또는 --run-baseline을 실행하세요.")


def check_revision() -> None:
    """TODO 4가 baseline을 한 번 수정했는지 API 없이 검사한다."""
    check_foundations()
    revised = REVISED_CRITERIA.strip()
    if not revised or revised == "TODO":
        raise SystemExit("TODO 4: baseline 관찰 후 REVISED_CRITERIA를 작성하세요.")
    if revised == BASELINE_CRITERIA.strip():
        raise SystemExit("TODO 4: baseline과 다른 수정 rubric을 작성하세요.")
    if len(revised) < 100:
        raise SystemExit(
            "TODO 4: 무엇을 명확히 했는지 judge가 해석할 수 있게 더 구체적으로 쓰세요."
        )
    print("수정 rubric 구조 검사 통과: 같은 여섯 사례에서 변경 효과를 확인하세요.")


def evaluate_scenarios(
    scenarios: dict[str, Scenario],
    metric: GEval,
    labeler: Callable[[float, float], HumanLabel],
) -> list[Observation]:
    """DeepEval evaluate() 결과를 비교하기 쉬운 관찰값으로 바꾼다."""
    result = evaluate(
        test_cases=[scenario.test_case for scenario in scenarios.values()],
        metrics=[metric],
        async_config=AsyncConfig(run_async=False),
        display_config=DisplayConfig(
            show_indicator=True,
            print_results=False,
            inspect_after_run=False,
        ),
    )

    observations: list[Observation] = []
    for test_result in result.test_results:
        metric_data = (test_result.metrics_data or [None])[0]
        if metric_data is None or metric_data.score is None:
            raise RuntimeError(f"{test_result.name}: metric 결과가 없습니다.")
        threshold = metric_data.threshold
        if threshold is None:
            threshold = PROVISIONAL_THRESHOLD
        observations.append(
            Observation(
                scenario_id=test_result.name,
                human_expected=scenarios[test_result.name].human_expected,
                judge_observed=labeler(metric_data.score, threshold),
                score=metric_data.score,
                reason=metric_data.reason or "(reason 없음)",
            )
        )
    return observations


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def print_observations(observations: Sequence[Observation]) -> None:
    """관찰 문서에 옮겨 적기 쉬운 Markdown 행을 출력한다."""
    print("\n| scenario_id | human | judge | score | 일치 | reason |")
    print("| --- | --- | --- | ---: | --- | --- |")
    for item in observations:
        matched = "yes" if item.human_expected == item.judge_observed else "no"
        print(
            f"| {item.scenario_id} | {item.human_expected} | "
            f"{item.judge_observed} | {item.score:.4f} | {matched} | "
            f"{_markdown_cell(item.reason)} |"
        )


def debug_one(scenario_id: str) -> None:
    """metric.measure()로 한 사례의 score와 reason을 자세히 본다."""
    check_foundations()
    scenario = SCENARIOS[scenario_id]
    metric = make_refund_completeness_metric(BASELINE_CRITERIA)
    metric.measure(scenario.test_case)
    observed = label_from_score(metric.score, metric.threshold)
    print(f"\n[{scenario_id}]")
    print(f"사람 예상: {scenario.human_expected} / judge 관찰: {observed}")
    print(f"score: {metric.score} / 임시 threshold: {metric.threshold}")
    print(f"reason: {metric.reason}")
    print(f"사람 근거: {scenario.human_rationale}")


def run_batch(*, revised: bool) -> None:
    """baseline 또는 수정 rubric을 여섯 사례에 일괄 실행한다."""
    if revised:
        check_revision()
        criteria = REVISED_CRITERIA
        name = "Refund Completeness Revised"
        phase = "수정 rubric"
    else:
        check_foundations()
        criteria = BASELINE_CRITERIA
        name = "Refund Completeness Baseline"
        phase = "baseline"

    metric = make_refund_completeness_metric(criteria, name=name)
    observations = evaluate_scenarios(SCENARIOS, metric, label_from_score)
    print(f"\n{phase} 관찰 결과")
    print_observations(observations)
    print(
        "\n결과를 evals/calibration/week2_geval_observations.md에 기록하고, "
        "불일치를 rubric/reference/사람 라벨/judge 변동 중 하나로 분류하세요."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="2주차 세션 3 GEval 경계 사례 실습")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="TODO 1~3 구조 검사")
    mode.add_argument(
        "--check-revision", action="store_true", help="TODO 4 수정 rubric 검사"
    )
    mode.add_argument(
        "--debug-one", choices=tuple(SCENARIOS), metavar="SCENARIO_ID"
    )
    mode.add_argument(
        "--run-baseline", action="store_true", help="baseline 여섯 사례 평가"
    )
    mode.add_argument(
        "--run-revised", action="store_true", help="수정 rubric 여섯 사례 평가"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.check:
        check_foundations()
    elif args.check_revision:
        check_revision()
    elif args.debug_one:
        debug_one(args.debug_one)
    else:
        run_batch(revised=args.run_revised)
