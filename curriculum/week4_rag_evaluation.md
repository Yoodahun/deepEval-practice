# 4주차 — RAG end-to-end와 실패 원인 분리

> - 상태: 예정
> - 권장 분량: 4회
> - 필수 트랙: RAG
> - 핵심 질문: 낮은 score가 retriever와 generator 중 어디의 문제인지 어떻게 구분할 것인가?

RAG 평가는 하나의 총점으로 끝내지 않는다. 사용자가 받은 최종 답변이 실패했는지를
end-to-end 평가로 확인하고, 같은 실패를 retriever의 근거 수집 문제와
generator의 근거 사용 문제로 나누어 조사한다. 같은 나쁜 답변도 필요한 문서를
못 찾았거나, 올바른 문서를 찾고도 왜곡했거나, 근거와 답은 맞지만 필수 절차를
누락해서 발생할 수 있기 때문이다.

이번 주의 목표는 metric 이름을 암기하는 것이 아니다. **어떤 field를 고정하고
무엇을 바꾸었는지, 낮은 score가 어떤 진단 가설을 가리키는지, 그 score만으로
무엇을 확정할 수 없는지**를 설명하는 것이 목표다. tracing은 먼저 배우지 않는다.
3주차의 환불 앱과 runtime field만으로 평가 범위를 분리한 뒤 선택 심화에서
span-level tracing을 추가한다.

## 이번 주에 배우는 RAG 진단 흐름

```text
input
  ↓
retriever ──→ retrieval_context
                    ↓
               generator ──→ actual_output

reviewer가 준비한 기준: context, expected_output
```

| 평가 범위 | 핵심 질문 | 주로 비교하는 값 | 이 단계의 한계 |
| --- | --- | --- | --- |
| end-to-end | 사용자가 받은 최종 결과가 유용한가? | `input`, `actual_output`, 필요시 `expected_output` | 실패 원인을 바로 확정하지 못함 |
| retriever | 답변에 필요한 근거를 잘 찾았는가? | `input`/reference와 `retrieval_context` | generator가 근거를 어떻게 썼는지 모름 |
| generator | 주어진 근거로 질문에 제대로 답했는가? | `input`, `retrieval_context`, `actual_output` | 검색 근거 자체가 정답인지는 별개 |

end-to-end는 사용자에게 나타난 **증상**을 찾고 component metric은 **첫 조사
대상**을 좁힌다. 반대로 component score만 보면 최종 사용자 피해를 놓칠 수
있으므로 둘 중 하나로 다른 하나를 대체하지 않는다.

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

`retrieval_context`가 있다고 해서 reviewed reference가 있는 것은 아니다.
retriever가 잘못 가져온 문서도 runtime observation에는 그대로 들어간다.
따라서 Faithfulness가 높아도 그 문서 자체가 실제 정책과 맞는지는 별도
reference와 사람 검토가 필요하다.

## 세션 1: tracing 없는 end-to-end RAG 평가

> - 예상 시간: 60~90분
> - 선행 조건: 3주차 parameterized regression

권장 파일:

```text
tests/evals/test_week4_session1_rag_end_to_end.py
```

### 왜 black-box부터 시작하는가

사용자는 내부 retriever score가 아니라 최종 답변을 경험한다. 먼저 최종 동작이 사용자 목표를 만족하는지 확인한 다음, 실패할 때 내부 컴포넌트를 좁힌다.

이 세션에서 배우는 것은 “최종 답변 실패를 사용자 위험으로 표현하되 원인은
아직 확정하지 않는 것”이다. 예를 들어 잘못된 90일 환불 안내는 사용자의 환불
기회를 놓치게 할 수 있지만, black-box 결과만으로 검색이 틀렸는지 생성이
왜곡했는지는 알 수 없다.

- [ ] 중요한 smoke Golden 5개를 선택한다.
- [ ] 각 Golden으로 앱을 실행해 `LLMTestCase`를 만든다.
- [ ] `AnswerRelevancyMetric`으로 질문에 직접 답하는지 본다.
- [ ] 2주차 custom 완전성 metric으로 다음 행동에 필요한 정보가 있는지 본다.
- [ ] 실패 reason과 사용자 영향을 함께 기록한다.

### 의도적인 한계 사례

최종 답변은 좋지만 retriever가 불필요한 문서를 많이 가져온 사례를 만든다. end-to-end metric이 통과할 수 있다는 점을 관찰한다. 이것이 retriever 평가를 별도로 수행하는 이유다.

현재 답변이 우연히 좋더라도 noisy retrieval은 토큰 비용과 지연을 늘리고,
다음 질문에서 잘못된 문서를 선택할 가능성을 높인다. 따라서 “최종 답변 통과”를
“retriever 정상”으로 해석하지 않는다.

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

### recall, relevancy, precision을 쉽게 구분하기

환불 답변에 필요한 근거를 `30일 정책`, `주문 번호`, `고객센터 요청`이라고
가정한다.

| fixture | 예시 검색 결과 | 예상되는 핵심 신호 |
| --- | --- | --- |
| clean | `[30일, 주문 번호, 고객센터]` | 필요한 근거가 모두 있고 잡음이 적음 |
| missing | `[30일, 고객센터]` | 관련 문서만 있어도 주문 번호 근거는 누락될 수 있음 |
| noisy | `[배송, 30일, 회원등급, 주문 번호, 고객센터]` | 필요한 근거는 있지만 불필요한 결과가 많음 |
| poorly-ranked | `[배송, 회원등급, 30일, 주문 번호, 고객센터]` | 근거의 존재와 앞쪽 순위는 다른 문제 |

- **Recall**은 필요한 근거를 빠뜨리지 않았는지 묻는다.
- **Relevancy**는 가져온 결과가 질문에 관련 있는지 묻는다.
- **Precision**은 관련 근거가 불필요한 결과보다 앞에 배치되는지 본다.

점수의 정확한 숫자를 외우지 않는다. fixture를 실행하기 전에 어느 metric이
어느 방향으로 움직일지 먼저 적고, 실제 reason이 그 결함을 읽었는지 비교한다.
제품 위험이 근거 누락이면 recall, top-k 잡음과 비용이면 relevancy/precision처럼
낮은 score가 서로 다른 수정 행동으로 이어지는 최소 1~2개만 suite에 남긴다.

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

### 왜 retrieval을 고정하는가

좋은 검색 결과를 고정하고 `actual_output`만 바꾸면 score 차이를 generator의
행동과 연결하기 쉬워진다. 이것은 production 전체를 재현하는 단계가 아니라
한 변수만 바꾸는 component 격리 실험이다.

### 같은 clean retrieval에서 답변만 변경

- [ ] 좋은 검색 + 좋은 답변
- [ ] 좋은 검색 + 질문에서 이탈한 답변
- [ ] 좋은 검색 + 근거에 없는 90일 환불 주장
- [ ] 좋은 검색 + 근거에는 충실하지만 필수 절차가 빠진 답변

`검색 누락 + 우연히 그럴듯한 답변`은 retrieval까지 바뀌므로 같은 실험에
섞지 않는다. 세션 4의 교차 컴포넌트 사례로 옮겨 end-to-end는 통과해도
retriever 실패가 남는 상황을 관찰한다.

### metric의 책임

| metric | 평가 질문 | 낮을 때 먼저 볼 대상 |
| --- | --- | --- |
| `AnswerRelevancyMetric` | 질문에 직접 답하는가? | generator prompt/output |
| `FaithfulnessMetric` | 답변의 주장이 검색 근거로 뒷받침되는가? | generator grounding |
| custom 완전성 `GEval` | 사용자가 다음 행동을 할 정보가 충분한가? | 답변 구성 로직 |

세 metric은 같은 답변을 다른 질문으로 읽는다.

- 환불 질문에 배송 설명을 하면 Answer Relevancy가 낮을 수 있다.
- 검색 근거는 30일인데 답변이 90일이면 Faithfulness가 낮을 수 있다.
- 30일은 맞지만 주문 번호와 고객센터가 빠지면 완전성 GEval이 낮을 수 있다.

Faithfulness는 사실 정확도 metric이 아니다. 잘못 검색된 “90일 정책”을
generator가 그대로 사용하면 Faithfulness는 높을 수 있다. 반대로 격리 실험에서
`retrieval_context`가 정상임을 확인하고 고정했을 때 낮은 Faithfulness가
generator grounding을 강하게 의심하게 한다.

- [ ] 관련성은 높지만 faithfulness가 낮은 사례를 확인한다.
- [ ] faithfulness는 높지만 제품 완전성이 낮은 사례를 확인한다.
- [ ] 표준 metric과 custom metric이 서로 다른 수정 행동으로 이어지는지 기록한다.

### 완료 조건

- [ ] 정상 retrieval을 고정한 실험에서 낮은 faithfulness를 generator grounding 가설로 연결한다.
- [ ] 관련성, 근거 충실성, 제품 완전성을 서로 바꿔 사용하지 않는다.

## 세션 4: RAG 진단 suite 통합

> - 예상 시간: 60~90분
> - 선행 조건: 세션 1~3 완료

반드시 재현할 네 조합:

| retrieval | generation | 예상 진단 |
| --- | --- | --- |
| 좋음 | 좋음 | 전체 통과 |
| 좋음 | 근거 없는 주장 | generator/faithfulness 실패 |
| 핵심 근거 누락 | 불완전하거나 잘못된 답변 | retriever와 end-to-end 모두 실패 가능 |
| 올바른 근거 + 과도한 잡음 | 좋은 답변 | contextual metric 실패 가능 |

추가로 다음 교차 사례를 포함한다.

| 교차 사례 | 관찰할 점 |
| --- | --- |
| 잘못된 정책 문서 검색 + 그 문서대로 답변 | Faithfulness가 높아도 실제 답변은 틀릴 수 있음 |
| 좋은 검색 + 근거에는 충실하지만 절차 누락 | Faithfulness 통과, 완전성 실패 가능 |
| 핵심 근거 누락 + 모델 사전지식으로 정답 | end-to-end 통과 가능, recall과 faithfulness는 실패 가능 |
| 배송 안내가 섞인 noisy retrieval + 배송만 요약 | Faithfulness는 높아도 Answer Relevancy가 낮고 retriever 잡음도 의심 |
| 오래되거나 잘못된 reference | 앱이 아니라 `data` 실패로 분류 |

### score를 원인이 아니라 증거로 읽는 순서

1. `case_id` 연결, input-reference 짝, field mapping, reference 승인·최신성 같은 평가 데이터 무결성을 확인한다. 오류가 있으면 `data`로 분류하고 앱 진단을 중단한다.
2. end-to-end 실패가 실제 사용자 영향을 만드는지 확인한다.
3. `retrieval_context`에 필요한 근거가 있고 잡음과 순위가 적절한지 본다.
4. `actual_output`의 주장이 retrieval 근거에 충실한지 본다.
5. 답변이 질문에 직접 답하고 필수 절차를 포함하는지 본다.
6. 증거를 바탕으로 `retriever`, `generator`, `data`, `unknown` 중 첫 조사 대상을 기록한다.

예를 들어 end-to-end fail, retriever pass, Faithfulness fail이면 generator
grounding을 먼저 조사한다. end-to-end fail, retriever pass, Faithfulness pass,
완전성 fail이면 answer composition을 먼저 조사한다. 모든 score가 원문과
모순되면 억지로 분류하지 않고 reference, judge 또는 data 문제를 확인한 뒤
`unknown`으로 남긴다.

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
- [ ] 실행 전 예상 metric, 실제 score/reason, 확인한 원문, 첫 조사 대상과 최종 분류를 기록한다.

## 4주차 완료 조건

- [ ] end-to-end와 retriever/generator 평가 질문을 구분한다.
- [ ] RAG 심화 사례가 10개 이상 있다.
- [ ] 낮은 score에서 먼저 조사할 컴포넌트를 근거와 함께 지목한다.
- [ ] tracing 없이도 동일 실패를 재현할 수 있다.
- [ ] 각 metric의 비교 대상과 blind spot을 자신의 말로 설명할 수 있다.
- [ ] 같은 사용자 실패를 retriever 원인과 generator 원인으로 각각 재현할 수 있다.
- [ ] 근거가 부족하면 원인을 확정하지 않고 `unknown`으로 남길 수 있다.

## 막히기 쉬운 지점

- 모든 RAG metric을 모든 test case에 붙여 비용과 noise가 커진다.
- retrieval과 generation을 동시에 바꿔 실패 원인을 알 수 없다.
- contextual metric이 낮다는 이유만으로 generator를 수정한다.
- 최종 답변이 우연히 맞았다는 이유로 누락된 retrieval을 통과 처리한다.
- Faithfulness가 높다는 이유로 검색 근거와 실제 정책까지 옳다고 결론낸다.

참고: [RAG QA Agent Tutorial](https://deepeval.com/tutorials/rag-qa-agent/evaluation), [End-to-End Evaluation](https://deepeval.com/docs/evaluation-end-to-end-llm-evals)

이전: [3주차 — dataset과 regression](week3_dataset_and_regression.md) · 다음: [5주차 — 보정과 신뢰도](week5_calibration_and_reliability.md)
