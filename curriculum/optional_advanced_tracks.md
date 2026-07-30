# 선택 심화 — tracing, Agent, multi-turn, SDET 응용

> - 상태: 선택
> - 선행 조건: 6주차 필수 캡스톤 완료 권장
> - 완료 규칙: 이 문서의 항목은 필수 커리큘럼 완료 조건에 포함되지 않는다.

선택 심화를 모두 진행하지 않는다. 실제 관심 시스템과 업무 적용 가능성이 가장 높은 트랙 하나만 고른다. RAG 필수 과정에서 얻은 test case, dataset, metric, calibration 경험을 재사용한다.

## 트랙 선택 가이드

| 관심 시스템 | 추천 트랙 | 난이도 | 추가로 필요한 것 |
| --- | --- | ---: | --- |
| 내부 단계가 많은 RAG/Agent | A. tracing | 4/5 | instrumentation과 span 이해 |
| 도구를 선택·호출하는 Agent | B. Agent 평가 | 5/5 | 최소 두 도구와 agent loop |
| 상담형 chatbot | C. multi-turn | 4/5 | 대화 상태와 scenario |
| 모바일 QA 업무 자동화 | D. SDET 응용 | 3~4/5 | 실제 업무 산출물과 reviewer 기준 |

## A. tracing과 span-level 평가

> - 권장 분량: 2회

### 학습 목표

- trace는 앱 전체 실행, span은 retriever·LLM·tool 같은 내부 실행 단위임을 설명한다.
- trace-level metric과 span-level metric을 동시에 사용할 때의 역할을 구분한다.
- tracing이 실제로 더 나은 진단을 주는 경우에만 instrumentation 비용을 감수한다.

### 1회차: 최소 instrumentation

- [ ] `@observe`, `update_current_trace`, `update_current_span`의 역할을 읽는다.
- [ ] `retrieve_policy()`와 `generate_answer()`를 각각 span으로 관찰한다.
- [ ] 전체 앱 실행이 하나의 trace가 되는지 확인한다.
- [ ] 앱 동작과 반환값이 instrumentation 전후에 바뀌지 않는지 deterministic test로 확인한다.

### 2회차: span metric

- [ ] trace 전체에는 end-to-end metric을 연결한다.
- [ ] retriever span에는 contextual metric을 연결한다.
- [ ] generator span에는 Answer Relevancy 또는 Faithfulness를 연결한다.
- [ ] tracing 없는 4주차 진단과 비교해 추가로 얻은 정보가 무엇인지 기록한다.

### 완료 신호

같은 실패에 대해 “최종 답변이 나쁘다”에서 끝나지 않고 어떤 span의 어떤 field가 잘못되었는지 trace에서 찾을 수 있다.

참고: [LLM Tracing](https://deepeval.com/docs/evaluation-llm-tracing), [Component-Level Evaluation](https://deepeval.com/docs/evaluation-component-level-llm-evals)

## B. 도구 호출 Agent 평가

> - 권장 분량: 3회

### 최소 Agent 범위

도구 두 개만 사용한다.

- `lookup_order_status(order_id)`
- `handoff_to_human(reason)`

도구가 많거나 planner가 복잡한 agent를 먼저 만들면 DeepEval보다 agent framework 학습이 더 커진다.

### 1회차: tool call 표현

- [ ] 실제 `tools_called`를 test case에 기록한다.
- [ ] `expected_tools`에 기대 도구와 중요한 argument를 기록한다.
- [ ] 올바른 도구, 잘못된 도구, 불필요한 추가 도구 사례를 만든다.

### 2회차: tool correctness

- [ ] `ToolCorrectnessMetric` required field와 비교 방식 옵션을 확인한다.
- [ ] 도구 이름만 맞고 argument가 틀린 사례를 평가한다.
- [ ] 답변은 좋아도 잘못된 도구를 호출한 사례를 만든다.

### 3회차: task completion

- [ ] agent 전체 실행을 trace한다.
- [ ] `TaskCompletionMetric`으로 사용자 과업 달성을 평가한다.
- [ ] 올바른 도구를 호출했지만 최종 과업에 실패한 사례를 만든다.
- [ ] tool correctness와 task completion이 서로 대체 관계가 아님을 기록한다.

### 완료 신호

좋은 최종 문장, 올바른 도구 호출, 전체 과업 달성을 서로 다른 평가 축으로 설명할 수 있다.

## C. 다중 턴 상담 평가

> - 권장 분량: 3회

### 1회차: 정적 대화부터 시작

- [ ] `ConversationalTestCase`와 `Turn`으로 3턴 이상의 대화를 표현한다.
- [ ] 이전 턴의 구매 날짜를 기억해야 하는 사례를 만든다.
- [ ] 환불 상담 역할에서 이탈하는 사례를 만든다.
- [ ] single-turn metric과 conversational metric을 혼용하지 않는다.

### 2회차: 대화 metric 선택

다음 중 실제 위험에 맞는 1~2개만 고른다.

- role adherence
- knowledge retention
- conversation relevancy
- conversation completeness

- [ ] 낮은 score가 어떤 prompt/memory/component 수정으로 이어지는지 적는다.
- [ ] 같은 대화 scenario에서 한 가지 결함만 바꿔 비교한다.

### 3회차: simulator 검토

정적 대화가 안정된 뒤에만 `ConversationSimulator`를 사용한다.

- [ ] `ConversationalGolden`에 scenario와 expected outcome을 작성한다.
- [ ] 고정 scenario에서 현재 chatbot을 실행한다.
- [ ] simulator의 사용자 행동 변동과 chatbot 변동을 구분한다.
- [ ] production 대화와 synthetic 대화를 같은 출처처럼 취급하지 않는다.

### 완료 신호

특정 turn 하나의 품질과 대화 전체의 목표 달성 여부를 구분할 수 있다.

참고: [Multi-Turn Conversation Tutorial](https://deepeval.com/tutorials/medical-chatbot/evaluation)

## D. SDET 업무 자산에 적용

다음 중 하나만 고른다.

### XCTest/Appium 실패 로그 요약

- deterministic: 테스트 이름, error code, stack trace의 필수 정보 누락 여부
- semantic: 원인 요약의 정확성, 추측 억제, 다음 조사 단계의 유용성

### 자연어에서 JSON 테스트 케이스 생성

- deterministic: JSON schema, 필수 key, enum, step 개수
- semantic: 전제조건, 실행 단계, 기대 결과가 사용자 요구를 반영하는가?

### 버그 리포트 초안

- deterministic: 제목, 환경, 재현 절차, 실제/기대 결과 field
- semantic: 재현 가능성, 관찰과 추측의 분리, 과도한 단정 억제

UI 자동화와 역할을 분리한다. 화면 전환, 버튼 노출, accessibility identifier 같은 결정적 동작은 Appium/XCTest가 담당하고, DeepEval은 LLM이 생성한 텍스트와 행동의 의미 품질을 평가한다.

## 선택 심화 공통 원칙

- 새 트랙에서도 평가 계약과 사용자 위험을 먼저 작성한다.
- 처음에는 5개 이하 사례와 1~2개 metric으로 시작한다.
- API 없는 assertion을 먼저 작성한다.
- 선택 트랙 때문에 필수 RAG suite의 회귀 안정성을 해치지 않는다.
- 실험이 유용하지 않으면 “tracing/Agent가 불필요했다”는 결론도 유효하다.

이전: [6주차 — CI와 캡스톤](week6_ci_and_capstone.md) · 인덱스: [주차별 커리큘럼 안내](README.md)
