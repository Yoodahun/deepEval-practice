# 1주차 — LLM 평가의 테스트 모델

> - 상태: 완료
> - 권장 분량: 4회
> - 핵심 질문: 하나의 LLM interaction을 어떤 데이터와 assertion으로 표현할 것인가?

1주차는 DeepEval API를 많이 외우는 주차가 아니다. 평가 범위를 먼저 정하고, 정적 reference와 runtime observation을 구분하고, 코드 assertion과 LLM judge의 책임을 나누는 것이 핵심이다.

## 주차 학습 지도

| 세션 | 상태 | 학습 결과 |
| --- | --- | --- |
| 1. 평가 대상과 범위 | 완료 | black-box 평가 계약 |
| 2. `LLMTestCase` field | 완료 | reference/runtime field 구분 |
| 3. 실행 방법 | 완료 | `measure`, `evaluate`, `assert_test` 선택 |
| 4. assertion 분리 | 완료 | deterministic/semantic 검사 분리 |

## 세션 1: 평가 대상과 평가 범위

### 왜 먼저 범위를 정하는가

“답변 품질을 평가한다”는 문장만으로는 metric을 고를 수 없다. 누구의 어떤 위험을 막는지, interaction이 어디서 시작해 어디서 끝나는지 정해야 test case field와 metric이 결정된다.

환불 고객지원 시나리오의 예:

```markdown
## 평가 계약서

- 사용자/비즈니스 목표: 사용자가 환불 가능 여부와 다음 행동을 정확히 이해한다.
- interaction 시작: 사용자가 환불 관련 질문을 입력한다.
- interaction 종료: 앱이 정책 근거를 사용해 최종 답변을 반환한다.
- 반드시 만족해야 하는 동작: 기간, 요청 방법, 필요한 정보를 정책과 모순 없이 안내한다.
- 허용 가능한 표현 차이: 존댓말, 문장 순서, 동의어 차이
- 절대 허용할 수 없는 실패: 환불 기간 왜곡, 카드번호 요구, 정책에 없는 보장
- 대표 입력: "지난주에 산 상품을 환불하려면 어떻게 해야 하나요?"
- 사람 reviewer의 합격 기준: 답변만 보고 사용자가 안전하게 다음 단계를 진행할 수 있다.
```

평가 계약은 이후 custom metric, Golden category, hard gate를 정하는 기준이 된다.

## 세션 2: `LLMTestCase` field

| field | 의미 | 데이터 성격 | 주로 누가 생성하는가 |
| --- | --- | --- | --- |
| `input` | 사용자 또는 상위 컴포넌트 입력 | 테스트 입력 | dataset/test |
| `actual_output` | 앱이 실제 생성한 출력 | runtime observation | generator/app |
| `expected_output` | 사람이 검토한 이상적 결과 | static reference | reviewer |
| `context` | 이상적이고 신뢰 가능한 근거 | static ground truth | reviewer/dataset |
| `retrieval_context` | retriever가 실제 반환한 문서 | runtime observation | retriever |
| `tools_called` | agent가 실제 호출한 도구 | runtime observation | agent |
| `expected_tools` | 기대하는 도구 호출 | static reference | reviewer/dataset |

### 가장 중요한 구분

`context`와 `retrieval_context`를 바꿔 넣으면 retriever가 실제로 무엇을 찾았는지와 사람이 무엇을 정답 근거로 정했는지가 뒤섞인다. 이 상태에서는 낮은 score가 데이터 문제인지 retriever 문제인지 판단할 수 없다.

`expected_output`도 문자열 완전 일치 정답이 아니다. 허용되는 의미와 필수 정보를 judge에게 전달하는 reference다.

## 세션 3: `measure()`, `evaluate()`, `assert_test()`

| API | 적합한 상황 | 실패 처리 |
| --- | --- | --- |
| `metric.measure(test_case)` | metric 하나를 디버깅하고 score/reason을 직접 확인 | 호출자가 해석 |
| `evaluate(test_cases=..., metrics=...)` | 여러 사례를 탐색하고 결과를 비교 | 결과를 수집 |
| `assert_test(test_case, metrics)` | pytest 회귀 테스트와 CI gate | threshold 미달 시 assertion 실패 |

권장 흐름:

1. 새 metric은 명백한 사례 하나에 `measure()`로 시작한다.
2. pass/fail/경계 사례 묶음은 `evaluate()`로 비교한다.
3. 기준과 threshold가 안정되면 `assert_test()`로 회귀 gate에 넣는다.

## 세션 4: deterministic assertion과 semantic eval

### 일반 pytest assertion이 먼저인 요구사항

- JSON으로 파싱할 수 있다.
- `answer`, `source` key가 존재한다.
- `confidence`가 숫자이고 0~1 범위다.
- 응답 길이가 제품 제한을 넘지 않는다.

### LLM judge가 필요한 요구사항

- 답변이 질문에 직접 관련되어 있다.
- 필요한 환불 절차가 의미상 빠짐없이 포함되어 있다.
- 답변의 주장이 검색 근거와 모순되지 않는다.
- 불확실한 내용을 과도하게 단정하지 않는다.

결정적 조건을 `GEval`에 넣으면 느리고 비싸며, 동일한 형식 오류가 확률적으로 통과할 수 있다. 반대로 의미상 같은 문장을 문자열 완전 일치로 검사하면 유효한 표현 차이를 실패시킨다.

## 1주차 산출물

- [x] 하나의 interaction을 `LLMTestCase`로 표현할 수 있다.
- [x] ground truth와 runtime observation을 구분한다.
- [x] 탐색용 평가와 CI assertion을 구분한다.
- [x] deterministic 검사와 LLM judge 검사를 분리한다.

## 복습 질문

1. `actual_output`을 Golden에 미리 고정하면 모델 변경 비교가 왜 어려워지는가?
2. 낮은 faithfulness score와 낮은 contextual score는 각각 어느 컴포넌트를 먼저 의심해야 하는가?
3. JSON schema 검사를 `GEval` 하나에 포함시키면 어떤 문제가 생기는가?

참고: [Single-Turn Test Case](https://deepeval.com/docs/evaluation-test-cases), [End-to-End Evaluation](https://deepeval.com/docs/evaluation-end-to-end-llm-evals)

이전: [준비 단계](00_setup.md) · 다음: [2주차 — 표준 metric과 custom GEval](week2_metrics_and_geval.md)
