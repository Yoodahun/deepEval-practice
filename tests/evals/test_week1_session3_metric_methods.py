"""1주차 세션 3: measure(), evaluate(), assert_test() 비교 실습.

실행 방법:

    python tests/evals/test_week1_session3_metric_methods.py measure
    python tests/evals/test_week1_session3_metric_methods.py evaluate
    deepeval test run tests/evals/test_week1_session3_metric_methods.py -v
    DEEPEVAL_SESSION3_FAIL=1 deepeval test run tests/evals/test_week1_session3_metric_methods.py -v

각 명령은 LLM judge API를 호출하므로 소량의 비용이 발생할 수 있다.
"""

import argparse
import os

from deepeval import assert_test, evaluate
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams


EXPECTED_OUTPUT = "모든 고객은 구매 후 30일 안에 전액 환불을 받을 수 있습니다."
PASSING_OUTPUT = "구매일로부터 30일 이내라면 전액 환불을 요청할 수 있습니다."
FAILING_OUTPUT = "환불은 어떤 경우에도 불가능합니다."


def make_correctness_metric() -> GEval:
    """실습마다 상태가 섞이지 않도록 새 metric 인스턴스를 만든다."""
    return GEval(
        name="Refund policy correctness",
        criteria=(
            "Determine whether the actual output communicates the same refund "
            "policy as the expected output without adding contradictory information."
        ),
        evaluation_params=[
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        threshold=0.7,
    )


def make_test_case(name: str, actual_output: str) -> LLMTestCase:
    return LLMTestCase(
        name=name,
        input="구매 후 며칠 안에 환불할 수 있나요?",
        actual_output=actual_output,
        expected_output=EXPECTED_OUTPUT,
    )


def run_measure_demo() -> None:
    """한 metric과 한 case를 직접 실행해 내부 판단을 관찰한다."""
    metric = make_correctness_metric()
    # test_case = make_test_case("contradictory-answer", FAILING_OUTPUT)
    test_case = make_test_case("contradictory-answer", PASSING_OUTPUT)

    returned_score = metric.measure(test_case)

    print(f"measure() 반환값: {returned_score}")
    print(f"metric.score: {metric.score}")
    print(f"metric.reason: {metric.reason}")
    print(f"metric.threshold: {metric.threshold}")
    print(f"metric.is_successful(): {metric.is_successful()}")


def run_evaluate_demo() -> None:
    """여러 case를 한 번에 평가하고 구조화된 결과를 순회한다."""
    test_cases = [
        make_test_case("valid-paraphrase", PASSING_OUTPUT),
        make_test_case("contradictory-answer", FAILING_OUTPUT),
    ]

    result = evaluate(
        test_cases=test_cases,
        metrics=[make_correctness_metric()],
    )

    print("\n구조화된 EvaluationResult:")
    for test_result in result.test_results:
        print(f"- case={test_result.name!r}, success={test_result.success}")
        for metric_data in test_result.metrics_data or []:
            print(
                "  "
                f"metric={metric_data.name!r}, "
                f"score={metric_data.score}, "
                f"threshold={metric_data.threshold}, "
                f"success={metric_data.success}"
            )
            print(f"  reason={metric_data.reason}")


def test_refund_policy_is_correct() -> None:
    """CI gate 예제: threshold 미달이면 pytest/CLI 테스트가 실패한다."""
    should_fail = os.getenv("DEEPEVAL_SESSION3_FAIL") == "1"
    actual_output = FAILING_OUTPUT if should_fail else PASSING_OUTPUT
    test_case = make_test_case("refund-policy-ci-gate", actual_output)

    assert_test(test_case, [make_correctness_metric()])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DeepEval 세션 3의 measure/evaluate 실습"
    )
    parser.add_argument("demo", choices=("measure", "evaluate"))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.demo == "measure":
        run_measure_demo()
    else:
        run_evaluate_demo()
