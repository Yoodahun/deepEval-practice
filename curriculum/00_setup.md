# 준비 단계 — 환경과 첫 평가

> - 상태: 완료
> - 권장 분량: 2~3회
> - 목적: 같은 환경에서 첫 pass/fail eval을 재현한다.

준비 단계는 DeepEval의 전체 기능을 배우는 구간이 아니다. 패키지, 비밀정보, judge 호출, CLI 실패 코드가 어떻게 연결되는지 한 번 끝까지 확인하는 것이 목표다. 이미 완료했으므로 이후 환경을 다시 만들거나 버전을 올릴 때 참고한다.

## 학습 목표

- 가상환경과 고정된 dependency로 평가를 재현한다.
- 평가 대상 모델과 judge API key의 역할을 구분한다.
- `LLMTestCase`, `GEval`, `threshold`, `assert_test()`의 최소 관계를 설명한다.
- 동일 test case를 의도적으로 통과와 실패 양쪽으로 실행한다.

## 1. 로컬 환경

권장 Python은 3.11 또는 3.12다. 저장소에서는 시스템 Python 대신 `.venv` 실행 파일을 명시적으로 사용한다.

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
python -m pip show deepeval
deepeval --help
```

### 왜 버전을 고정하는가

DeepEval metric의 required field, 기본 judge, CLI flag와 score 계산은 버전에 따라 달라질 수 있다. 동일 prompt의 품질을 비교할 때 평가 프레임워크가 바뀌면 앱 변경과 metric 변경의 효과를 분리하기 어렵다.

확인할 항목:

- [x] 새 가상환경에서 `deepeval` import가 성공한다.
- [x] 설치된 DeepEval 버전을 확인했다.
- [x] `requirements-lock.txt`로 환경을 다시 구성할 수 있다.

## 2. API key와 비밀정보

대부분의 의미 기반 metric은 별도의 LLM judge를 호출한다. key는 소스 코드나 test data에 직접 쓰지 않는다.

```dotenv
# .env.example
OPENAI_API_KEY=
```

로컬 값은 `.env.local` 또는 이미 설정된 shell 환경 변수에 둔다.

```bash
python -c 'import os; print("OPENAI_API_KEY loaded:", bool(os.getenv("OPENAI_API_KEY")))'
```

### 보안 원칙

- `.env.local`, 실제 API key, 토큰은 Git에 추가하지 않는다.
- key 값을 확인하기 위해 출력하지 않고 로드 여부만 확인한다.
- 공개 이력에 key가 한 번이라도 들어갔다면 삭제만 하지 않고 즉시 폐기·재발급한다.
- 실제 고객 대화나 식별정보는 dataset에 넣기 전에 익명화한다.

## 3. 첫 DeepEval test

첫 테스트는 pytest 자동 수집 규칙에 맞춰 다음 파일을 사용한다.

```text
tests/evals/test_setup_first_eval.py
```

```python
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams


def test_refund_answer_is_correct() -> None:
    metric = GEval(
        name="Correctness",
        criteria=(
            "Determine whether the actual output communicates the same refund "
            "policy as the expected output without contradiction."
        ),
        evaluation_params=[
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        threshold=0.7,
    )
    test_case = LLMTestCase(
        input="구매 후 며칠 안에 환불할 수 있나요?",
        actual_output="구매 후 30일 이내에 전액 환불을 요청할 수 있습니다.",
        expected_output="모든 고객은 구매 후 30일 안에 전액 환불을 받을 수 있습니다.",
    )
    assert_test(test_case, [metric])
```

```bash
.venv/bin/deepeval test run tests/evals/test_setup_first_eval.py -v
```

### 의도적인 pass/fail이 중요한 이유

항상 통과하는 예제만 실행하면 metric이 좋은 답을 보상하는지만 알 수 있다. `actual_output`을 “환불은 불가능합니다”로 바꿔 실패시켜야 threshold가 CI 실패로 연결되고 reason이 실제 결함을 지목하는지 확인할 수 있다.

## 완료 산출물

- [x] 첫 test가 pass와 fail 양쪽으로 실행되었다.
- [x] 실패 시 non-zero exit code를 확인했다.
- [x] score와 reason을 함께 검토했다.
- [x] API key가 Git 추적 대상이 아님을 확인했다.

## 다시 확인해야 하는 경우

- Python 또는 DeepEval 버전을 올렸을 때
- 새 개발 장비나 CI 환경을 구성할 때
- judge provider 또는 인증 방법을 바꿀 때
- 갑자기 모든 judge test가 timeout 또는 quota 오류로 실패할 때

참고: [DeepEval 5-minute Quickstart](https://deepeval.com/docs/getting-started)

다음: [1주차 — LLM 평가의 테스트 모델](week1_evaluation_foundations.md)
