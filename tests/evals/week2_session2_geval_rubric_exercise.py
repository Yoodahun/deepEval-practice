"""2주차 세션 2: 단일 품질 축 GEval 만들기 - 학생용 실습.

이 파일은 커리큘럼만 읽고 어디서 시작할지 막히지 않도록, 환불 안내
완전성(refund completeness) metric을 만드는 순서를 코드 안에 고정한다.

학습 목표:

1. 코드로 확정할 수 있는 응답 계약을 LLM judge에서 분리한다.
2. 서로 독립적인 요구를 섞지 않고 한 가지 품질 축의 criteria를 작성한다.
3. criteria가 실제로 읽는 최소 evaluation parameter를 선택한다.
4. 재사용 가능한 ``make_refund_completeness_metric()``을 만든다.

진행 순서:

1. TODO 1에서 빈 문자열을 막는 deterministic assertion을 작성한다.
2. TODO 2에서 "환불 안내 완전성"만 평가하는 criteria를 작성한다.
3. TODO 3에서 actual output과 expected output을 evaluation parameter로 고른다.
4. TODO 4에서 GEval 생성자를 완성한다.
5. API 호출 없이 네 TODO의 구조를 검사한다.

   .venv/bin/python \
       tests/evals/week2_session2_geval_rubric_exercise.py --check

6. 구조 검사 통과 후 명백한 pass 2개와 fail 2개를 judge로 평가한다.

   .venv/bin/python \
       tests/evals/week2_session2_geval_rubric_exercise.py --run

``--run``은 LLM judge API를 호출하므로 ``OPENAI_API_KEY``와 소량의 비용이
필요하다. 이 세션의 threshold는 학습용 임시 값이다. 네 사례에 맞춰
threshold를 조정하지 말고, 실제 보정은 5주차 calibration에서 수행한다.
이번 탐색 실습에서는 ``model``을 생략해 설치된 DeepEval의 기본 judge를
사용한다. calibration과 CI에서는 재현성을 위해 judge model을 고정한다.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Final, Literal

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams


QUESTION: Final = "지난주에 산 상품을 환불하려면 어떻게 해야 하나요?"
EXPECTED_OUTPUT: Final = (
    "구매 후 30일 이내에 주문 번호를 준비해 고객센터로 요청하면 "
    "전액 환불을 받을 수 있습니다."
)
PROVISIONAL_THRESHOLD: Final = 0.7


@dataclass(frozen=True)
class Scenario:
    """명백한 사례 하나와 사람이 미리 정한 기대 판정을 묶는다."""

    test_case: LLMTestCase
    human_expected: Literal["pass", "fail"]
    learning_point: str


SCENARIOS: Final = {
    "clear_pass_complete": Scenario(
        test_case=LLMTestCase(
            name="필수 절차를 모두 포함한 답변",
            input=QUESTION,
            actual_output=(
                "지난주 구매 건은 30일 이내이므로 주문 번호를 준비해 "
                "고객센터에 전액 환불을 요청할 수 있습니다."
            ),
            expected_output=EXPECTED_OUTPUT,
        ),
        human_expected="pass",
        learning_point="표현이 달라도 기간, 필요 정보, 요청 방법을 모두 안내한다.",
    ),
    "clear_pass_paraphrased": Scenario(
        test_case=LLMTestCase(
            name="표현 순서가 다른 완전한 답변",
            input=QUESTION,
            actual_output=(
                "고객센터에 주문 번호와 함께 환불을 접수해 주세요. "
                "구매일로부터 30일 안이라면 전액 환불 대상입니다."
            ),
            expected_output=EXPECTED_OUTPUT,
        ),
        human_expected="pass",
        learning_point="문장 순서나 동의어 차이는 허용해야 한다.",
    ),
    "clear_fail_missing_action": Scenario(
        test_case=LLMTestCase(
            name="다음 행동이 빠진 답변",
            input=QUESTION,
            actual_output="구매 후 30일 이내에는 환불할 수 있습니다.",
            expected_output=EXPECTED_OUTPUT,
        ),
        human_expected="fail",
        learning_point="기간만 있고 주문 번호와 요청 채널이 빠졌다.",
    ),
    "clear_fail_missing_window": Scenario(
        test_case=LLMTestCase(
            name="환불 기간이 빠진 답변",
            input=QUESTION,
            actual_output="주문 번호를 준비해 고객센터로 환불을 요청해 주세요.",
            expected_output=EXPECTED_OUTPUT,
        ),
        human_expected="fail",
        learning_point="요청 방법은 있지만 환불 가능 기간이 빠졌다.",
    ),
}


def assert_response_contract(actual_output: str) -> None:
    """judge를 호출하기 전에 코드로 확정할 수 있는 최소 계약을 검사한다."""
    # TODO 1: actual_output이 str이고 공백 제거 후 비어 있지 않은지
    # 일반 assert 문으로 검사한다. 의미상 완전한지는 여기서 판단하지 않는다.
    assert isinstance(actual_output, str) and actual_output.strip() != ""


# TODO 2: 아래 문자열을 환불 안내 "완전성" 한 축만 평가하는 criteria로 바꾼다.
# 포함할 핵심: 환불 가능 기간, 필요한 정보(주문 번호), 요청 방법(고객센터).
# 제외할 축: 어조, 친절함, 문장 길이, JSON 형식, retrieval 품질.
REFUND_COMPLETENESS_CRITERIA = """
Evaluate whether the actual output provides a complete refund guide based on the expected output.
A complete answer must include:
1. 환불 가능 기간,
2. 필요한 정보인 주문 번호,
3. 고객센터를 통한 요청 방법.
Reduce the score when one or more required elements are missing.
Do not evaluate tone, sentence length, JSON format, or retrieval quality.
"""


# TODO 3: criteria가 비교해야 하는 최소 field 두 개를 선택한다.
# 힌트: SingleTurnParams.ACTUAL_OUTPUT과 어떤 reference가 필요한지 생각한다.
EVALUATION_PARAMS: list[SingleTurnParams] = [
    SingleTurnParams.ACTUAL_OUTPUT,
    SingleTurnParams.EXPECTED_OUTPUT,
]


def make_refund_completeness_metric() -> GEval:
    """환불 안내 완전성만 평가하는 학습용 custom metric을 만든다."""
    # TODO 4: GEval을 반환한다.
    # 반드시 사용할 설정:
    # - name="Refund Completeness"
    # - criteria=REFUND_COMPLETENESS_CRITERIA
    # - evaluation_params=EVALUATION_PARAMS
    # - threshold=PROVISIONAL_THRESHOLD
    # - async_mode=False  # 네 사례를 순서대로 읽기 쉽게 실행
    # 이번 탐색 단계에서는 model을 생략해 DeepEval 기본 judge를 사용한다.
    return GEval(
        name="Refund Completeness",
        criteria=REFUND_COMPLETENESS_CRITERIA,
        evaluation_params=EVALUATION_PARAMS,
        threshold=PROVISIONAL_THRESHOLD,
        async_mode=False,
    )


def _check_response_contract(errors: list[str]) -> None:
    """TODO 1을 API 호출 없이 검사한다."""
    try:
        assert_response_contract("유효한 환불 안내")
    except NotImplementedError:
        errors.append("TODO 1: assert_response_contract()를 구현하세요.")
        return
    except AssertionError:
        errors.append("TODO 1: 유효한 문자열을 실패 처리하면 안 됩니다.")
        return

    try:
        assert_response_contract("   ")
    except AssertionError:
        return
    except Exception as error:  # pragma: no cover - 학생에게 오류 원인을 보여준다.
        errors.append(
            "TODO 1: 빈 문자열은 AssertionError로 실패해야 합니다. "
            f"현재 오류: {type(error).__name__}"
        )
        return

    errors.append("TODO 1: 공백뿐인 actual_output을 실패 처리하세요.")


def _check_criteria(errors: list[str]) -> None:
    """TODO 2가 한 품질 축을 설명할 만큼 구체적인지 최소한으로 검사한다."""
    criteria = REFUND_COMPLETENESS_CRITERIA.strip()
    if not criteria or criteria == "TODO":
        errors.append("TODO 2: REFUND_COMPLETENESS_CRITERIA를 작성하세요.")
        return
    if len(criteria) < 50:
        errors.append(
            "TODO 2: 기간, 주문 번호, 고객센터를 어떻게 평가할지 조금 더 "
            "구체적으로 작성하세요."
        )


def _check_evaluation_params(errors: list[str]) -> None:
    """TODO 3이 최소 reference-based field를 선택했는지 검사한다."""
    expected = {
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.EXPECTED_OUTPUT,
    }
    actual = set(EVALUATION_PARAMS)
    if actual != expected or len(EVALUATION_PARAMS) != len(expected):
        errors.append(
            "TODO 3: ACTUAL_OUTPUT과 EXPECTED_OUTPUT을 각각 한 번 선택하세요."
        )


def _check_metric(errors: list[str]) -> None:
    """TODO 4의 GEval 설정을 API 호출 없이 검사한다."""
    try:
        metric = make_refund_completeness_metric()
    except NotImplementedError:
        errors.append("TODO 4: make_refund_completeness_metric()을 구현하세요.")
        return
    except Exception as error:  # pragma: no cover - 학생의 설정 오류를 설명한다.
        errors.append(
            "TODO 4: GEval 생성 중 오류가 발생했습니다: "
            f"{type(error).__name__}: {error}"
        )
        return

    if not isinstance(metric, GEval):
        errors.append("TODO 4: GEval 인스턴스를 반환해야 합니다.")
        return

    if metric.name != "Refund Completeness":
        errors.append('TODO 4: metric name은 "Refund Completeness"로 작성하세요.')
    if metric.criteria != REFUND_COMPLETENESS_CRITERIA:
        errors.append("TODO 4: 작성한 criteria 상수를 metric에 전달하세요.")
    if metric.evaluation_params != EVALUATION_PARAMS:
        errors.append("TODO 4: 작성한 EVALUATION_PARAMS를 metric에 전달하세요.")
    # if metric.evaluation_model != JUDGE_MODEL:
    #     errors.append("TODO 4: JUDGE_MODEL을 model에 전달하세요.")
    if metric.threshold != PROVISIONAL_THRESHOLD:
        errors.append("TODO 4: 학습용 PROVISIONAL_THRESHOLD를 사용하세요.")
    if metric.async_mode is not False:
        errors.append("TODO 4: 이번 실습에서는 async_mode=False를 사용하세요.")


def check_exercise() -> None:
    """네 TODO를 검사하되 LLM judge API는 호출하지 않는다."""
    errors: list[str] = []
    _check_response_contract(errors)
    _check_criteria(errors)
    _check_evaluation_params(errors)
    _check_metric(errors)

    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise SystemExit(f"아직 완료되지 않은 항목이 있습니다:\n{details}")

    for scenario in SCENARIOS.values():
        assert_response_contract(scenario.test_case.actual_output)

    metric = make_refund_completeness_metric()
    print(f"구조 검사 통과: 현재 기본 judge는 {metric.evaluation_model}입니다.")
    print("이제 --run으로 네 사례의 score와 reason을 읽으세요.")


def run_evaluation() -> None:
    """명백한 pass/fail 네 사례에 custom metric을 순서대로 실행한다."""
    check_exercise()
    metric = make_refund_completeness_metric()

    for scenario_key, scenario in SCENARIOS.items():
        test_case = scenario.test_case
        assert_response_contract(test_case.actual_output)
        metric.measure(test_case)
        observed = "pass" if metric.score >= metric.threshold else "fail"

        print(f"\n[{scenario_key}] {test_case.name}")
        print(f"사람 예상: {scenario.human_expected} / judge 관찰: {observed}")
        print(f"score: {metric.score} / 임시 threshold: {metric.threshold}")
        print(f"reason: {metric.reason}")
        print(f"학습 포인트: {scenario.learning_point}")

    print(
        "\n네 사례에 맞춰 threshold를 조정하지 마세요. 예상과 다르면 먼저 "
        "criteria와 expected_output이 충분히 명확한지 기록하세요."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="2주차 세션 2 단일 품질 축 GEval 실습"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="API 호출 없는 TODO 검사")
    mode.add_argument("--run", action="store_true", help="LLM judge로 네 사례 평가")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.check:
        check_exercise()
    else:
        run_evaluation()
