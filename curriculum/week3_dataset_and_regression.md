# 3주차 — 최소 앱, Golden, dataset, 회귀 테스트

> - 상태: 예정
> - 권장 분량: 4회
> - 핵심 질문: 정적인 예제에서 벗어나 실제 앱 실행 결과를 어떻게 반복 가능한 테스트로 만들 것인가?

2주차에는 production 실패 한 건을 사람이 검토한 reference로 바꾸는 경계를
배웠다. 3주차에는 그 한 건을 여러 reviewed Golden으로 확장하고, 매 실행마다
현재 앱에서 새로운 `actual_output`과 `retrieval_context`를 만들어 같은 위험이
다시 나타나는지 검사한다.

가장 중요한 변화는 `actual_output`을 테스트 코드에 직접 써 두지 않고 앱
callback으로 생성한다는 점이다. 저장된 답변만 다시 채점하면 prompt나
retriever가 망가져도 현재 앱을 한 번도 실행하지 않으므로 회귀를 발견할 수
없다. 완전한 production RAG나 벡터 데이터베이스를 만드는 것이 목표는 아니다.
외부 API 없이 동작하는 작은 환불 고객지원 앱으로 평가 데이터의 배선을 먼저
익힌다.

## 이번 주에 배우는 전체 흐름

```text
reviewed Golden
(input, expected_output, context, metadata)
        ↓ input으로 현재 앱 실행
runtime observation
(actual_output, retrieval_context)
        ↓ reference와 runtime을 결합
LLMTestCase
        ↓ deterministic assertion + 필요한 metric
case_id가 표시된 regression 결과
```

이 흐름에서 학습할 핵심은 파일 형식 자체가 아니라 다음 세 가지다.

1. **기준과 관측값을 분리한다.** Golden은 실행 전 승인된 기준이고,
  `actual_output`은 실행할 때마다 앱에서 얻는 결과다.
2. **데이터와 테스트 로직을 분리한다.** 사례를 추가할 때 Python 테스트를
  복사하지 않고 JSONL 한 행을 추가한다.
3. **실패를 추적 가능하게 만든다.** 숫자 인덱스가 아니라 `case_id`와 위험
  metadata로 어떤 사용자 위험이 깨졌는지 찾는다.



### 핵심 용어


| 용어                  | 이 과정에서의 의미                                         | 아닌 것                   |
| ------------------- | -------------------------------------------------- | ---------------------- |
| `Golden`            | 사람이 검토한 입력, 기대 결과, 정답 근거와 metadata                 | 현재 모델이 생성한 답변 모음       |
| `EvaluationDataset` | 여러 Golden을 로드·저장·순회하는 컨테이너                         | 자동으로 좋은 데이터를 만들어 주는 도구 |
| JSONL               | Golden 하나를 한 줄에 저장하는 버전 관리용 형식                     | 평가 로직 자체               |
| `LLMTestCase`       | 정적 reference와 현재 앱의 runtime observation을 결합한 평가 단위 | Golden과 동일한 객체 역할      |
| regression test     | 이미 보호하기로 한 동작이 변경 후에도 유지되는지 같은 사례로 재실행하는 테스트       | 한 번만 실행하는 데모           |


`context`는 사람이 승인한 이상적 근거이고 `retrieval_context`는 retriever가
실행 중 실제로 반환한 문서다. DeepEval 타입이 runtime field 저장을 허용하더라도
이 저장소에서는 재현 가능한 회귀 데이터 원칙상 Golden에 runtime observation을
고정하지 않는다.

## 주차 학습 지도


| 세션                   | 난이도 | 핵심 산출물                        |
| -------------------- | --- | ----------------------------- |
| 1. 최소 고객지원 앱         | 3/5 | runtime output callback       |
| 2. Golden 설계         | 3/5 | 20개 reviewed Golden           |
| 3. 로컬 dataset        | 2/5 | JSONL과 데이터 검증                 |
| 4. pytest regression | 3/5 | smoke/full parameterized test |




## 세션 1: 평가 가능한 최소 고객지원 앱

> - 예상 시간: 60~90분
> - 선행 조건: 환불 시나리오의 평가 계약

권장 파일:

```text
app/refund_support.py
tests/evals/test_week3_session1_refund_app_contract.py
```



### 실습 진행 순서

학생용 `app/refund_support.py`에는 정책 데이터와 함수 signature가 준비되어 있고,
retriever, generator, callback에 TODO가 하나씩 남아 있다. 처음부터 자연어 처리나
RAG 프레임워크를 추가하지 말고 아래 red-green 순서로 한 함수씩 완성한다.

1. 계약 테스트를 실행해 세 함수가 아직 구현되지 않아 실패하는 것을 확인한다.
2. `retrieve_policy()`를 구현하고 retriever 테스트만 통과시킨다.
3. `generate_answer()`를 구현하고 generator 테스트만 통과시킨다.
4. `answer_refund_question()`으로 두 함수를 연결한다.
5. 전체 계약 테스트를 실행해 모름 응답과 빈 입력까지 확인한다.

```bash
.venv/bin/python -m pytest \
  tests/evals/test_week3_session1_refund_app_contract.py::test_retriever_returns_relevant_policy_documents -v

.venv/bin/python -m pytest \
  tests/evals/test_week3_session1_refund_app_contract.py::test_generator_uses_supplied_documents -v

.venv/bin/python -m pytest \
  tests/evals/test_week3_session1_refund_app_contract.py -v
```


| 함수                         | 입력        | 실행 중 만들어지는 값      | 평가에서의 역할                    |
| -------------------------- | --------- | ----------------- | --------------------------- |
| `retrieve_policy()`        | 사용자 질문    | 관련 정책 `list[str]` | `retrieval_context`         |
| `generate_answer()`        | 질문, 검색 문서 | 답변 `str`          | `actual_output`             |
| `answer_refund_question()` | 사용자 질문    | 답변과 검색 문서 tuple   | Golden을 현재 앱에 연결하는 callback |




### 왜 최소 앱이 먼저 필요한가

Golden은 실행 전 입력과 기대 결과를 담고, 앱이 실행된 뒤에야 `actual_output`과 `retrieval_context`가 생긴다. 앱 callback이 없으면 dataset을 만들어도 runtime test case로 변환하는 과정을 배울 수 없다.

처음에는 외부 LLM API 없이 재현 가능한 작은 함수로 만든다.

이 세션에서 배우는 callback은 “테스트가 Golden의 `input`을 전달하면 실제
평가 대상 코드를 실행하고 runtime observation을 돌려주는 어댑터 함수”다.
deterministic 앱을 먼저 쓰는 이유는 실제 LLM 품질이 아니라 reference와
runtime field의 연결, retriever와 generator의 경계를 비용과 변동성 없이
확인하기 위해서다.

잘못된 정적 테스트와 runtime 테스트의 차이를 먼저 확인한다.

```python
# 잘못된 예: 앱을 바꿔도 저장된 답변만 다시 평가한다.
test_case = LLMTestCase(
    input=golden.input,
    actual_output="구매 후 30일 이내에 환불할 수 있습니다.",
)

# 이번 주의 목표: 현재 앱을 매번 실행한다.
actual_output, retrieval_context = answer_refund_question(golden.input)
```

세션이 끝나면 “이 값은 누가 미리 승인했는가?”와 “이 값은 앱의 어느 함수에서
실행 중 생겼는가?”를 기준으로 각 field를 설명할 수 있어야 한다.

```python
def retrieve_policy(question: str) -> list[str]:
    ...


def generate_answer(question: str, documents: list[str]) -> str:
    ...


def answer_refund_question(question: str) -> tuple[str, list[str]]:
    ...
```



### 구현 범위

- [x] 환불 기간, 요청 방법, 필요 정보가 담긴 정책 문서 3~5개를 준비한다.
- [x] `retrieve_policy()`가 질문에 맞는 문서 목록을 반환한다.
- [x] `generate_answer()`가 답변 문자열을 반환한다.
- [x] 상위 callback이 `(actual_output, retrieval_context)`를 반환한다.
- [x] 정책에 답이 없을 때 예외 대신 명시적인 모름 응답을 반환한다.



### API 없는 계약 테스트

- [x] 반환 타입과 빈 값 여부를 검사한다.
- [x] retrieval 결과가 `list[str]`인지 검사한다.
- [x] 입력이 비어 있을 때 정의된 동작을 확인한다.
- [x] 이 세션에서는 judge를 호출하지 않는다.



### 완료 조건

- [x] 테스트가 하드코딩된 `actual_output` 대신 앱을 호출한다.
- [x] retriever와 generator를 독립적으로 호출할 수 있다.
- [x] deterministic 계약 테스트가 통과한다.



## 세션 2: Golden을 5개에서 20개로 확장

> - 예상 시간: 60~90분 + 이후 세션에서 보완
> - 선행 조건: 세션 1 완료

권장 파일:

```text
tests/evals/week3_session2_golden_design_exercise.py
tests/evals/week3_session2_golden_design_solution.py
```

처음에는 JSONL이나 `EvaluationDataset`부터 만들지 않는다. 학생용 파일에 준비된
reference 후보를 읽고, 승인 상태와 보호할 위험을 판단해 metadata를 붙이는
것부터 시작한다. 아래 순서대로 실행하면 5개 smoke, 10개 reviewed Golden,
20개 coverage 목표를 단계적으로 완성할 수 있다.

```bash
# 1. 승인·미검토·거절 후보를 읽는다.
.venv/bin/python \
  tests/evals/week3_session2_golden_design_exercise.py --show-queue

# 2. TODO 1~4를 순서대로 작성한 뒤 API 없는 검사를 실행한다.
.venv/bin/python \
  tests/evals/week3_session2_golden_design_exercise.py --check

# 3. 현재 10개에서 category별로 몇 개를 더 추가할지 확인한다.
.venv/bin/python \
  tests/evals/week3_session2_golden_design_exercise.py --show-coverage

# 4. 직접 완성한 뒤에만 참고 답안과 비교한다.
.venv/bin/python \
  tests/evals/week3_session2_golden_design_solution.py --check
```

한 번에 20개를 채우지 않는다. 먼저 중요한 5개를 리뷰하고 10개로 확장한 뒤, 주차가 끝날 때 20개를 완성한다.

### 왜 여러 Golden이 필요한가

한 사례만 통과하면 그 문장 하나에만 잘 맞는 앱이나 rubric을 만들 수 있다.
여러 Golden은 숫자를 채우기 위한 것이 아니라 표현 차이, 정책 경계, 과거 결함,
고위험 행동을 서로 다른 사례로 보호하기 위해 필요하다. 이 과정의 20개는
production 품질을 보장하는 통계적 기준이 아니라 **coverage 설계를 연습하기
위한 학습 목표**다.

- 5개: PR에서 빠르게 돌릴 핵심 사용자 위험을 고른다.
- 10개: 같은 의도의 표현 차이와 경계 질문을 추가한다.
- 20개: category 편중과 중복을 검토하며 작은 regression dataset을 완성한다.

`reviewed`는 단지 사람이 파일을 열어 봤다는 뜻이 아니다. reviewer가 현재
정책 근거인 `context`, 허용할 기대 행동인 `expected_output`, 보호할 사용자
위험과 metadata를 함께 확인하고 승인했다는 뜻이다. 2주차의
`prod_refund_001`은 `unsupported_refund_window`를 보호하는 첫 known-bug
Golden으로 재사용한다. 상태값은 2주차 계약과 맞춰 `unreviewed`, `approved`,
`rejected`를 사용하며 **Golden에는** `approved`**만 포함한다.**

### 1단계: smoke 후보 5개

- [x] 가장 흔한 환불 질문 2개
- [x] 환불 기간 경계 질문 1개
- [x] 정책에 답이 없는 질문 1개
- [x] 개인정보를 불필요하게 요구하면 안 되는 질문 1개



### 2단계: 10개로 확장

- [x] 표현만 다른 동등 질문
- [x] 정보가 부족한 질문
- [x] 두 요구가 섞인 복합 질문
- [x] 2주차의 off-topic과 unsupported claim 위험



### 3단계: 20개 coverage


| category                 | 목표  | 예시                    |
| ------------------------ | --- | --------------------- |
| normal                   | 6   | 기간, 요청 채널, 필요 정보      |
| boundary                 | 4   | 구매 날짜 누락, 복합 질문       |
| known_bug                | 4   | 90일 오안내, 배송 설명으로 이탈   |
| safety_policy            | 3   | 카드번호 요구, 본인 확인 범위     |
| unknown_or_invalid_input | 3   | 정책에 없는 질문, 빈 입력, 긴 입력 |




### metadata 규칙

```json
{
  "case_id": "refund-normal-001",
  "category": "normal",
  "protected_risk": "wrong_refund_window",
  "suspected_component": "generator",
  "suite": "smoke",
  "review_status": "approved",
  "bug_status": "fixed"
}
```

- [x] `case_id`가 중복되지 않는다.
- [x] 각 Golden이 보호하는 위험을 설명한다.
- [x] `actual_output`, `retrieval_context`, `tools_called`를 Golden에 고정하지 않는다.
- [x] synthetic 초안은 reviewer 승인 전 `approved`로 표시하지 않는다.

metadata는 장식이 아니라 실패 후 조사 경로를 보존한다.


| metadata              | 사용하는 이유                                           |
| --------------------- | ------------------------------------------------- |
| `case_id`             | pytest 리포트와 원본 Golden을 연결한다.                      |
| `category`            | 정상·경계·과거 결함 등 coverage 편중을 찾는다.                   |
| `protected_risk`      | 이 사례를 계속 유지해야 하는 사용자 위험을 설명한다.                    |
| `suspected_component` | 실패 시 첫 조사 대상을 기록한다. 확정 원인은 아니다.                   |
| `suite` 또는 tags       | smoke 등 실행 시점을 선택한다.                              |
| `review_status`       | reference 승인 상태를 나타낸다. Golden에는 `approved`만 허용한다. |
| `bug_status`          | 과거 결함이 아직 `active`인지 수정되어 `fixed`인지 구분한다.         |


`known_bug`는 과거 결함을 나타내는 category이고 `suite`는 실행 시점을 나타낸다.
아직 수정되지 않은 `bug_status=active` 사례와 이미 수정되어 재발을 막는
`bug_status=fixed` regression 사례를 구분한다. 전자는 일반 gate에서 기대 실패나
비차단 대상으로 관리할 수 있지만, 수정 완료 후에는 blocking regression으로
승격해 다시 실패하면 차단해야 한다. 아래 canonical 예시는 90일 오안내가 이미
수정된 `fixed` 사례이므로 smoke에서 반드시 통과해야 한다.

### 완료 조건

- [x] 세션 종료 시 최소 10개, 주차 종료 시 20개가 있다.
- [x] 모든 Golden에 안정적인 ID와 위험 metadata가 있다.



## 세션 3: `EvaluationDataset`과 JSONL

> - 예상 시간: 60~90분
> - 선행 조건: reviewed Golden 최소 10개

권장 파일:

```text
evals/data/refund_goldens.jsonl
tests/evals/test_week3_session3_local_dataset.py
```

예시 JSONL:

2주차의 `retrieval_context`를 이름만 바꿔 `context`로 자동 복사하지 않는다.
reviewer가 원 정책 또는 source of truth와 대조해 검색 문구가 올바른 근거임을
별도로 승인한 뒤에만 정적 `context`로 승격한다. 2주차 `ReviewedGolden`에 없던
`context`는 이 review 단계에서 새로 보강되는 field다.

```json
{"input":"지난주 구매를 환불하려면 어떻게 하나요?","expected_output":"구매 후 30일 이내 주문 번호와 함께 고객센터에 요청합니다.","context":["구매 후 30일 이내에는 주문 번호와 함께 고객센터에 요청하면 전액 환불할 수 있다."],"additional_metadata":{"case_id":"refund-known-bug-001","category":"known_bug","protected_risk":"unsupported_refund_window","suspected_component":"generator_grounding","suite":"smoke","review_status":"approved","bug_status":"fixed","source_sample_id":"prod_refund_001"}}
```

### 실습 진행 순서

세션 2에서 승인한 10개 Golden이 `refund_goldens.jsonl`에 준비되어 있다. 먼저
각 행의 네 최상위 field가 정적 reference인지 설명한 뒤, 아래 순서로 테스트를
읽고 실행한다.

```bash
# 1. JSONL의 한 행과 파일 경로 계약을 확인한다.
.venv/bin/python -m pytest \
  tests/evals/test_week3_session3_local_dataset.py::test_jsonl_has_one_golden_per_line -v

# 2. reference와 metadata 검증만 좁게 실행한다.
.venv/bin/python -m pytest \
  tests/evals/test_week3_session3_local_dataset.py \
  -k "reference or metadata or runtime or sensitive" -v

# 3. DeepEval loader와 single-turn 제약을 포함해 전체를 실행한다.
.venv/bin/python -m pytest \
  tests/evals/test_week3_session3_local_dataset.py -v
```

`iter_jsonl()`은 원본 key가 저장되어 있는지를 검사하기 위한 얇은 loader이고,
`make_dataset()`은 JSON object를 `Golden` 목록으로 명시적으로 변환한다.
`load_dataset()`은 DeepEval의 `add_goldens_from_jsonl_file()`로 같은 파일을 다시
읽는다. 두 경로에서 `case_id` 순서가 같아야 저장 형식과 in-memory dataset의
배선이 맞다.

`refund-invalid-001`의 공백 `input`은 누락 오류가 아니라 빈 입력 동작을 보호하는
의도적 Golden이다. 따라서 `input` key와 문자열 타입은 필수지만, 모든 입력에
`strip()` 후 비어 있지 않다는 조건을 일괄 적용하지 않는다.



### 왜 JSONL과 dataset이 필요한가

Python 코드 안에 사례를 복사하면 reference 수정과 코드 변경이 섞이고 review가
어렵다. JSONL은 한 행이 한 Golden이라 diff가 작고, 테스트 로직을 건드리지
않고 사례만 추가할 수 있다. `EvaluationDataset`은 이 파일을 메모리에서
일관되게 다루는 컨테이너다. 즉 JSONL은 저장 형식, dataset은 사례 모음,
`LLMTestCase`는 앱 실행 후의 평가 단위로 역할이 다르다.

데이터 검증 테스트는 앱 품질을 평가하지 않는다. 중복 ID, 누락된 reference,
runtime field 혼입, 미검토 상태와 개인정보처럼 **평가 자체를 신뢰할 수 없게
만드는 데이터 오류**를 API 없이 먼저 차단한다. 경로 검증은 로컬과 CI의 현재
작업 디렉터리가 달라도 같은 파일을 읽게 만들기 위해 필요하다.

### 구현 작업

- [x] `Golden` 목록으로 `EvaluationDataset`을 만든다.
- [x] JSONL 한 줄이 Golden 하나가 되게 저장한다.
- [x] 프로젝트 루트 기준으로 파일 경로를 안정적으로 해석한다.
- [x] 다시 로드한 개수와 `case_id`를 검사한다.
- [x] single-turn과 conversational Golden을 섞지 않는 제약을 확인한다.

필수 과정에서는 single-turn Golden만 사용한다. multi-turn dataset은 선택
심화로 미루며, 이 제약은 아직 배우지 않은 대화 평가를 섞지 않기 위한 범위
통제다.

### API 없는 데이터 검증

- [x] 중복 `case_id`가 없다.
- [x] `input`, reference, 위험 metadata가 비어 있지 않다.
- [x] runtime field가 저장되어 있지 않다.
- [x] 실제 개인정보나 key 형태의 값이 없다.



### 완료 조건

- [x] 코드 변경 없이 JSONL 행을 추가할 수 있다.
- [x] 로컬 파일에서 동일 dataset을 재구성할 수 있다.
- [x] 데이터 검증 테스트가 judge 없이 통과한다.



## 세션 4: pytest parameterization과 데이터 리뷰

> - 예상 시간: 60~90분
> - 선행 조건: 앱 callback과 JSONL dataset

권장 파일:

```text
tests/evals/test_week3_session4_dataset_regression.py
```



### Golden에서 runtime test case로

Parameterization은 테스트 함수를 20개 복사하는 기능이 아니다. 하나의 평가
절차를 모든 Golden에 동일하게 적용하고, 실패한 사례를 안정적인 ID로 찾는
방법이다.

1. Golden의 `input`으로 `answer_refund_question()`을 호출한다.
2. 답변은 `actual_output`, 검색 결과는 `retrieval_context`에 넣는다.
3. Golden의 `expected_output`, `context`를 reference로 전달한다.
4. pytest ID는 `case_id`를 사용한다.

```python
actual_output, retrieval_context = answer_refund_question(golden.input)
test_case = LLMTestCase(
    input=golden.input,
    actual_output=actual_output,
    expected_output=golden.expected_output,
    context=golden.context,
    retrieval_context=retrieval_context,
)
```

먼저 schema, 빈 값, 금지 정보처럼 싸고 확정적인 deterministic 검사를 전체
데이터에 실행한다. 의미 기반 judge는 비용과 변동성이 있으므로 작은 smoke에서
연결 상태를 확인하고, 본격적인 RAG 의미 진단은 4주차에서 수행한다.

- [ ] `pytest.mark.parametrize`로 Golden을 순회한다.
- [ ] `case_id`가 실패 리포트에 표시된다.
- [ ] 모든 데이터에는 deterministic 검증을 먼저 실행한다.
- [ ] smoke 5개에만 judge metric을 우선 연결한다.
- [ ] `smoke`, `full`, `known_bug` 선택 규칙을 정의한다.

- `smoke`: 핵심 위험 5개 정도를 빠르게 확인하는 부분집합
- `full`: reviewed Golden 전체
- `known_bug`: category이며 `bug_status`와 gate 규칙으로 active/fixed를 구분

metadata 문자열이 자동으로 pytest marker가 되지는 않는다. loader에서 subset을
선택하거나 `pytest.param(..., marks=pytest.mark.smoke)`로 변환하는 방식 중 하나를
정하고, 예상 수집 개수를 문서화한다.

수집 검증:

```bash
.venv/bin/python -m pytest tests/evals/test_week3_session4_dataset_regression.py --collect-only -q
```



### 최종 데이터 리뷰

- [ ] 모순되는 reference를 제거했다.
- [ ] 보호 위험이 같은 중복 사례를 정리했다.
- [ ] 지나치게 쉬운 사례만 모여 있지 않다.
- [ ] production data를 사용했다면 익명화했다.
- [ ] runtime output이 Golden에 남아 있지 않다.



## 3주차 완료 조건

- [ ] 20개 이상의 reviewed Golden이 JSONL에 있다.
- [ ] 앱 callback에서 runtime output을 생성한다.
- [ ] smoke/full/known-bug를 선택 실행할 수 있다.
- [ ] 실패한 ID에서 보호 위험과 의심 컴포넌트를 찾을 수 있다.
- [ ] Golden reference와 앱 runtime observation을 예시 field로 설명할 수 있다.
- [ ] JSONL 한 행을 추가했을 때 테스트 로직 변경 없이 수집 사례가 늘어난다.
- [ ] 데이터 오류와 앱 runtime 실패를 서로 다른 실패로 분류할 수 있다.



## 막히기 쉬운 지점

- production 수준의 RAG 앱을 먼저 만들려다 dataset 학습이 지연된다.
- Golden에 현재 모델의 `actual_output`을 저장해 변경 비교가 불가능해진다.
- 20개를 숫자로만 채워 중복되고 쉬운 사례가 많아진다.
- parameterized test ID가 숫자여서 실패한 Golden을 찾기 어렵다.

참고: [Evaluation Datasets](https://deepeval.com/docs/evaluation-datasets), [Unit Testing in CI/CD](https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd)

이전: [2주차 — metric과 GEval](week2_metrics_and_geval.md) · 다음: [4주차 — RAG 평가](week4_rag_evaluation.md)