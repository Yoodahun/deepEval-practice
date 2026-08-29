# 2주차 — 표준 metric과 custom `GEval`

> - 상태: 세션 1~3 완료, 세션 4 예정
> - 남은 권장 분량: 1회
> - 핵심 질문: 이 score가 낮을 때 실제로 무엇을 고칠 것인가?

2주차는 metric 이름을 많이 암기하는 주차가 아니다. 사용자 위험, 필요한 test-case field, 낮은 score가 가리키는 수정 대상을 연결한다. 하나의 metric에 독립적인 요구사항을 몰아넣지 않고 표준 metric과 제품 고유 custom metric의 책임을 나눈다.

## 주차 학습 지도


| 세션                  | 상태  | 난이도 | 핵심 산출물             |
| ------------------- | --- | --- | ------------------ |
| 1. 표준 metric 선택     | 완료  | 2/5 | 결함-metric-수정 대상 매핑 |
| 2. 단일 품질 축 `GEval`  | 완료  | 3/5 | custom metric 1개   |
| 3. 경계 사례 검증         | 완료  | 3/5 | pass/fail/경계 사례 6개 |
| 4. reference와 실패 진단 | 예정  | 2/5 | reference 원칙과 진단표  |




## 세션 1: 표준 metric 선택 — 완료

실습 파일:

- [학생용 실습](../tests/evals/week2_session1_metric_selection_exercise.py)
- [참고 답안](../tests/evals/week2_session1_metric_selection_solution.py)

```bash
.venv/bin/python tests/evals/week2_session1_metric_selection_exercise.py --check
.venv/bin/python tests/evals/week2_session1_metric_selection_exercise.py --run
```

`--check`는 API 없이 metric 선택, 생성자, required field 구성을 검사한다. `--run`은 실제 judge를 호출해 score와 reason을 관찰하므로 두 단계를 분리한다.

### 결함별 선택 기준


| 관찰한 결함         | metric                      | DeepEval 4.1.4 required field                 | 먼저 수정할 대상               |
| -------------- | --------------------------- | --------------------------------------------- | ----------------------- |
| 질문과 무관한 답변     | `AnswerRelevancyMetric`     | `input`, `actual_output`                      | generator prompt/output |
| 검색 근거와 모순되는 주장 | `FaithfulnessMetric`        | `input`, `actual_output`, `retrieval_context` | generator grounding     |
| 검색 결과에 잡음이 많음  | `ContextualRelevancyMetric` | `input`, `retrieval_context`                  | retriever 조건/top-k      |


metric required field는 버전에 따라 바뀔 수 있으므로 설치 버전과 공식 문서를 기준으로 다시 확인한다. 학생용 실습의 구조 검사가 공식 required field보다 교육 목적상 더 많은 field를 요구할 수 있다는 점도 구분한다.

## 세션 2: 단일 품질 축으로 `GEval` 만들기 — 완료

> - 예상 시간: 60~90분
> - 선행 조건: 세션 1 완료
> - 핵심 산출물: TODO를 완성한 custom metric과 네 개의 pass/fail 관찰 결과

학생용 실습:

- [GEval rubric 실습](../tests/evals/week2_session2_geval_rubric_exercise.py)

처음에는 custom metric을 별도 모듈로 추출하려고 하지 말고 학생용 파일의 TODO 네 개를 순서대로 완성한다.

```bash
# 1. 현재 TODO와 안내를 읽는다.
sed -n '1,260p' tests/evals/week2_session2_geval_rubric_exercise.py

# 2. API 호출 없이 TODO 구현을 검사한다.
.venv/bin/python tests/evals/week2_session2_geval_rubric_exercise.py --check

# 3. 구조 검사를 통과한 뒤에만 네 사례를 judge로 평가한다.
.venv/bin/python tests/evals/week2_session2_geval_rubric_exercise.py --run
```

이 탐색 실습에서는 `model` 인자를 생략해 설치된 DeepEval의 기본 judge를 사용한다. `--check`가 실제 기본 model 이름을 출력하므로 학습 기록에 남긴다. 5주차 calibration과 6주차 CI에서는 실행 조건을 재현할 수 있도록 judge model을 명시적으로 고정한다.

실습에서 score와 reason을 확인한 후 다른 세션에서도 재사용할 단계가 되면 `make_refund_completeness_metric()`을 다음 파일로 옮긴다.

```text
evals/metrics/refund_completeness.py
```



### 왜 배우는가

표준 metric은 일반적인 관련성이나 근거 충실성을 평가하지만, 제품이 요구하는 “좋은 환불 안내” 전체를 그대로 알지는 못한다. 이 세션에서는 환불 답변이 사용자의 다음 행동에 필요한 정보를 충분히 주는지 평가하는 custom metric을 만든다.

품질 축은 **환불 안내 완전성** 하나로 제한한다.

- 포함: 환불 가능 기간, 필요한 정보, 요청 방법이 충분히 안내되었는가?
- 제외: JSON schema, 문장 길이, 존댓말, retrieval 품질



### 1. metric 계약 작성

코드를 작성하기 전에 다음을 문서화한다.


| 계약 항목          | 예시                                          |
| -------------- | ------------------------------------------- |
| 보호할 사용자 위험     | 중요한 절차가 빠져 사용자가 환불을 진행하지 못함                 |
| 평가 품질 축        | 환불 안내 완전성                                   |
| required field | `input`, `actual_output`, `expected_output` |
| 낮을 때 수정할 대상    | generator prompt 또는 답변 구성 로직                |
| 평가하지 않는 것      | 형식, 어조, retrieval 성능                        |


- [x] deterministic requirement 한 개를 `GEval`에서 제외하고 pytest assertion으로 옮긴다.
- [x] `criteria`가 한 품질 축만 다루게 쓴다.
- [x] criteria가 실제로 읽는 field만 `evaluation_params`에 넣는다.
- [x] 생성 함수 이름을 `make_refund_completeness_metric()`으로 작성한다.
- [x] 기본 judge model을 확인하고 임시 threshold를 명시한다.



### 2. 명백한 사례로 방향 확인

처음에는 네 사례만 사용한다.

- [x] 기간·필요 정보·요청 방법을 모두 담은 pass 2개
- [x] 중요한 절차가 빠졌거나 정책과 모순된 fail 2개
- [x] import와 field 구성은 API 없이 검사
- [x] 네 사례만 judge에 실행하고 score와 reason 기록

reason이 예상과 다르면 threshold부터 바꾸지 않는다. 먼저 criteria, reference, 사례 자체의 모호함을 확인한다.

### 완료 조건

- [x] custom metric이 여러 테스트에서 import 가능하다.
- [x] metric이 평가하는 것과 평가하지 않는 것을 설명할 수 있다.
- [x] 명백한 pass/fail 네 사례가 기대 방향으로 구분된다.



## 세션 3: 경계 사례로 rubric 검증

> - 예상 시간: 60~90분
> - 선행 조건: 세션 2 완료
> - 핵심 산출물: `evals/calibration/week2_geval_observations.md`



### 왜 배우는가

명백한 pass/fail만으로는 실제 release gate의 경계에서 metric이 어떻게 행동하는지 알 수 없다. 이 세션은 threshold를 확정하는 세션이 아니라 rubric 해석을 확인하는 작은 실험이다.

권장 보조 파일:

- [학생용 경계 사례 실습](../tests/evals/week2_session3_geval_boundary_exercise.py)
- [참고 답안](../tests/evals/week2_session3_geval_boundary_solution.py)
- [관찰 기록 템플릿](../evals/calibration/week2_geval_observations.md)

CLI 전용 실습이므로 pytest 자동 수집이 필요하지 않다면 `test_` 접두사를 사용하지 않는다.

학생용 파일에는 사람 라벨 공백 채우기, `GEval` 생성 함수 구현,
score 판정 함수 구현, 관찰 후 rubric 수정의 네 TODO가 있다. 다음 순서로
실행하면 LLM judge 호출과 API 없는 구조 검사를 분리할 수 있다.

```bash
# 1. TODO 1~3을 구현하고 API 없이 검사한다.
.venv/bin/python tests/evals/week2_session3_geval_boundary_exercise.py --check

# 2. metric.measure()로 경계 사례 하나를 디버깅한다. 이때부터 API를 호출한다.
.venv/bin/python tests/evals/week2_session3_geval_boundary_exercise.py \
  --debug-one boundary_missing_order_id

# 3. evaluate()로 baseline 여섯 사례를 비교한다.
.venv/bin/python tests/evals/week2_session3_geval_boundary_exercise.py --run-baseline

# 4. 관찰 결과를 바탕으로 TODO 4의 rubric만 한 번 수정한다.
.venv/bin/python tests/evals/week2_session3_geval_boundary_exercise.py --check-revision
.venv/bin/python tests/evals/week2_session3_geval_boundary_exercise.py --run-revised
```

`--run-baseline`과 `--run-revised`가 출력하는 Markdown 행을 관찰 기록
템플릿에 옮긴다. 참고 답안은 baseline과 수정 실행을 모두 끝낸 뒤 확인한다.

### 1. 사람 라벨을 먼저 작성

- [x] 명백한 pass 2개와 fail 2개를 준비한다.
- [x] 주문 번호가 빠진 답변처럼 경계 사례 1개를 만든다.
- [x] 요청 채널이 모호한 답변처럼 다른 경계 사례 1개를 만든다.
- [x] judge 실행 전에 `human_expected`와 한 줄 근거를 기록한다.
- [x] `clear_pass_001`, `boundary_missing_order_id`처럼 안정적인 ID를 붙인다.



### 2. reason 비교

1. `metric.measure()`로 한 사례를 디버깅한다.
2. `evaluate()`로 여섯 사례를 비교한다.
3. reason이 rubric의 같은 항목을 일관되게 보는지 확인한다.
4. 불일치를 rubric, reference, 사람 라벨, judge 변동 중 하나로 분류한다.

- [x] 가장 명확한 문제 하나만 골라 rubric을 한 번 수정한다.
- [x] 같은 사례를 재실행해 변경 전후를 기록한다.
- [x] 애매한 사례는 5주차 calibration 후보로 남긴다.



### 완료 조건

- [x] 여섯 사례에 사람 예상, score, reason이 기록되어 있다.
- [x] rubric 수정 이유와 효과를 설명할 수 있다.
- [x] 현재 threshold가 아직 임시 값임을 명시했다.



## 세션 4: reference 전략과 실패 진단

> - 예상 시간: 60~90분
> - 선행 조건: 세션 1~3 완료
> - 핵심 산출물: reference 운영 원칙과 결함 진단표

권장 실습 파일:

- [학생용 reference/진단 실습](../tests/evals/week2_session4_reference_diagnosis_exercise.py)
- [참고 답안](../tests/evals/week2_session4_reference_diagnosis_solution.py)
- [reference 운영 원칙과 진단 기록 템플릿](../evals/calibration/week2_reference_diagnosis.md)

학생용 파일에는 field 역할 분류, 상황별 reference 전략 선택, metric별
진단 경로 작성, reviewed Golden 승격 함수의 네 TODO가 있다. 이번 세션의
핵심은 새 score를 얻는 것이 아니라 이미 배운 metric의 책임 범위와 운영
경계를 명확히 하는 것이므로 모든 명령은 LLM judge와 외부 API를 호출하지
않는다.

```bash
# 1. TODO 1~4를 구현하고 API 없이 검사한다.
.venv/bin/python \
  tests/evals/week2_session4_reference_diagnosis_exercise.py --check

# 2. 완성한 metric별 진단표를 출력해 기록 템플릿에 옮긴다.
.venv/bin/python \
  tests/evals/week2_session4_reference_diagnosis_exercise.py \
  --show-diagnosis

# 3. reference 없는 production 실패가 사람 검토 후 Golden이 되는 흐름을 확인한다.
.venv/bin/python \
  tests/evals/week2_session4_reference_diagnosis_exercise.py \
  --simulate-feedback-loop
```

참고 답안은 네 TODO와 기록 템플릿을 먼저 완성한 뒤 비교한다. production
표본의 `actual_output`을 그대로 정답으로 복사하지 않고, 사람이 승인한
`reviewed_expected_output`만 다음 regression dataset의 정적 reference로
승격하는 경계를 확인한다.



### reference-based와 referenceless

- reference-based: 사람이 검토한 `expected_output`, `context`, `expected_tools` 등을 기준으로 평가한다.
- referenceless: `input`, `actual_output` 같은 관측값만으로 평가한다.

운영 원칙:

- [ ] 개발·회귀 테스트는 신뢰 가능한 reference를 우선한다.
- [ ] production sample에는 처음부터 reference가 없을 수 있음을 인정한다.
- [ ] 중요한 production 실패는 사람이 검토해 다음 regression dataset으로 환류한다.
- [ ] referenceless score를 제품 품질의 절대 진실로 사용하지 않는다.



### 종합 score 대신 진단표


| 결함              | 직접적인 metric          | 낮을 때 먼저 볼 대상        | 놓칠 수 있는 문제              |
| --------------- | -------------------- | ------------------- | ----------------------- |
| 질문에서 이탈         | Answer Relevancy     | generator           | 근거가 맞는지는 모름             |
| 근거 없는 주장        | Faithfulness         | generator grounding | 질문에 유용한지는 별개            |
| noisy retrieval | Contextual Relevancy | retriever           | 필요한 근거 누락 여부는 별개        |
| 절차 불완전          | custom `GEval`       | 답변 구성               | retriever 원인은 직접 확정 못 함 |


- [ ] 각 metric이 놓칠 수 있는 결함을 한 개씩 적는다.
- [ ] 실패 결과에 `suspected_component`를 기록할 방식을 정한다.
- [ ] Agent trace 결함은 아직 포함하지 않고 선택 심화로 미룬다.

### 완료 조건

- [ ] field를 `request`, `reviewed_reference`, `runtime_observation`으로 구분할 수 있다.
- [ ] 개발 회귀와 reference 없는 production 표본의 평가 전략을 구분했다.
- [ ] 네 metric의 낮은 score를 첫 수정 대상과 blind spot에 연결했다.
- [ ] 사람이 승인한 production 실패만 reviewed Golden으로 환류했다.



## 2주차 완료 조건

- [ ] 표준 metric과 custom metric의 책임 범위가 문서화되어 있다.
- [ ] custom metric이 pass/fail/경계 사례에서 의도한 신호를 낸다.
- [ ] reference가 없는 사례를 reviewed Golden으로 환류하는 원칙이 있다.
- [ ] 낮은 score를 구체적인 수정 대상으로 연결할 수 있다.



## 막히기 쉬운 지점

- criteria에 완전성, 어조, 정확성, 간결성을 한꺼번에 넣는다.
- judge reason이 그럴듯하다는 이유로 사람 라벨보다 우선한다.
- 한 사례에 여러 주요 결함을 동시에 넣어 어떤 metric이 반응했는지 모른다.
- threshold를 수정해 현재 여섯 사례에 과적합한다.

참고: [Metrics Introduction](https://deepeval.com/docs/metrics-introduction)

이전: [1주차 — 평가의 테스트 모델](week1_evaluation_foundations.md) · 다음: [3주차 — dataset과 regression](week3_dataset_and_regression.md)
