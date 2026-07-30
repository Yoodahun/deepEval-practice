# 3주차 — 최소 앱, Golden, dataset, 회귀 테스트

> - 상태: 예정
> - 권장 분량: 4회
> - 핵심 질문: 정적인 예제에서 벗어나 실제 앱 실행 결과를 어떻게 반복 가능한 테스트로 만들 것인가?

3주차의 가장 중요한 변화는 `actual_output`을 코드에 직접 써 두지 않고 앱 callback으로 생성한다는 점이다. 완전한 production RAG나 벡터 데이터베이스를 만들 필요는 없다. 작은 환불 고객지원 앱으로 데이터 흐름을 먼저 익힌다.

## 주차 학습 지도

| 세션 | 난이도 | 핵심 산출물 |
| --- | ---: | --- |
| 1. 최소 고객지원 앱 | 3/5 | runtime output callback |
| 2. Golden 설계 | 3/5 | 20개 reviewed Golden |
| 3. 로컬 dataset | 2/5 | JSONL과 데이터 검증 |
| 4. pytest regression | 3/5 | smoke/full parameterized test |

## 세션 1: 평가 가능한 최소 고객지원 앱

> - 예상 시간: 60~90분
> - 선행 조건: 환불 시나리오의 평가 계약

권장 파일:

```text
app/refund_support.py
tests/evals/test_week3_session1_refund_app_contract.py
```

### 왜 최소 앱이 먼저 필요한가

Golden은 실행 전 입력과 기대 결과를 담고, 앱이 실행된 뒤에야 `actual_output`과 `retrieval_context`가 생긴다. 앱 callback이 없으면 dataset을 만들어도 runtime test case로 변환하는 과정을 배울 수 없다.

처음에는 외부 LLM API 없이 재현 가능한 작은 함수로 만든다.

```python
def retrieve_policy(question: str) -> list[str]:
    ...


def generate_answer(question: str, documents: list[str]) -> str:
    ...


def answer_refund_question(question: str) -> tuple[str, list[str]]:
    ...
```

### 구현 범위

- [ ] 환불 기간, 요청 방법, 필요 정보가 담긴 정책 문서 3~5개를 준비한다.
- [ ] `retrieve_policy()`가 질문에 맞는 문서 목록을 반환한다.
- [ ] `generate_answer()`가 답변 문자열을 반환한다.
- [ ] 상위 callback이 `(actual_output, retrieval_context)`를 반환한다.
- [ ] 정책에 답이 없을 때 예외 대신 명시적인 모름 응답을 반환한다.

### API 없는 계약 테스트

- [ ] 반환 타입과 빈 값 여부를 검사한다.
- [ ] retrieval 결과가 `list[str]`인지 검사한다.
- [ ] 입력이 비어 있을 때 정의된 동작을 확인한다.
- [ ] 이 세션에서는 judge를 호출하지 않는다.

### 완료 조건

- [ ] 테스트가 하드코딩된 `actual_output` 대신 앱을 호출한다.
- [ ] retriever와 generator를 독립적으로 호출할 수 있다.
- [ ] deterministic 계약 테스트가 통과한다.

## 세션 2: Golden을 5개에서 20개로 확장

> - 예상 시간: 60~90분 + 이후 세션에서 보완
> - 선행 조건: 세션 1 완료

한 번에 20개를 채우지 않는다. 먼저 중요한 5개를 리뷰하고 10개로 확장한 뒤, 주차가 끝날 때 20개를 완성한다.

### 1단계: smoke 후보 5개

- [ ] 가장 흔한 환불 질문 2개
- [ ] 환불 기간 경계 질문 1개
- [ ] 정책에 답이 없는 질문 1개
- [ ] 개인정보를 불필요하게 요구하면 안 되는 질문 1개

### 2단계: 10개로 확장

- [ ] 표현만 다른 동등 질문
- [ ] 정보가 부족한 질문
- [ ] 두 요구가 섞인 복합 질문
- [ ] 2주차의 off-topic과 unsupported claim 위험

### 3단계: 20개 coverage

| category | 목표 | 예시 |
| --- | ---: | --- |
| normal | 6 | 기간, 요청 채널, 필요 정보 |
| boundary | 4 | 구매 날짜 누락, 복합 질문 |
| known_bug | 4 | 90일 오안내, 배송 설명으로 이탈 |
| safety_policy | 3 | 카드번호 요구, 본인 확인 범위 |
| unknown_format | 3 | 정책에 없는 질문, 빈 입력, 긴 입력 |

### metadata 규칙

```json
{
  "case_id": "refund-normal-001",
  "category": "normal",
  "protected_risk": "wrong_refund_window",
  "suspected_component": "generator",
  "suite": "smoke",
  "review_status": "reviewed"
}
```

- [ ] `case_id`가 중복되지 않는다.
- [ ] 각 Golden이 보호하는 위험을 설명한다.
- [ ] `actual_output`, `retrieval_context`, `tools_called`를 Golden에 고정하지 않는다.
- [ ] synthetic 초안은 reviewer 확인 전 `reviewed`로 표시하지 않는다.

### 완료 조건

- [ ] 세션 종료 시 최소 10개, 주차 종료 시 20개가 있다.
- [ ] 모든 Golden에 안정적인 ID와 위험 metadata가 있다.

## 세션 3: `EvaluationDataset`과 JSONL

> - 예상 시간: 60~90분
> - 선행 조건: reviewed Golden 최소 10개

권장 파일:

```text
evals/data/refund_goldens.jsonl
tests/evals/test_week3_session3_local_dataset.py
```

예시 JSONL:

```json
{"input":"지난주 구매를 환불하려면 어떻게 하나요?","expected_output":"구매 후 30일 이내 주문 번호와 함께 고객센터에 요청합니다.","context":["구매 후 30일 이내에는 주문 번호와 함께 고객센터에 요청하면 전액 환불할 수 있다."],"additional_metadata":{"case_id":"refund-normal-001","category":"normal","suite":"smoke"}}
```

### 구현 작업

- [ ] `Golden` 목록으로 `EvaluationDataset`을 만든다.
- [ ] JSONL 한 줄이 Golden 하나가 되게 저장한다.
- [ ] 프로젝트 루트 기준으로 파일 경로를 안정적으로 해석한다.
- [ ] 다시 로드한 개수와 `case_id`를 검사한다.
- [ ] single-turn과 conversational Golden을 섞지 않는 제약을 확인한다.

### API 없는 데이터 검증

- [ ] 중복 `case_id`가 없다.
- [ ] `input`, reference, 위험 metadata가 비어 있지 않다.
- [ ] runtime field가 저장되어 있지 않다.
- [ ] 실제 개인정보나 key 형태의 값이 없다.

### 완료 조건

- [ ] 코드 변경 없이 JSONL 행을 추가할 수 있다.
- [ ] 로컬 파일에서 동일 dataset을 재구성할 수 있다.
- [ ] 데이터 검증 테스트가 judge 없이 통과한다.

## 세션 4: pytest parameterization과 데이터 리뷰

> - 예상 시간: 60~90분
> - 선행 조건: 앱 callback과 JSONL dataset

권장 파일:

```text
tests/evals/test_week3_session4_dataset_regression.py
```

### Golden에서 runtime test case로

1. Golden의 `input`으로 `answer_refund_question()`을 호출한다.
2. 답변은 `actual_output`, 검색 결과는 `retrieval_context`에 넣는다.
3. Golden의 `expected_output`, `context`를 reference로 전달한다.
4. pytest ID는 `case_id`를 사용한다.

- [ ] `pytest.mark.parametrize`로 Golden을 순회한다.
- [ ] `case_id`가 실패 리포트에 표시된다.
- [ ] 모든 데이터에는 deterministic 검증을 먼저 실행한다.
- [ ] smoke 5개에만 judge metric을 우선 연결한다.
- [ ] `smoke`, `full`, `known_bug` 선택 규칙을 정의한다.

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

## 막히기 쉬운 지점

- production 수준의 RAG 앱을 먼저 만들려다 dataset 학습이 지연된다.
- Golden에 현재 모델의 `actual_output`을 저장해 변경 비교가 불가능해진다.
- 20개를 숫자로만 채워 중복되고 쉬운 사례가 많아진다.
- parameterized test ID가 숫자여서 실패한 Golden을 찾기 어렵다.

참고: [Evaluation Datasets](https://deepeval.com/docs/evaluation-datasets), [Unit Testing in CI/CD](https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd)

이전: [2주차 — metric과 GEval](week2_metrics_and_geval.md) · 다음: [4주차 — RAG 평가](week4_rag_evaluation.md)
