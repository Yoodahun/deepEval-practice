# DeepEval 실습 커리큘럼

> 대상: Python, pytest, Appium 사용 경험이 있지만 LLM 평가와 DeepEval은 처음인 SDET  
> 권장 기간: 6주, 주 4회, 회당 60~90분  
> 작성 기준: 2026-07-27, DeepEval 4.x (작성 시점 PyPI 최신 버전 4.1.4)  
> 목표: 테스트 몇 개를 실행하는 수준을 넘어, 평가 목표·데이터·메트릭·임계값을 설계하고 CI에 신뢰할 수 있는 회귀 테스트를 구축한다.

---

## 0. 먼저 이해할 것

DeepEval은 Appium이나 XCUITest를 대체하는 UI 테스트 도구가 아니다. LLM 앱의 답변, RAG 검색 결과, 에이전트의 도구 호출, 다중 턴 대화처럼 **정답이 한 문자열로 고정되지 않는 동작의 품질**을 평가하는 Python 프레임워크다. `pytest`와 통합되며, 메트릭이 임계값을 넘지 못하면 테스트를 실패시킬 수 있다.

기존 테스트 경험과 대응시키면 다음과 같다.


| 익숙한 테스트 개념         | DeepEval 개념                                    | 차이점                              |
| ------------------ | ---------------------------------------------- | -------------------------------- |
| 테스트 입력/fixture     | `Golden`, `EvaluationDataset`                  | 실행 전에는 실제 LLM 출력이 없을 수 있다.       |
| 테스트 실행 결과          | `actual_output`                                | 동일 입력에도 표현과 점수가 달라질 수 있다.        |
| 예상 결과              | `expected_output`, `context`, `expected_tools` | 완전 일치 문자열뿐 아니라 의미·근거·행동을 정의한다.   |
| assertion          | metric + `threshold` + `assert_test()`         | 상당수 메트릭이 다른 LLM을 judge로 사용한다.    |
| parameterized test | dataset + `pytest.mark.parametrize`            | 대표 사례, 실패 사례, 경계 사례의 품질이 중요하다.   |
| 테스트 리포트            | 로컬 결과 / 선택적 Confident AI                       | Confident AI 계정 없이도 로컬 실행이 가능하다. |
| flaky test 관리      | 반복 측정·judge 고정·임계값 보정                          | 확률적 시스템과 확률적 judge 양쪽의 변동을 다룬다.  |




### 이 과정에서 만들 최종 산출물

- [ ] 20개 이상의 사람이 검토한 golden으로 구성된 로컬 평가 데이터셋
- [ ] 표준 메트릭 2~3개와 제품 요구사항용 custom metric 1개
- [ ] `deepeval test run`으로 실행되는 pytest 기반 회귀 테스트
- [ ] 사람이 정한 라벨과 judge 점수를 비교한 임계값 보정 기록
- [ ] 빠른 PR gate와 더 넓은 정기 평가를 분리한 CI 설계
- [ ] 실패 원인을 데이터·retriever·generator·agent 중 하나로 분류하는 리포트

---



## 1. 전체 학습 로드맵


| 주차  | 주제              | 주차 완료 산출물              |
| --- | --------------- | ---------------------- |
| 준비  | 설치, API 키, 첫 실행 | 통과/실패하는 첫 eval 2개      |
| 1주차 | LLM 평가 기본 모델    | 평가 계약서와 단일 턴 테스트       |
| 2주차 | 표준·custom 메트릭   | 메트릭 선택표와 G-Eval rubric |
| 3주차 | 데이터셋과 회귀 테스트    | 20개 이상의 golden dataset |
| 4주차 | RAG·agent·대화 평가 | 관심 시스템 하나의 심화 suite    |
| 5주차 | 신뢰도·비용·디버깅      | 임계값 보정 및 flaky 대응 기록   |
| 6주차 | CI/CD와 캡스톤      | 재현 가능한 eval pipeline   |


권장 원칙은 “문서 읽기 20%, 직접 실패시켜 보기 80%”다. 각 실습에서는 좋은 출력만 만들지 말고, 의도적으로 관련성 부족·근거 부족·형식 오류·잘못된 도구 호출을 넣어 메트릭이 실패를 잘 잡는지 확인한다.

---



## 준비 단계 — 설치부터 첫 테스트까지



### 2. 로컬 환경 준비

DeepEval은 Python 3.9 이상 4.0 미만을 요구한다. 학습 환경은 Python 3.11 또는 3.12를 권장한다. 처음에는 최신 안정판을 설치하고, 첫 성공 후 실제 설치 버전을 고정한다.

#### 2.1 가상환경 생성

- [x] 현재 Python 버전을 확인한다.

```bash
python3 --version
```

- [x] 프로젝트 루트에서 가상환경을 만들고 활성화한다.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

- [x] 패키지 도구와 DeepEval을 설치한다.

```bash
python -m pip install --upgrade pip
python -m pip install --upgrade deepeval
```

- [ ] 설치 결과를 확인하고 버전을 기록한다.

```bash
python -m pip show deepeval
deepeval --help
```

- [ ] 첫 실행이 성공한 뒤 정확한 버전을 고정한다. 팀 프로젝트에서는 전체 `pip freeze`보다 사용하는 패키지만 명시하고 lock 도구를 사용하는 방법도 고려한다.

```bash
python -m pip freeze > requirements-lock.txt
```



#### 2.2 권장 디렉터리 구조

```text
deepEval-practice/
├── app/                         # 평가 대상이 되는 예제 LLM 앱
├── evals/
│   ├── data/                    # JSON/JSONL/CSV golden
│   ├── metrics/                 # 재사용할 custom metric
│   └── calibration/             # 사람 라벨과 threshold 결정 기록
├── tests/
│   └── evals/                   # deepeval test run 대상
├── .env.example
├── .env.local                   # 실제 키, Git에 커밋하지 않음
├── .gitignore
└── requirements-lock.txt
```

- [x] `.gitignore`에 다음을 추가한다.

```gitignore
.venv/
.env
.env.*
!.env.example
.deepeval/
__pycache__/
.pytest_cache/
```



### 3. OpenAI API 키 설정

대부분의 DeepEval 메트릭은 LLM-as-a-Judge 방식이므로 judge 모델 호출용 키가 필요하다. OpenAI 키는 로컬 또는 CI secret에서만 사용하고, 소스 코드·테스트 데이터·모바일 앱 번들에 넣지 않는다.

- [x] OpenAI Platform에서 프로젝트용 API 키를 생성한다.
- [x] 결제/사용 한도와 API 사용 가능 상태를 확인한다.
- [ ] `.env.example`을 만든다. 실제 키는 쓰지 않는다.

```dotenv
OPENAI_API_KEY=
```

- [x] `.env.local`을 만들고 실제 키를 입력한다.

```bash
cp .env.example .env.local
```

```dotenv
OPENAI_API_KEY=여기에_실제_키
```

DeepEval은 import 시 기존 프로세스 환경 변수, `.env.local`, `.env` 순으로 환경 설정을 읽을 수 있다. 셸 환경 변수를 선호한다면 다음처럼 설정해도 된다.

```bash
export OPENAI_API_KEY="여기에_실제_키"
```

- [ ] 키 값을 출력하지 않고 로드 여부만 확인한다.

```bash
python -c 'import os; print("OPENAI_API_KEY loaded:", bool(os.getenv("OPENAI_API_KEY")))'
```

- [x] 공개 저장소에 키가 한 번이라도 올라갔다면 파일에서 지우는 것으로 끝내지 않고 즉시 키를 폐기·재발급한다.



### 4. 첫 DeepEval 테스트

- [ ] `tests/evals/test_setup_first_eval.py`를 만들고 아래 코드를 입력한다.

```python
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams


def test_refund_answer_is_correct():
    correctness = GEval(
        name="Correctness",
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

    test_case = LLMTestCase(
        input="구매 후 며칠 안에 환불할 수 있나요?",
        actual_output="구매 후 30일 이내에 전액 환불을 요청할 수 있습니다.",
        expected_output="모든 고객은 구매 후 30일 안에 전액 환불을 받을 수 있습니다.",
    )

    assert_test(test_case, [correctness])
```

- [x] DeepEval CLI로 실행한다. 일반 `pytest`도 동작할 수 있지만 학습과 실제 eval suite에서는 DeepEval의 추가 기능이 붙는 전용 명령을 사용한다.

```bash
deepeval test run tests/evals/test_setup_first_eval.py -v
```

- [x] `actual_output`을 “환불은 불가능합니다”로 바꾸어 테스트가 실패하는지 확인한다.
- [x] 다시 원래 값으로 되돌리고 통과하는지 확인한다.
- [x] 점수뿐 아니라 judge가 제공한 실패 이유를 읽고 합리적인지 한 문장으로 기록한다.



### 준비 단계 완료 조건

- [x] 가상환경을 새로 만들어 같은 명령으로 재현할 수 있다.
- [x] API 키가 Git 추적 대상이 아님을 `git status`로 확인했다.
- [x] 같은 테스트를 의도적으로 pass와 fail 양쪽으로 실행했다.
- [x] `LLMTestCase`, `GEval`, `threshold`, `assert_test`의 역할을 설명할 수 있다.

---



## 1주차 — LLM 평가의 테스트 모델 익히기



### 세션 1: 평가 대상과 평가 범위

- [x] DeepEval의 Introduction과 Single-Turn Test Case 문서를 읽는다.
- [x] 평가 대상을 하나 고른다. 추천: 고객지원 답변기, 문서 요약기, RAG Q&A, 도구 호출 agent 중 하나.
- [ ] 가장 먼저 전체 앱을 black-box로 평가할 end-to-end 범위를 정의한다.
- [ ] 다음 양식으로 “평가 계약서”를 작성한다.

```markdown
## 평가 계약서
- 사용자/비즈니스 목표:
- 평가할 interaction의 시작과 끝:
- 반드시 만족해야 하는 동작:
- 허용 가능한 표현 차이:
- 절대 허용할 수 없는 실패:
- 대표 사용자 입력:
- 사람 reviewer가 합격/불합격을 판단하는 기준:
```



### 세션 2: `LLMTestCase` 필드

- [x] 다음 필드의 의미와 “정적 ground truth인지, 런타임 관측값인지”를 구분한다.


| 필드                  | 의미                        | 성격              |
| ------------------- | ------------------------- | --------------- |
| `input`             | 사용자 또는 상위 컴포넌트의 입력        | 테스트 입력          |
| `actual_output`     | 평가 대상 앱이 실제 생성한 출력        | 런타임 값           |
| `expected_output`   | 이상적인 결과의 예시               | 정적 reference    |
| `context`           | 입력에 대한 이상적이고 신뢰 가능한 근거    | 정적 ground truth |
| `retrieval_context` | RAG retriever가 실제로 가져온 문서 | 런타임 값           |
| `tools_called`      | agent가 실제 호출한 도구          | 런타임 값           |
| `expected_tools`    | 기대하는 도구 호출                | 정적 reference    |


- [x] `context`와 `retrieval_context`를 바꾸어 넣으면 진단 의미가 어떻게 틀어지는지 설명한다.
- [x] `expected_output`은 단 하나의 허용 문자열이 아니라 평가 기준을 구체화하는 reference임을 예제로 확인한다.



### 세션 3: `measure()`, `evaluate()`, `assert_test()`

- [x] 한 테스트 케이스에 `metric.measure(test_case)`를 사용해 점수와 이유를 출력한다.
- [x] 여러 테스트 케이스에 `evaluate(test_cases=..., metrics=...)`를 사용한다.
- [x] 동일 케이스를 `assert_test()`와 `deepeval test run`으로 실행해 실패가 CI exit code로 연결되는 것을 확인한다.
- [x] 다음 사용 원칙을 자신의 말로 정리한다.
  - 탐색·분석·일괄 리포트: `evaluate()`
  - 개별 메트릭 디버깅: `measure()`
  - 회귀 방지와 CI gate: `assert_test()` + `deepeval test run`



### 세션 4: 결정적 assertion과 의미 기반 eval 분리

- [ ] JSON 파싱 가능 여부, 필수 key, 길이 제한처럼 코드로 정확히 검증 가능한 요구사항 3개를 작성한다.
- [ ] 관련성, 도움됨, 어조, 근거 충실성처럼 의미 평가가 필요한 요구사항 3개를 작성한다.
- [ ] 결정적 조건은 우선 일반 pytest assertion으로 검증하고, 주관적·의미적 조건에 LLM judge를 사용한다.
- [ ] “모든 것을 G-Eval 하나로 평가”하지 않는 이유를 정리한다.



### 1주차 완료 조건

- [ ] 하나의 interaction을 `LLMTestCase`로 정확히 표현할 수 있다.
- [ ] ground truth와 runtime observation을 혼동하지 않는다.
- [ ] 결정적 검사와 LLM judge 검사를 분리할 수 있다.
- [ ] 평가 계약서가 완성되었다.

---



## 2주차 — 메트릭 선택과 custom rubric



### 세션 1: 메트릭 선택법

표준 메트릭은 이름이 좋아 보인다는 이유로 고르지 않고, “이 점수가 낮으면 어느 컴포넌트를 고쳐야 하는가?”로 선택한다. 처음에는 전체 suite에 5개 이하를 권장한다.

직접 코딩하는 실습은 [`tests/evals/week2_session1_metric_selection_exercise.py`](tests/evals/week2_session1_metric_selection_exercise.py)에서 진행한다. TODO를 완성하고 `--check`로 구조를 검사한 뒤 `--run`으로 결함별 점수와 reason을 관찰한다. 막혔을 때만 [`tests/evals/week2_session1_metric_selection_solution.py`](tests/evals/week2_session1_metric_selection_solution.py)와 비교한다.

- [ ] 아래 표에서 현재 평가 대상에 필요한 2~3개만 고른다.


| 평가 질문                   | 후보 메트릭                            | 주로 진단하는 대상             |
| ----------------------- | --------------------------------- | ---------------------- |
| 답변이 질문에 관련 있는가?         | `AnswerRelevancyMetric`           | generator/final answer |
| 답변의 주장이 검색 문서에 근거하는가?   | `FaithfulnessMetric`              | RAG generator          |
| 검색 결과에 불필요한 내용이 많은가?    | `ContextualRelevancyMetric`       | retriever              |
| 필요한 근거를 빠뜨렸는가?          | `ContextualRecallMetric`          | retriever              |
| 중요한 근거가 위에 랭크되었는가?      | `ContextualPrecisionMetric`       | retriever/reranker     |
| 정해진 도구를 올바르게 호출했는가?     | `ToolCorrectnessMetric`           | agent                  |
| 전체 과업을 달성했는가?           | `TaskCompletionMetric`            | traced agent           |
| 제품 고유 기준을 만족하는가?        | `GEval`                           | 요구사항에 따라 결정            |
| 출력이 JSON schema를 만족하는가? | `JsonCorrectnessMetric` 또는 결정적 검사 | structured output      |
| 대화 전체가 목적을 달성했는가?       | conversational metrics            | multi-turn chatbot     |


- [ ] 선택한 각 메트릭에 대해 required test-case fields를 공식 문서에서 확인한다.
- [ ] 각 메트릭 점수가 낮을 때 담당자가 취할 수정 행동을 한 줄로 적는다.



### 세션 2: G-Eval rubric 작성

- [ ] 제품 고유 요구사항 하나를 `GEval`로 작성한다. 예: “답변은 해결 단계와 주의사항을 구분하고, 확인되지 않은 사실을 단정하지 않는다.”
- [ ] `criteria`에 여러 독립 요구사항을 한꺼번에 넣지 않고 가능하면 한 가지 품질 축만 평가한다.
- [ ] pass와 fail의 경계가 드러나는 평가 기준을 작성한다.
- [ ] 명백한 pass 3개, 명백한 fail 3개, 애매한 경계 사례 4개를 준비한다.
- [ ] judge의 reason을 읽고 rubric이 의도대로 해석되는지 검토한다.



### 세션 3: 기준 기반 vs 기준 없는 평가

- [ ] reference-based metric과 referenceless metric의 차이를 설명한다.
- [ ] 개발/회귀 테스트에는 사람이 검토한 reference를 우선 사용한다.
- [ ] production sampling처럼 정답 라벨이 없는 상황에는 referenceless metric만 사용해야 하는 이유를 정리한다.
- [ ] referenceless 점수를 제품의 절대 진실로 해석하지 않는다는 운영 원칙을 적는다.



### 세션 4: 실패 진단 실험

동일 입력에 대해 아래 네 가지 결함을 각각 하나씩 만든다.

- [ ] 질문과 무관하지만 사실인 답변
- [ ] 관련은 있지만 근거에 없는 답변
- [ ] 올바른 문서를 검색했지만 잡음이 너무 많은 `retrieval_context`
- [ ] 좋은 최종 답변이지만 잘못된 도구를 호출한 agent trace

- [ ] 각 결함을 어떤 메트릭이 잡고 어떤 메트릭은 놓치는지 표로 기록한다.
- [ ] 하나의 종합 점수만으로는 원인 분석이 어려운 이유를 설명한다.



### 2주차 완료 조건

- [ ] 표준 메트릭 2~3개와 custom metric 1개를 선택했다.
- [ ] 각 메트릭의 입력 필드, threshold 방향, 수정 대상이 문서화되었다.
- [ ] custom rubric이 pass/fail/경계 사례에서 기대대로 동작한다.

---



## 3주차 — 평가 데이터셋과 회귀 테스트



### 세션 1: Golden과 Test Case

- [ ] `Golden`은 재사용할 입력과 기대 정보를 담고, 실행 중 `actual_output` 등의 런타임 값이 채워져 `LLMTestCase`가 된다는 관계를 설명한다.
- [ ] 아래 범주로 최소 20개 golden을 설계한다.


| 범주        | 권장 개수 | 예시                        |
| --------- | ----- | ------------------------- |
| 대표 정상 흐름  | 6     | 가장 흔한 사용자 질문              |
| 경계·모호한 입력 | 4     | 정보 부족, 복합 질문              |
| 알려진 과거 결함 | 4     | 이미 발견했던 regression        |
| 안전·정책·PII | 3     | 민감정보 요청, 위험한 지시           |
| 형식·도구 호출  | 3     | JSON, 특정 tool/argument 요구 |


- [ ] 각 golden에 왜 필요한지와 예상 실패 위험을 metadata 또는 별도 문서에 기록한다.



### 세션 2: 로컬 dataset

- [ ] `EvaluationDataset`을 코드에서 생성한다.
- [ ] 같은 데이터를 JSON 또는 JSONL로 저장해 코드와 테스트 데이터를 분리한다.
- [ ] 로컬 파일에서 dataset을 다시 로드한다.
- [ ] single-turn golden과 conversational golden을 한 dataset에 섞지 않는 제약을 확인한다.

예시 JSONL:

```json
{"input":"환불 기간은 얼마인가요?","expected_output":"구매 후 30일 이내 전액 환불이 가능합니다.","context":["모든 고객은 구매 후 30일 이내 전액 환불을 받을 수 있다."]}
{"input":"배송지 변경은 언제까지 가능한가요?","expected_output":"출고 전에 고객센터를 통해 변경할 수 있습니다.","context":["배송지는 상품 출고 전에만 변경 가능하다."]}
```



### 세션 3: pytest parameterization

- [ ] golden을 순회하며 실제 앱 callback으로 `actual_output`을 생성한다.
- [ ] 생성한 test case를 `pytest.mark.parametrize`와 `assert_test()`에 연결한다.
- [ ] 테스트 ID를 읽기 쉽게 만들어 실패한 golden을 바로 찾게 한다.
- [ ] smoke dataset과 full regression dataset을 pytest marker로 나눈다.



### 세션 4: 데이터 품질 리뷰

- [ ] expected output과 context를 사람이 검토한다.
- [ ] 서로 모순되는 golden, 중복 케이스, 지나치게 쉬운 케이스를 제거한다.
- [ ] production 데이터 사용 시 개인정보·기밀정보를 제거한다.
- [ ] synthetic data는 초기 coverage 확대에만 사용하고, 배포 gate에 넣기 전에 사람이 검토한다.
- [ ] prompt/model 버전이 바뀌어도 동일 golden으로 재평가할 수 있게 런타임 출력은 golden에 고정하지 않는다.



### 3주차 완료 조건

- [ ] 20개 이상의 reviewed golden이 로컬 파일에 있다.
- [ ] dataset으로부터 실제 앱 출력을 생성해 회귀 테스트를 실행한다.
- [ ] smoke/full/known-bug 범주를 선택 실행할 수 있다.
- [ ] 실패 케이스가 어떤 요구사항을 보호하는지 추적할 수 있다.

---



## 4주차 — 시스템 유형별 심화 과정

세 트랙을 모두 깊게 할 필요는 없다. 공통 세션 후 자신의 관심 시스템 한 트랙을 주력으로 선택하고, 나머지는 개념과 최소 예제만 실행한다.

### 공통 세션: end-to-end와 component-level

- [ ] 전체 앱의 최종 동작을 보는 end-to-end eval을 만든다.
- [ ] 실패 원인을 분리할 가치가 있는 컴포넌트를 하나 고른다. 예: retriever, tool call, LLM generation.
- [ ] `@observe`, trace, span의 관계를 읽고 trace-level과 span-level test case의 차이를 설명한다.
- [ ] instrumentation이 필요 없는 offline eval과 tracing이 유용한 agent/component eval을 구분한다.



### 트랙 A: RAG 평가

- [ ] `input`, `expected_output`, `context`, `retrieval_context`, `actual_output`을 모두 구분해 기록한다.
- [ ] retriever에 `ContextualRecall`, `ContextualPrecision` 또는 `ContextualRelevancy`를 적용한다.
- [ ] generator에 `AnswerRelevancy`와 `Faithfulness`를 적용한다.
- [ ] 다음 네 조합을 재현한다.
  - 좋은 검색 + 좋은 생성
  - 좋은 검색 + 근거 없는 생성
  - 누락된 검색 + 그럴듯한 생성
  - 올바른 문서 포함 + 과도한 잡음

- [ ] 낮은 faithfulness는 주로 generator 문제이고, 낮은 contextual score는 주로 retriever/reranker 문제라는 진단 가설을 검증한다.



### 트랙 B: Agent 평가

- [ ] 실제 tool call과 expected tool call을 test case에 표현한다.
- [ ] `ToolCorrectnessMetric`으로 도구 선택과 인자를 평가한다.
- [ ] agent 전체 실행을 trace하고 `TaskCompletionMetric`을 적용한다.
- [ ] 최종 답변은 좋아도 불필요한 도구 호출이 있는 사례를 만든다.
- [ ] 올바른 도구를 호출했지만 최종 과업에 실패한 사례를 만든다.



### 트랙 C: 다중 턴 대화 평가

- [ ] `ConversationalTestCase`와 `Turn`으로 3턴 이상의 대화를 표현한다.
- [ ] 대화 단위 metric과 단일 답변 metric을 혼용하지 않는다.
- [ ] role adherence, knowledge retention, conversation relevancy/completeness 중 목적에 맞는 것을 선택한다.
- [ ] 이전 턴의 사용자 정보를 잊는 사례와 역할을 이탈하는 사례를 만든다.



### 선택 실습: 일반 SDET 자산에 적용

iOS 자동화에 직접 결합할 필요는 없다. 관심이 있다면 아래 중 하나만 해본다.

- [ ] XCTest/Appium 실패 로그를 요약하는 LLM의 정확성·누락을 평가한다.
- [ ] 테스트 케이스를 자연어에서 JSON으로 생성하는 LLM의 schema와 의미 정확성을 평가한다.
- [ ] 버그 리포트 초안 생성기의 재현 절차 완전성과 추측 억제를 평가한다.
- [ ] AI 기능이 있는 앱이라면 UI 테스트는 화면 흐름을, DeepEval은 백엔드 응답 품질을 각각 담당하게 분리한다.



### 4주차 완료 조건

- [ ] end-to-end 실패와 component-level 실패를 구분할 수 있다.
- [ ] RAG, agent, multi-turn 중 한 트랙에 최소 10개 사례가 있다.
- [ ] 점수가 낮을 때 수정할 컴포넌트를 합리적으로 지목할 수 있다.

---



## 5주차 — 신뢰도, 임계값, 비용, 디버깅



### 세션 1: LLM-as-a-Judge의 한계

- [ ] judge의 점수도 확률적이며 완전한 정답이 아님을 설명한다.
- [ ] 표현, prompt, judge 모델, metric 버전 변화가 점수에 영향을 줄 수 있음을 기록한다.
- [ ] judge reason이 그럴듯하다는 이유만으로 자동 수용하지 않고 원문과 rubric을 함께 검토한다.
- [ ] 고위험 release gate는 결정적 검사, 사람 라벨, LLM judge를 함께 사용한다.



### 세션 2: threshold 보정

- [ ] 최소 30개 사례를 사람이 pass/fail로 먼저 라벨링한다. 가능하면 경계 사례를 충분히 포함한다.
- [ ] 사람 라벨을 보지 않게 분리한 상태에서 metric 점수를 실행한다.
- [ ] false positive(좋은 결과를 실패 처리)와 false negative(나쁜 결과를 통과)를 계산한다.
- [ ] 비즈니스 위험에 따라 어느 오류가 더 비싼지 정한다.
- [ ] 가장 보기 좋은 숫자를 임의로 고르지 않고, 이 분석으로 threshold를 결정한다.
- [ ] threshold와 선택 근거를 `evals/calibration/`에 기록한다.



### 세션 3: 반복성과 flaky eval

- [ ] 핵심 경계 사례를 `--repeat`로 여러 번 실행해 결과 분산을 본다.

```bash
deepeval test run tests/evals -r 3
```

- [ ] judge 모델과 metric 설정을 명시적으로 고정할지 결정한다.
- [ ] 점수가 threshold 주변에서 반복적으로 뒤집히면 먼저 rubric과 사례의 모호함을 수정한다.
- [ ] flaky를 숨기기 위해 threshold를 무조건 낮추지 않는다.
- [ ] 모델/프롬프트 변경 비교에서는 같은 dataset, metric, judge 설정을 유지한다.



### 세션 4: 속도·비용·오류 처리

- [ ] 작은 smoke suite와 넓은 nightly suite를 분리한다.
- [ ] 동일 케이스 재실행에는 cache를 사용해 시간과 judge 호출 비용을 줄인다.

```bash
deepeval test run tests/evals -c
```

- [ ] 소규모로 시작한 뒤 필요할 때만 병렬 실행 수를 높인다.

```bash
deepeval test run tests/evals -n 4
```

- [ ] rate limit, quota 부족, timeout, judge의 잘못된 구조화 출력과 실제 품질 실패를 구분한다.
- [ ] `--ignore-errors`를 release gate의 기본값으로 사용하지 않는다. 인프라 오류가 품질 통과로 오인될 수 있기 때문이다.
- [ ] 테스트 실행별 케이스 수, metric 수, 호출 횟수, 대략적 비용과 소요 시간을 기록한다.



### 5주차 완료 조건

- [ ] threshold가 사람 판단 데이터로 보정되었다.
- [ ] 반복 실행 결과와 경계 사례의 안정성을 알고 있다.
- [ ] 품질 실패, 데이터 실패, judge/API 오류를 구분하는 triage 규칙이 있다.
- [ ] 실행 시간과 API 비용을 제어하는 전략이 있다.

---



## 6주차 — CI/CD와 캡스톤



### 세션 1: CI용 suite 설계

- [ ] PR마다 실행할 5~10개의 빠르고 중요한 smoke eval을 고른다.
- [ ] 전체 regression, 반복 실행, synthetic 탐색은 nightly 또는 수동 workflow로 분리한다.
- [ ] `OPENAI_API_KEY`는 CI secret에 저장하고 로그에 노출하지 않는다.
- [ ] dependency와 judge 설정을 고정한다.
- [ ] API/network 오류와 metric threshold 실패가 리포트에서 구분되게 한다.
- [ ] 같은 명령이 로컬과 CI에서 실행되게 한다.

```bash
deepeval test run tests/evals --mark "smoke" --exit-on-first-failure -- --tb=short
```



### 세션 2: 변경 전후 비교

- [ ] baseline prompt/model/config로 전체 dataset을 실행한다.
- [ ] 변경 후보를 같은 dataset과 metric 설정으로 실행한다.
- [ ] 평균 점수만 비교하지 않고 케이스별 regression과 improvement를 확인한다.
- [ ] 중요한 케이스 하나의 큰 regression이 평균에 가려지지 않도록 hard gate를 둔다.
- [ ] 변경된 출력, 점수, judge reason, 실행 설정을 함께 보관한다.



### 세션 3: 캡스톤 구현

아래 중 하나를 고른다.

- [ ] 고객지원 Q&A의 관련성·정확성·정책 준수 회귀 테스트
- [ ] 작은 문서 집합을 사용하는 RAG의 retriever/generator 분리 평가
- [ ] 2개 도구를 사용하는 agent의 tool correctness와 task completion 평가
- [ ] 다중 턴 상담 bot의 지식 유지와 역할 준수 평가
- [ ] 테스트 실패 로그 요약/분류 LLM의 정확성·완전성 평가

필수 구현 항목:

- [ ] 평가 계약서
- [ ] 20개 이상의 reviewed golden
- [ ] 결정적 assertion 최소 1개
- [ ] 표준 metric 2개
- [ ] custom `GEval` metric 1개
- [ ] 사람이 보정한 threshold
- [ ] smoke/full marker
- [ ] 재현 가능한 실행 명령
- [ ] 실패 triage 문서



### 세션 4: 최종 리뷰

- [ ] 다른 사람이 README만 보고 환경을 만들고 테스트를 실행할 수 있다.
- [ ] 각 metric이 어떤 요구사항을 보호하는지 설명할 수 있다.
- [ ] 각 실패가 어느 컴포넌트의 문제인지 추적할 수 있다.
- [ ] dataset에 대표·경계·과거 결함·안전 사례가 포함되었다.
- [ ] API 키와 민감한 production 데이터가 저장소에 없다.
- [ ] framework 업그레이드 시 release note 확인과 작은 검증 suite 실행 절차가 있다.



### 6주차 완료 조건

- [ ] PR용 smoke eval 명령이 실패 시 non-zero exit code를 반환한다.
- [ ] 캡스톤의 baseline과 변경 후보를 같은 조건에서 비교했다.
- [ ] 평가 결과를 근거로 실제 prompt, retriever, model 또는 tool flow를 한 번 개선했다.
- [ ] 개선 후 새 regression 방지용 golden을 추가했다.

---



## 최종 자기 점검



### 개념

- [ ] 일반 unit test와 LLM eval의 차이를 설명할 수 있다.
- [ ] LLM 앱과 judge가 모두 변동성을 가질 수 있음을 안다.
- [ ] `expected_output`, `context`, `retrieval_context`의 차이를 설명할 수 있다.
- [ ] reference-based와 referenceless metric을 구분할 수 있다.
- [ ] end-to-end, trace, span의 평가 범위를 구분할 수 있다.



### 구현

- [ ] `LLMTestCase`, `Golden`, `EvaluationDataset`을 사용할 수 있다.
- [ ] `measure`, `evaluate`, `assert_test` 중 상황에 맞는 것을 고를 수 있다.
- [ ] custom G-Eval rubric을 작고 명확하게 작성할 수 있다.
- [ ] pytest parameterization과 marker로 eval suite를 구조화할 수 있다.
- [ ] `deepeval test run`의 repeat, cache, parallel 옵션을 목적에 맞게 사용한다.



### 품질 엔지니어링

- [ ] metric을 추가하기 전에 사용자 위험과 평가 목표를 정의한다.
- [ ] threshold를 사람 라벨로 보정한다.
- [ ] 평균 점수뿐 아니라 케이스별 regression을 본다.
- [ ] synthetic golden을 사람 검토 없이 release gate에 넣지 않는다.
- [ ] judge 오류를 제품 품질 실패 또는 성공으로 오인하지 않는다.
- [ ] 실제 장애·사용자 피드백을 새로운 golden으로 환류한다.

---



## 자주 빠지는 함정

- [ ] **문자열 완전 일치만 사용**: 유효한 표현 변형을 실패시킨다.
- [ ] **모든 요구를 metric 하나에 넣음**: 점수는 나오지만 실패 원인을 알 수 없다.
- [ ] **threshold를 0.5로 두고 끝냄**: 제품 위험과 사람 판단을 반영하지 못한다.
- [ ] **expected output을 모델로 대량 생성 후 무검토 사용**: judge와 데이터가 같은 편향을 공유할 수 있다.
- [ ] **average score만 gate로 사용**: 중요한 단일 회귀가 평균에 가려질 수 있다.
- [ ] **RAG의 context와 retrieval context를 혼동**: retriever와 generator 진단이 뒤바뀐다.
- [ ] **judge reason을 사실로 간주**: 이유도 모델 출력이므로 검토 대상이다.
- [ ] **API 오류를 ignore하고 통과 처리**: 평가하지 못한 상태를 품질 합격으로 오인한다.
- [ ] **키를** `.env`**와 함께 커밋**: 발견 즉시 폐기·재발급해야 한다.
- [ ] **DeepEval을 일반 UI 자동화 대체재로 사용**: 결정적 UI 동작은 기존 테스트 도구가 더 적합하다.

---



## 공식 자료 읽기 순서

1. [DeepEval Introduction](https://deepeval.com/docs/introduction)
2. [5-minute Quickstart](https://deepeval.com/docs/getting-started)
3. [Single-Turn Test Case](https://deepeval.com/docs/evaluation-test-cases)
4. [Metrics Introduction](https://deepeval.com/docs/metrics-introduction)
5. [Evaluation Datasets](https://deepeval.com/docs/evaluation-datasets)
6. [End-to-End Evaluation](https://deepeval.com/docs/evaluation-end-to-end-llm-evals)
7. [LLM Tracing](https://deepeval.com/docs/evaluation-llm-tracing)
8. [Unit Testing in CI/CD](https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd)
9. [CLI Settings](https://deepeval.com/docs/command-line-interface)
10. [Flags and Configs](https://deepeval.com/docs/evaluation-flags-and-configs)
11. [Synthetic Data Introduction](https://deepeval.com/docs/synthetic-data-generation-introduction)
12. [DeepEval GitHub](https://github.com/confident-ai/deepeval) / [PyPI](https://pypi.org/project/deepeval/)
13. [OpenAI API Quickstart](https://platform.openai.com/docs/quickstart)

문서는 4.x 동안에도 빠르게 바뀔 수 있다. 예제 import 이름이나 CLI 옵션이 다르면 설치된 버전의 `deepeval --help`, PyPI 버전, 공식 문서 순으로 다시 확인한다.

---



## 학습 기록 템플릿

각 세션이 끝날 때 아래를 복사해 기록한다.

```markdown
## YYYY-MM-DD — 주제

- 완료한 체크리스트:
- 실행 명령:
- 사용한 DeepEval / judge 설정:
- 관찰한 pass 사례:
- 관찰한 fail 사례:
- 예상과 달랐던 점:
- 비용/소요 시간:
- 다음에 dataset에 추가할 golden:
- 남은 질문:
```



### 최종 완료 정의

이 문서의 체크박스를 많이 채우는 것 자체가 목표는 아니다. **새로운 LLM 기능 요구사항을 받았을 때 위험을 정의하고, 대표 데이터를 만들고, 적합한 metric을 선택·보정하고, 회귀 테스트로 운영할 수 있다면** 커리큘럼을 완료한 것이다.
