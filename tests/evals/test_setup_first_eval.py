"""준비 단계: 처음 실행하는 단일 DeepEval 테스트."""

from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams


def test_refund_answer_is_correct():
    # GEval은 데이터를 어떤 기준으로 평가할지를 정의한다.
    # name : 평가 지표의 이름.
    # criteria : 무엇을 기준으로 채점할 지 자연어로 설명한다. 
    #           현재는 실제 답변과 기대답변이 같은 환불 정책을 전달하고 모순된 정보를 추가하지 않았는지를 평가 한다.
    # evaluation_params : 평가모델에게 어떤 데이터를 보여줄지 정한다. 현재는 실제 답변과 기대답변을 비교한다.
    # actual_output + expected_output
    #          ↓
    # criteria를 기준으로 비교
    #           ↓
    # 0~1 점수 산출
    #           ↓
    # 0.7 이상이면 테스트 통과
    # openai 모델이 GEval 평가자로 동작한다.
    correctness = GEval(
        name="Correctness",
        criteria=("Determine whether the actual output communicates the same refund policy as the expected output without adding contradictory information"),
        evaluation_params=[
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        threshold=0.7,

    )

    # LLMTestCase는 평가할 데이터를 보관한다.
    # input : 평가모델에게 보여줄 질문.
    # actual_output : 평가모델이 답변한 결과.
    # expected_output : 기대하는 답변.
    # 실제 모델을 평가하려면, 앱에서 생성된 답변을 actual_output에 넣어야한다.
    testcase = LLMTestCase(
        input="구매 후 며칠 안에 환불할 수 있나요?",
        actual_output="환불은 불가능합니다",
        expected_output="모든 고객은 구매 후 30일 안에 전액 환불을 받을 수 있습니다.",
    )

    # testcase에 평가지표를 넣고 테스트를 실행한다.
    # actual_output과 expected_output을 GEval로 비교한다.
    assert_test(testcase, [correctness])
