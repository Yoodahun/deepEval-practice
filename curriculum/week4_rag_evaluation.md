# 4주차 — RAG end-to-end와 실패 원인 분리

> - 상태: 세션 1~2 완료, 세션 3 진행 중, 세션 4 예정
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


| 평가 범위      | 핵심 질문                 | 주로 비교하는 값                                       | 이 단계의 한계                  |
| ---------- | --------------------- | ----------------------------------------------- | ------------------------- |
| end-to-end | 사용자가 받은 최종 결과가 유용한가?  | `input`, `actual_output`, 필요시 `expected_output` | 실패 원인을 바로 확정하지 못함         |
| retriever  | 답변에 필요한 근거를 잘 찾았는가?   | `input`/reference와 `retrieval_context`          | generator가 근거를 어떻게 썼는지 모름 |
| generator  | 주어진 근거로 질문에 제대로 답했는가? | `input`, `retrieval_context`, `actual_output`   | 검색 근거 자체가 정답인지는 별개        |


end-to-end는 사용자에게 나타난 **증상**을 찾고 component metric은 **첫 조사
대상**을 좁힌다. 반대로 component score만 보면 최종 사용자 피해를 놓칠 수
있으므로 둘 중 하나로 다른 하나를 대체하지 않는다.

## 주차 학습 지도


| 세션                | 난이도 | 평가 범위         | 핵심 산출물               |
| ----------------- | --- | ------------- | -------------------- |
| 1. RAG end-to-end | 2/5 | 사용자 관점의 최종 결과 | black-box smoke eval |
| 2. retriever      | 3/5 | 검색 품질         | 누락·잡음·순위 사례          |
| 3. generator      | 3/5 | 관련성·근거 충실성    | generator 결함 사례      |
| 4. suite 통합       | 3/5 | 진단 흐름         | 10개 RAG 사례와 triage 표 |




## 먼저 구분할 데이터


| field               | 의미                  | 평가 관점                            |
| ------------------- | ------------------- | -------------------------------- |
| `input`             | 사용자 질문              | 전체                               |
| `expected_output`   | 이상적인 답변 reference   | end-to-end, 일부 contextual metric |
| `context`           | 사람이 검토한 이상적 근거      | ground truth                     |
| `retrieval_context` | retriever의 실제 반환 문서 | retriever/generator runtime      |
| `actual_output`     | generator의 실제 답변    | end-to-end/generator runtime     |


`context`와 `retrieval_context`가 우연히 같은 내용이어도 역할은 다르다. 하나는 reviewer가 정한 정답 근거이고 다른 하나는 앱이 실제 관측한 검색 결과다.

`retrieval_context`가 있다고 해서 reviewed reference가 있는 것은 아니다.
retriever가 잘못 가져온 문서도 runtime observation에는 그대로 들어간다.
따라서 Faithfulness가 높아도 그 문서 자체가 실제 정책과 맞는지는 별도
reference와 사람 검토가 필요하다.

## 세션 1: tracing 없는 end-to-end RAG 평가 — 완료

> - 예상 시간: 60~90분
> - 선행 조건: 3주차 parameterized regression

권장 파일:

```text
tests/evals/test_week4_session1_rag_end_to_end.py
tests/evals/week4_session1_rag_end_to_end_solution.py
evals/metrics/refund_completeness.py
```

학생용 파일은 3주차에 만든 JSONL과 앱 callback을 그대로 사용한다. TODO 1~4를
순서대로 완성하며 reference와 runtime field를 다시 구분하고, 두 end-to-end
metric의 실패를 사용자 위험으로 기록한다.


| TODO | 구현 대상                      | 완료 후 확인할 것                                      |
| ---- | -------------------------- | ----------------------------------------------- |
| 1    | metadata로 smoke Golden 선택  | reviewed smoke 5개만 남는다.                         |
| 2    | 앱 실행 결과로 `LLMTestCase` 생성  | `context`와 `retrieval_context`가 섞이지 않는다.        |
| 3    | `AnswerRelevancyMetric` 생성 | 질문 직접성이라는 한 품질 축을 평가한다.                         |
| 4    | 실패 관찰 기록                   | score/reason과 사용자 영향은 연결하되 원인은 `unknown`으로 남긴다. |


먼저 외부 API 없이 TODO의 구조와 noisy retrieval 한계를 확인한다.

```bash
.venv/bin/python -m pytest \
  tests/evals/test_week4_session1_rag_end_to_end.py \
  -k "not judge" -v
```

구조 검사를 통과한 뒤에만 smoke 5개와 의도적인 90일 오류를 judge로 실행한다.

```bash
DEEPEVAL_WEEK4_SESSION1_RUN_JUDGE=1 \
  .venv/bin/deepeval test run \
  tests/evals/test_week4_session1_rag_end_to_end.py -v

# 직접 완성한 뒤 참고 답안의 API 없는 구조만 비교
.venv/bin/python -m \
  tests.evals.week4_session1_rag_end_to_end_solution --check
```

첫 명령에는 비용이 들지 않는다. judge 명령은 `OPENAI_API_KEY`와 비용이
필요하며, threshold는 5주차 보정 전의 임시 값이다.

### 왜 black-box부터 시작하는가

사용자는 내부 retriever score가 아니라 최종 답변을 경험한다. 먼저 최종 동작이 사용자 목표를 만족하는지 확인한 다음, 실패할 때 내부 컴포넌트를 좁힌다.

이 세션에서 배우는 것은 “최종 답변 실패를 사용자 위험으로 표현하되 원인은
아직 확정하지 않는 것”이다. 예를 들어 잘못된 90일 환불 안내는 사용자의 환불
기회를 놓치게 할 수 있지만, black-box 결과만으로 검색이 틀렸는지 생성이
왜곡했는지는 알 수 없다.

- [x] 중요한 smoke Golden 5개를 선택한다.
- [x] 각 Golden으로 앱을 실행해 `LLMTestCase`를 만든다.
- [x] `AnswerRelevancyMetric`으로 질문에 직접 답하는지 본다.
- [ ] 2주차 custom 완전성 metric으로 다음 행동에 필요한 정보가 있는지 본다.
- [x] 실패 reason과 사용자 영향을 함께 기록한다.



### 의도적인 한계 사례

최종 답변은 좋지만 retriever가 불필요한 문서를 많이 가져온 사례를 만든다. end-to-end metric이 통과할 수 있다는 점을 관찰한다. 이것이 retriever 평가를 별도로 수행하는 이유다.

현재 답변이 우연히 좋더라도 noisy retrieval은 토큰 비용과 지연을 늘리고,
다음 질문에서 잘못된 문서를 선택할 가능성을 높인다. 따라서 “최종 답변 통과”를
“retriever 정상”으로 해석하지 않는다.

### 완료 조건

- [x] black-box 평가가 답할 수 있는 질문과 없는 질문을 구분한다.
- [x] 최종 답변 실패 한 개를 재현하고 사용자 영향을 기록한다.



## 세션 2: retriever 평가 — 완료

> - 예상 시간: 60~90분
> - 선행 조건: `context`와 `retrieval_context` 구분

권장 파일:

```text
tests/evals/test_week4_session2_rag_retriever.py
tests/evals/week4_session2_rag_retriever_solution.py
```

학생용 파일은 같은 질문과 기대 답변을 유지하고 `retrieval_context`만 바꾸는
격리 실험이다. TODO 1~3을 순서대로 완성하며 metric을 실행하기 전에 예상 신호를
먼저 기록하고, 낮은 점수를 서로 다른 retriever/reranker 진단 가설로 연결한다.


| TODO | 구현 대상                                     | 완료 후 확인할 것                                  |
| ---- | ----------------------------------------- | ------------------------------------------- |
| 1    | clean/missing/noisy/poorly-ranked fixture | 누락, 잡음 양, 순서 효과가 분리된다.                      |
| 2    | fixture별 primary signal 예측                | recall, relevancy, precision의 책임을 사례로 구분한다. |
| 3    | contextual metric 생성자                     | 세 metric을 같은 threshold와 실행 조건으로 비교한다.       |


먼저 외부 API 없이 fixture, field와 metric 설정을 확인한다.

```bash
.venv/bin/python -m pytest \
  tests/evals/test_week4_session2_rag_retriever.py \
  -k "not judge" -v
```

구조 검사를 통과한 뒤 clean/defective fixture 세 쌍을 총 6회 judge로 비교한다.

```bash
DEEPEVAL_WEEK4_SESSION2_RUN_JUDGE=1 \
  .venv/bin/deepeval test run \
  tests/evals/test_week4_session2_rag_retriever.py -v

# 직접 완성한 뒤 참고 답안의 API 없는 구조만 비교
.venv/bin/python -m \
  tests.evals.week4_session2_rag_retriever_solution --check
```

judge 결과는 절대 점수보다 `clean > missing`, `clean > noisy`,
`noisy > poorly-ranked`의 방향과 reason이 예상 결함을 읽었는지 먼저 확인한다.

### DeepEval 4.1.4 required field


| metric                      | required field                                  | 주로 보는 실패             |
| --------------------------- | ----------------------------------------------- | -------------------- |
| `ContextualRelevancyMetric` | `input`, `retrieval_context`                    | 검색 결과 전체에 무관한 내용이 많음 |
| `ContextualRecallMetric`    | `input`, `retrieval_context`, `expected_output` | 답변에 필요한 근거 누락        |
| `ContextualPrecisionMetric` | `input`, `retrieval_context`, `expected_output` | 관련 근거의 순위와 불필요한 결과   |


설치 버전이 바뀌면 공식 문서와 metric 객체의 required parameter를 다시 확인한다.

### recall, relevancy, precision을 쉽게 구분하기

환불 답변에 필요한 근거를 `30일 정책`, `주문 번호`, `고객센터 요청`이라고
가정한다.


| fixture       | 예시 검색 결과                       | 예상되는 핵심 신호                    |
| ------------- | ------------------------------ | ----------------------------- |
| clean         | `[30일, 주문 번호, 고객센터]`           | 필요한 근거가 모두 있고 잡음이 적음          |
| missing       | `[30일, 고객센터]`                  | 관련 문서만 있어도 주문 번호 근거는 누락될 수 있음 |
| noisy         | `[30일, 주문 번호, 고객센터, 배송, 회원등급]` | 필요한 근거는 앞에 있지만 잡음이 섞임         |
| poorly-ranked | `[배송, 회원등급, 30일, 주문 번호, 고객센터]` | 같은 문서지만 잡음이 관련 근거보다 앞에 있음     |


- **Recall**은 필요한 근거를 빠뜨리지 않았는지 묻는다.
- **Relevancy**는 가져온 결과가 질문에 관련 있는지 묻는다.
- **Precision**은 관련 근거가 불필요한 결과보다 앞에 배치되는지 본다.

점수의 정확한 숫자를 외우지 않는다. fixture를 실행하기 전에 어느 metric이
어느 방향으로 움직일지 먼저 적고, 실제 reason이 그 결함을 읽었는지 비교한다.
이 세션에서는 세 metric을 모두 실행해 책임 차이를 학습한다. 최종 suite에 무엇을
남길지는 실제 사용자 위험, 관찰 결과와 비용을 함께 볼 수 있는 세션 4에서 정한다.

### 네 가지 retrieval fixture

- [x] 필요한 문서를 모두 포함한 clean retrieval
- [x] 핵심 정책 문서가 하나 빠진 missing retrieval
- [x] 관련 문서와 배송·회원등급 문서가 섞인 noisy retrieval
- [x] 핵심 문서가 뒤쪽에 위치한 poorly-ranked retrieval

각 fixture에서는 retrieval만 바꾸고 입력과 expected output은 유지한다. 여러 컴포넌트를 동시에 바꾸면 metric의 진단 신호를 해석하기 어렵다.

### metric 비교 실험

- [x] recall이 missing retrieval에 반응하는지 확인한다.
- [x] relevancy가 noisy retrieval에 반응하는지 확인한다.
- [x] precision이 ranking 차이를 구분하는지 확인한다.
- [x] 낮은 recall, relevancy, precision을 각각 coverage, 잡음, reranking 조사 가설로 연결한다.



### 완료 조건

- [x] recall, relevancy, precision을 사례로 구분한다.
- [x] 낮은 contextual score를 retriever/reranker 진단 가설로 연결한다.



## 세션 3: generator 평가

> - 예상 시간: 60~90분
> - 선행 조건: 세션 2 완료

### generator란 무엇인가

RAG는 보통 **retriever**와 **generator** 두 컴포넌트로 나누어 생각한다.

```text
사용자 질문
   ↓
retriever: 질문에 필요한 문서를 찾는다.
   ↓
retrieval_context: 실제로 검색된 문서 목록
   ↓
generator: 질문과 검색 문서를 읽고 사용자에게 보여 줄 답변을 만든다.
   ↓
actual_output: 최종 답변
```

환불 질문을 예로 들면 retriever는 “30일 이내”, “주문 번호와 구매일”,
“고객센터로 요청”이라는 정책 문서를 찾는다. generator는 이 문서들을 그대로
나열하는 대신 사용자의 질문에 맞는 자연스러운 답변으로 구성한다.

```text
질문: 지난주에 산 상품을 환불하려면 어떻게 해야 하나요?

retriever가 찾은 문서:
- 구매 후 30일 이내에는 전액 환불을 요청할 수 있습니다.
- 환불 요청에는 주문 번호와 구매일이 필요합니다.
- 환불은 고객센터를 통해 요청해야 합니다.

generator가 만든 답변:
지난주 구매 건은 30일 이내이므로 주문 번호와 구매일을 준비해
고객센터로 전액 환불을 요청해 주세요.
```

retriever가 좋은 문서를 찾아도 generator는 실패할 수 있다. 질문과 무관한
배송 정보를 답하거나, 30일을 90일로 바꾸거나, 주문 번호와 고객센터 절차를
빠뜨릴 수 있기 때문이다. 반대로 generator가 검색 문서를 충실히 요약했어도
retriever가 잘못된 정책을 가져왔다면 최종 답변은 실제 정책과 다를 수 있다.

이번 세션에서 말하는 **generator 평가**는 “검색 결과가 옳은가?”가 아니라
**“정상으로 확인된 검색 결과를 generator가 질문에 맞고, 근거에 충실하며,
필요한 정보가 빠지지 않은 답변으로 만들었는가?”**를 평가하는 것이다.

실제 서비스에서는 LLM이 generator 역할을 맡는 경우가 많다. 하지만 이번
격리 실험에서는 LLM을 직접 호출하지 않고 미리 작성한 네 답변 문자열을
``actual_output``으로 사용한다. 이렇게 하면 생성 모델의 무작위성과 호출 비용을
제외하고, 각 metric이 어떤 generator 결함을 감지하는지 먼저 학습할 수 있다.

권장 파일:

```text
tests/evals/test_week4_session3_rag_generator.py
tests/evals/week4_session3_rag_generator_solution.py
```

학생용 파일은 정상으로 검토한 질문, 기대 답변과 검색 문서 세 개를 고정하고
``actual_output``만 바꾸는 격리 실험이다. TODO 1~4를 순서대로 완성하면서
관련성, 검색 근거 충실성, 제품 완전성이 서로 다른 질문임을 코드로 확인한다.

| TODO | 구현 대상 | 왜 하는가 | 완료 후 관찰할 것 |
| --- | --- | --- | --- |
| 1 | 네 generator 출력 연결 | 결함이 통제된 답변을 준비한다. | fixture별 답변이 준비된다. |
| 2 | `LLMTestCase` 생성 | reference와 runtime field를 구분한다. | 답변만 다른 사례가 만들어진다. |
| 3 | generator metric factory | 세 품질 축을 metric에 연결한다. | 관련성·충실성·완전성 metric을 생성한다. |
| 4 | 정상/결함 비교 쌍 | judge 실행 전 비교 가설을 정한다. | metric별 대표 비교가 준비된다. |

먼저 외부 API 없이 구문 오류를 확인한다.

```bash
.venv/bin/python -m py_compile \
  tests/evals/test_week4_session3_rag_generator.py
```

TODO를 완성한 뒤 정상 답변과 대표 결함 답변을 metric별로 비교한다.

```bash
DEEPEVAL_WEEK4_SESSION3_RUN_JUDGE=1 \
  .venv/bin/deepeval test run \
  tests/evals/test_week4_session3_rag_generator.py -v

# 직접 완성하고 실행한 뒤 참고 답안을 비교
.venv/bin/python -m \
  tests.evals.week4_session3_rag_generator_solution --run
```

judge 명령은 세 metric을 두 fixture씩 총 6회 실행하므로 ``OPENAI_API_KEY``와
비용이 필요하다. 0.7은 5주차 calibration 전의 임시 threshold다. 정확한 숫자에
맞추기보다 ``good > defective`` 방향과 reason이 원문의 결함을 언급하는지 본다.



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

실습의 네 fixture는 다음처럼 읽는다.

| fixture | 답변의 핵심 | 먼저 관찰할 신호 | 첫 조사 대상 |
| --- | --- | --- | --- |
| `good` | 30일, 주문 정보, 고객센터를 모두 안내 | 모두 건강한 기준선 | 없음 |
| `off_topic` | 환불 대신 배송 기간을 설명 | Answer Relevancy | prompt와 output의 주제 선택 |
| `hallucinated_window` | 30일 근거를 90일로 왜곡 | Faithfulness | grounding |
| `incomplete` | 30일은 맞지만 주문 정보와 고객센터 누락 | custom 완전성 | 답변 구성 로직 |

한 결함이 다른 metric에도 영향을 줄 수 있다. 예를 들어 배송 답변은 질문과
관련이 없을 뿐 아니라 clean 환불 근거에도 없는 내용이다. primary signal은
“이 metric만 실패해야 한다”는 뜻이 아니라, fixture를 만든 첫 학습 목적이다.

### metric의 책임


| metric                  | 평가 질문                   | 낮을 때 먼저 볼 대상            |
| ----------------------- | ----------------------- | ----------------------- |
| `AnswerRelevancyMetric` | 질문에 직접 답하는가?            | generator prompt/output |
| `FaithfulnessMetric`    | 답변의 주장이 검색 근거로 뒷받침되는가?  | generator grounding     |
| custom 완전성 `GEval`      | 사용자가 다음 행동을 할 정보가 충분한가? | 답변 구성 로직                |


세 metric은 같은 답변을 다른 질문으로 읽는다.

- 환불 질문에 배송 설명을 하면 Answer Relevancy가 낮을 수 있다.
- 검색 근거는 30일인데 답변이 90일이면 Faithfulness가 낮을 수 있다.
- 30일은 맞지만 주문 번호와 고객센터가 빠지면 완전성 GEval이 낮을 수 있다.

Faithfulness는 사실 정확도 metric이 아니다. 잘못 검색된 “90일 정책”을
generator가 그대로 사용하면 Faithfulness는 높을 수 있다. 반대로 격리 실험에서
`retrieval_context`가 정상임을 확인하고 고정했을 때 낮은 Faithfulness가
generator grounding을 강하게 의심하게 한다.

### required field로 metric의 시야 확인하기

| metric | 비교하는 field | 의도적으로 보지 않는 것 |
| --- | --- | --- |
| `AnswerRelevancyMetric` | `input`, `actual_output` | 검색 근거와 기대 답변 |
| `FaithfulnessMetric` | `input`, `actual_output`, `retrieval_context` | reviewed `expected_output` |
| custom 완전성 `GEval` | `actual_output`, `expected_output` | retrieval의 검색 품질 |

따라서 높은 Faithfulness만으로 정책이 실제로 옳다고 말할 수 없다. 이 metric은
runtime 검색 문서와 답변의 정합성을 본다. 검색 문서가 정상이라는 사실은 세션 2의
retriever 평가나 reviewer 검토로 별도로 확보해야 한다.

### 결과를 기록하는 법

각 비교에서 다음 네 가지를 한 묶음으로 기록한다.

1. 실행 전에 예측한 primary signal
2. 정상/결함 fixture의 score와 reason
3. 답변과 retrieval 원문에서 직접 확인한 결함
4. 첫 조사 대상과 metric만으로 확정할 수 없는 것

예: “clean retrieval을 고정한 상태에서 90일 답변의 Faithfulness가 내려갔고
reason도 30일 근거와의 충돌을 언급했다. generator grounding을 먼저 조사한다.
다만 이 결과 하나만으로 production retriever 전체가 정상이라고 확정하지 않는다.”

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


| retrieval       | generation    | 예상 진단                          |
| --------------- | ------------- | ------------------------------ |
| 좋음              | 좋음            | 전체 통과                          |
| 좋음              | 근거 없는 주장      | generator/faithfulness 실패      |
| 핵심 근거 누락        | 불완전하거나 잘못된 답변 | retriever와 end-to-end 모두 실패 가능 |
| 올바른 근거 + 과도한 잡음 | 좋은 답변         | contextual metric 실패 가능        |


추가로 다음 교차 사례를 포함한다.


| 교차 사례                              | 관찰할 점                                                   |
| ---------------------------------- | ------------------------------------------------------- |
| 잘못된 정책 문서 검색 + 그 문서대로 답변           | Faithfulness가 높아도 실제 답변은 틀릴 수 있음                        |
| 좋은 검색 + 근거에는 충실하지만 절차 누락           | Faithfulness 통과, 완전성 실패 가능                              |
| 핵심 근거 누락 + 모델 사전지식으로 정답            | end-to-end 통과 가능, recall과 faithfulness는 실패 가능           |
| 배송 안내가 섞인 noisy retrieval + 배송만 요약 | Faithfulness는 높아도 Answer Relevancy가 낮고 retriever 잡음도 의심 |
| 오래되거나 잘못된 reference                | 앱이 아니라 `data` 실패로 분류                                    |




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
