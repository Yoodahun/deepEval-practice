# 2주차 세션 4 — reference 운영 원칙과 실패 진단 기록

이 문서는 referenceless score를 절대적인 품질 판정으로 사용하지 않고,
중요한 production 실패를 사람이 검토한 regression Golden으로 환류하기 위한
학습 기록이다. 학생용 실습의 TODO를 먼저 완성한 뒤 아래 표를 채운다.

## 1. Field 역할


| field               | 역할                    | 판단 근거                        |
| ------------------- | --------------------- | ---------------------------- |
| `input`             | `request`             | 정답이 아니라 평가 대상 요청이다.          |
| `actual_output`     | `runtime_observation` | llm 실행 후 생성하는 답이기 때문         |
| `expected_output`   | `reviewed_reference`  | 기대결과는 사람이 미리 생성해야한다.         |
| `context`           | `reviewed_reference`  | 정확한 근거는 사람이 미리 생성해야한다.       |
| `retrieval_context` | `runtime_observation` | llm이 실행하면서 참조하는 문서.          |
| `expected_tools`    | `reviewed_reference`  | 이번 세션에서는 Agent 품질을 평가하지 않는다. |
| `tools_called`      | `runtime_observation` | 이번 세션에서는 Agent 품질을 평가하지 않는다. |


사용할 역할: `request`, `reviewed_reference`, `runtime_observation`

## 2. Reference 운영 원칙

레퍼런스란, 실제 출력이 좋은지 판단하기 위해 사람이 미리 검토하고 승인한 기준 정보. 채점 정보.

> 평가 점수를 언제 믿을 수 있고, 데이터를 어떻게 운영해야하는가?
>
> Metric 사용법만 알면 다음과 같은 실수를 하기 쉽다.
>
> - Production 답변에 레퍼런스가 없는데도 점수를 정답처럼 믿는다.
> - 잘못 생성된 실제 결과를 기대 결과 값으로 복사한다.
> - referenceless metric이 낮다는 이유만으로 제품 결함을 자동 확정한다.
> - 발견한 production 실패를 일회성 모니터링으로 끝내고 회귀 테스트에 남기지 않는다.


| 상황                                        | 선택한 전략                                  | 이유                                                                                          |
| ----------------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------- |
| 사람이 검토한 reference가 있는 개발 회귀 테스트           | ```python reference_based ```           | 실제 출력과 레퍼런스를 직접 비교. 믿을만한 기대결과가 있으므로 실제 출력과 비교하면서 요구사항이 깨지는 것을 확인할 수 있다.                     |
| reference가 없는 production 표본               | ```python referenceless_then_review ``` | 아직 검토된 정답이 없기 때문에, 관련성/충실성과 같은 referenceless metric으로 실패 후보만 찾고, 중요 사례는 사람이 원문과 근거를 검토해야한다. |
| 사람이 expected output을 승인한 중요 production 실패 | ```python promote_to_regression ```     | 올바른 기대 결과가 사람 검토로 확정되었으므로 Golden에 추가해 같은 문제가 발생하는지 회귀 테스트를 해볼 수 있다.                         |


우리 팀의 원칙:

- 개발·회귀 테스트에서는: 사람이 검토한 레퍼런스를 우선 사용한다.
- reference 없는 production 표본에서는: Referenceless metric을 실패 후보 탐지에만 사용하고 자동으로 품질 실패를 확정지으면 안된다.
- production 실패를 regression에 추가하는 승인 조건은: 사람이 원문과 근거를 확인하고 올바른 기대결과를 승인한 경우
- referenceless score만으로 자동 확정하지 않을 것은: 제품 결함 여부, 정답 내용, 담당 컴포넌트의 골든의 승격여부



여기서 알아야할 점으로는 아래와 같다.

1. 레퍼런스 유무에 따라 평가 목적이 달라진다.
  1. 레퍼런스가 있으면 : 실제 출력이 검토된 기대 결과를 만족하는지 검사
  2. 레퍼런스가 없으면 : 이상하거나 위험해보이는 실패 후보를 탐지

즉, Referenceless metric은 정답 판정기가 아닌 검토 후보 탐지기에 가깝다.

1. 점수의 의미를 과대해석하지 않는다.

예를 들어 프로덕션 답변의 Faithfulness가 낮다면 다음 정도만 말할 수 있다.

> "답변이 검색결과와 일치하지 않을 가능성이 있으니 검토가 필요하다."

1. Production 실패를 재현 가능한 테스트로 바꾼다.
2. Reference 의 신뢰도를 관리한다.



## 3. Metric별 실패 진단표

아래 명령이 출력한 Markdown 행을 옮기고, 각 blind spot을 자신의 말로
설명한다.

```bash
.venv/bin/python \
  tests/evals/week2_session4_reference_diagnosis_exercise.py --show-diagnosis
```


| metric                    | required fields                         | reference       | suspected component | blind spot                            |
| ------------------------- | --------------------------------------- | --------------- | ------------------- | ------------------------------------- |
| Answer Relevancy          | actual_output, input                    | referenceless   | generator           | 답변의 주장이 검색 근거에 충실한지는 알 수 없다.          |
| Faithfulness              | actual_output, input, retrieval_context | referenceless   | generator_grounding | 검색된 근거가 질문에 필요하고 충분한지는 알 수 없다.        |
| Contextual Relevancy      | input, retrieval_context                | referenceless   | retriever           | 필요한 근거의 누락이나 최종 답변의 품질은 알 수 없다.       |
| Refund Completeness GEval | actual_output, expected_output          | reference_based | answer_composition  | 답변 불완전성의 원인이 retriever인지 직접 확정할 수 없다. |


- Answer Relevancy
  - 사용자가 환불 방법을 물어봤는데 배송 기간을 답하면 점수가 낮아저야한다.
    - 질문과 답변을 비교한다.
    - 사람이 검토한 기대결과가 없어도 평가가 가능하다.
    - generator : 검색 결과를 바탕으로 사용자에게 최종 답변을 만드는 LLM 부분
- Faithfulness
  - 검색 문서에는 "30일 이내" 라고 기재되어있는데 답변이 "90일 이내" 라고 말하면 점수가 낮아져야한다.
    - 질문, 실제 답변, 검색 결과를 비교한다.
      - 최종 답변이 가져온 검색 문서에서 근거하는가?? 를 확인하는 것.
    - generator_grounding : 제네레이터가 검색된 근거를 정확하게 사용하는지?
- Contextual Relevancy
  - 환불 질문에 배송, 회원 등급, 선물 포장 문서가 검색되면 점수가 낮아져야한다.
    - 질문과 검색결과를 비교한다.
    - 런타임 검색 결과를 평가한다.
    - retriever : 사용자 질문과 관련된 문서를 검색하는 부분
- Refund completeness
  - 실습 자료에서의 커스텀 메트릭.
  - 환불 기간, 주문 번호, 고객센터 요청 방법의 포함 여부를 검토한다.
    - 실제 답변과 기대 답변
    - 기대 답변이라는 명확한 레퍼런스 사용.
    - 답변의 필수 정보를 구성하는 answer_composition
    - answer_composition : 제네레이터가 최종 답변에 필요한 정보를 빠짐없이 구성하는 방식.





## 4. Production 실패 환류 기록

```bash
.venv/bin/python \
  tests/evals/week2_session4_reference_diagnosis_exercise.py \
  --simulate-feedback-loop
```


| 항목                     | 기록                                                                |
| ---------------------- | ----------------------------------------------------------------- |
| `source_sample_id`     | `prod_refund_001`                                                 |
| 처음 관찰한 결함              | retrieval_context에는 30일 이내 환불이 가능하다고 했으나, 실제 출력에는 90일 이내라고 하고 있다. |
| 낮은 score가 의심하게 한 컴포넌트  | ground                                                            |
| metric 하나로 확정할 수 없었던 것 | 검색된 30일 정책 자체가 실제로 올바른 정책인지까지는 알 수가 없다.                           |
| 사람이 검토한 원문과 근거         | 실제 답변의 90일 안내와 검색 근거의 30일 정책을 비교 판단한다.                            |
| 승인된 `expected_output`  | 구매 후 30일 이내 주문번호를 준비해 고객 센터에 요청하면 전액 환불을 받을 수 있다.                 |
| regression에 추가하기로 한 이유 | 잘못된 환불 기간은 사용자에게 직접 피해를 줄 수 있다.                                   |




## 완료 확인

- [x] 정적 reference와 runtime observation을 구분했다.
- [x] 세 상황에 맞는 reference 전략을 설명할 수 있다.
- [x] 네 metric의 낮은 score를 첫 수정 대상과 연결했다.
- [x] 각 metric이 놓칠 수 있는 결함을 하나씩 기록했다.
- [x] 미검토 `actual_output`을 정답으로 승격하지 않았다.
- [x] 중요 production 실패의 사람 검토 및 Golden 환류 조건을 정했다.