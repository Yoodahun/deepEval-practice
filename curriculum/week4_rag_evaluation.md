# 4주차 — RAG end-to-end와 실패 원인 분리

> - 상태: 예정
> - 권장 분량: 4회
> - 필수 트랙: RAG
> - 핵심 질문: 낮은 score가 retriever와 generator 중 어디의 문제인지 어떻게 구분할 것인가?

4주차에는 tracing을 먼저 배우지 않는다. 3주차의 환불 앱과 runtime field만으로 end-to-end, retriever, generator 평가를 분리한다. 이 흐름이 안정된 뒤에만 선택 심화에서 span-level tracing을 추가한다.

## 주차 학습 지도

| 세션 | 난이도 | 평가 범위 | 핵심 산출물 |
| --- | ---: | --- | --- |
| 1. RAG end-to-end | 2/5 | 사용자 관점의 최종 결과 | black-box smoke eval |
| 2. retriever | 3/5 | 검색 품질 | 누락·잡음·순위 사례 |
| 3. generator | 3/5 | 관련성·근거 충실성 | generator 결함 사례 |
| 4. suite 통합 | 3/5 | 진단 흐름 | 10개 RAG 사례와 triage 표 |

## 먼저 구분할 데이터

| field | 의미 | 평가 관점 |
| --- | --- | --- |
| `input` | 사용자 질문 | 전체 |
| `expected_output` | 이상적인 답변 reference | end-to-end, 일부 contextual metric |
| `context` | 사람이 검토한 이상적 근거 | ground truth |
| `retrieval_context` | retriever의 실제 반환 문서 | retriever/generator runtime |
| `actual_output` | generator의 실제 답변 | end-to-end/generator runtime |

`context`와 `retrieval_context`가 우연히 같은 내용이어도 역할은 다르다. 하나는 reviewer가 정한 정답 근거이고 다른 하나는 앱이 실제 관측한 검색 결과다.

## 세션 1: tracing 없는 end-to-end RAG 평가

> - 예상 시간: 60~90분
> - 선행 조건: 3주차 parameterized regression

권장 파일:

```text
tests/evals/test_week4_session1_rag_end_to_end.py
```

### 왜 black-box부터 시작하는가

사용자는 내부 retriever score가 아니라 최종 답변을 경험한다. 먼저 최종 동작이 사용자 목표를 만족하는지 확인한 다음, 실패할 때 내부 컴포넌트를 좁힌다.

- [ ] 중요한 smoke Golden 5개를 선택한다.
- [ ] 각 Golden으로 앱을 실행해 `LLMTestCase`를 만든다.
- [ ] `AnswerRelevancyMetric`으로 질문에 직접 답하는지 본다.
- [ ] 2주차 custom 완전성 metric으로 다음 행동에 필요한 정보가 있는지 본다.
- [ ] 실패 reason과 사용자 영향을 함께 기록한다.

### 의도적인 한계 사례

최종 답변은 좋지만 retriever가 불필요한 문서를 많이 가져온 사례를 만든다. end-to-end metric이 통과할 수 있다는 점을 관찰한다. 이것이 retriever 평가를 별도로 수행하는 이유다.

### 완료 조건

- [ ] black-box 평가가 답할 수 있는 질문과 없는 질문을 구분한다.
- [ ] 최종 답변 실패 한 개를 재현하고 사용자 영향을 기록한다.

## 세션 2: retriever 평가

> - 예상 시간: 60~90분
> - 선행 조건: `context`와 `retrieval_context` 구분

권장 파일:

```text
tests/evals/test_week4_session2_rag_retriever.py
```

### DeepEval 4.1.4 required field

| metric | required field | 주로 보는 실패 |
| --- | --- | --- |
| `ContextualRelevancyMetric` | `input`, `retrieval_context` | 검색 결과 전체에 무관한 내용이 많음 |
| `ContextualRecallMetric` | `input`, `retrieval_context`, `expected_output` | 답변에 필요한 근거 누락 |
| `ContextualPrecisionMetric` | `input`, `retrieval_context`, `expected_output` | 관련 근거의 순위와 불필요한 결과 |

설치 버전이 바뀌면 공식 문서와 metric 객체의 required parameter를 다시 확인한다.

### 네 가지 retrieval fixture

- [ ] 필요한 문서를 모두 포함한 clean retrieval
- [ ] 핵심 정책 문서가 하나 빠진 missing retrieval
- [ ] 관련 문서와 배송·회원등급 문서가 섞인 noisy retrieval
- [ ] 핵심 문서가 뒤쪽에 위치한 poorly-ranked retrieval

각 fixture에서는 retrieval만 바꾸고 입력과 expected output은 유지한다. 여러 컴포넌트를 동시에 바꾸면 metric의 진단 신호를 해석하기 어렵다.

### metric 선택 실험

- [ ] recall이 missing retrieval에 반응하는지 확인한다.
- [ ] relevancy가 noisy retrieval에 반응하는지 확인한다.
- [ ] precision이 ranking 차이를 구분하는지 확인한다.
- [ ] suite에 세 metric을 모두 넣지 않고 실제 위험을 보호하는 1~2개를 고른다.

### 완료 조건

- [ ] recall, relevancy, precision을 사례로 구분한다.
- [ ] 낮은 contextual score를 retriever/reranker 진단 가설로 연결한다.

## 세션 3: generator 평가

> - 예상 시간: 60~90분
> - 선행 조건: 세션 2 완료

권장 파일:

```text
tests/evals/test_week4_session3_rag_generator.py
```

### 같은 retrieval에서 답변만 변경

- [ ] 좋은 검색 + 좋은 답변
- [ ] 좋은 검색 + 질문에서 이탈한 답변
- [ ] 좋은 검색 + 근거에 없는 90일 환불 주장
- [ ] 검색 누락 + 우연히 그럴듯한 답변

### metric의 책임

| metric | 평가 질문 | 낮을 때 먼저 볼 대상 |
| --- | --- | --- |
| `AnswerRelevancyMetric` | 질문에 직접 답하는가? | generator prompt/output |
| `FaithfulnessMetric` | 답변의 주장이 검색 근거로 뒷받침되는가? | generator grounding |
| custom 완전성 `GEval` | 사용자가 다음 행동을 할 정보가 충분한가? | 답변 구성 로직 |

- [ ] 관련성은 높지만 faithfulness가 낮은 사례를 확인한다.
- [ ] faithfulness는 높지만 질문과 무관한 사례를 확인한다.
- [ ] 표준 metric과 custom metric이 서로 다른 수정 행동으로 이어지는지 기록한다.

### 완료 조건

- [ ] 낮은 faithfulness를 generator grounding 문제로 분류한다.
- [ ] 관련성, 근거 충실성, 제품 완전성을 서로 바꿔 사용하지 않는다.

## 세션 4: RAG 진단 suite 통합

> - 예상 시간: 60~90분
> - 선행 조건: 세션 1~3 완료

반드시 재현할 네 조합:

| retrieval | generation | 예상 진단 |
| --- | --- | --- |
| 좋음 | 좋음 | 전체 통과 |
| 좋음 | 근거 없는 주장 | generator/faithfulness 실패 |
| 핵심 근거 누락 | 그럴듯한 답변 | retriever 실패, 최종 답변은 우연히 통과 가능 |
| 올바른 근거 + 과도한 잡음 | 좋은 답변 | contextual metric 실패 가능 |

### triage metadata

기존 20개 Golden 중 10개 이상을 골라 다음 값을 보완한다.

```json
{
  "case_id": "refund-rag-004",
  "protected_risk": "unsupported_refund_window",
  "suspected_component": "generator",
  "expected_failure_axis": "faithfulness"
}
```

- [ ] 실제 metric 결과와 예상 컴포넌트를 비교한다.
- [ ] 결과를 `retriever`, `generator`, `data`, `unknown`으로 분류한다.
- [ ] metric 실패를 확정 원인이 아니라 조사할 진단 가설로 표현한다.
- [ ] 잘못된 reference는 앱 품질 실패와 분리한다.

## 4주차 완료 조건

- [ ] end-to-end와 retriever/generator 평가 질문을 구분한다.
- [ ] RAG 심화 사례가 10개 이상 있다.
- [ ] 낮은 score에서 먼저 조사할 컴포넌트를 근거와 함께 지목한다.
- [ ] tracing 없이도 동일 실패를 재현할 수 있다.

## 막히기 쉬운 지점

- 모든 RAG metric을 모든 test case에 붙여 비용과 noise가 커진다.
- retrieval과 generation을 동시에 바꿔 실패 원인을 알 수 없다.
- contextual metric이 낮다는 이유만으로 generator를 수정한다.
- 최종 답변이 우연히 맞았다는 이유로 누락된 retrieval을 통과 처리한다.

참고: [RAG QA Agent Tutorial](https://deepeval.com/tutorials/rag-qa-agent/evaluation), [End-to-End Evaluation](https://deepeval.com/docs/evaluation-end-to-end-llm-evals)

이전: [3주차 — dataset과 regression](week3_dataset_and_regression.md) · 다음: [5주차 — 보정과 신뢰도](week5_calibration_and_reliability.md)
