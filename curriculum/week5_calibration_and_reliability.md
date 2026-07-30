# 5주차 — 사람 라벨, threshold, 반복성, 비용

> - 상태: 예정
> - 권장 분량: 5회
> - 핵심 질문: metric score를 release decision에 사용할 만큼 어떻게 신뢰할 수 있게 만드는가?

5주차는 API 사용법보다 실험 설계와 데이터 검토가 어렵다. 30개 사례를 한 번에 라벨링하지 않고, 10개 파일럿으로 rubric 문제를 찾은 뒤 30개로 확장한다. threshold는 보기 좋은 숫자가 아니라 false positive와 false negative의 비용으로 선택한다.

## 주차 학습 지도

| 세션 | 난이도 | 핵심 산출물 |
| --- | ---: | --- |
| 1. judge 한계와 계획 | 2/5 | calibration 계약 |
| 2. 10개 파일럿 | 3/5 | 사람 라벨/score 비교 |
| 3. 30개 확장 | 4/5 | calibration dataset |
| 4. threshold 선택 | 4/5 | FP/FN과 결정 기록 |
| 5. 반복성·비용·오류 | 3/5 | flaky/API triage 규칙 |

## 세션 1: LLM-as-a-Judge의 한계와 계획

> - 예상 시간: 약 60분

### 먼저 기록할 한계

- [ ] 평가 대상 모델과 judge 모델이 서로 다른 역할임을 설명한다.
- [ ] judge score도 확률적이며 정답 라벨이 아님을 기록한다.
- [ ] criteria, evaluation step, judge model, DeepEval 버전이 score에 영향을 준다고 기록한다.
- [ ] reason은 원문·reference·rubric과 함께 검토한다.
- [ ] 고위험 gate에는 deterministic assertion, 사람 라벨, judge를 함께 사용한다.

### calibration 계약

`evals/calibration/refund_calibration_plan.md`에 작성한다.

```markdown
# Refund completeness calibration plan

- 보정할 metric:
- 사람의 pass 기준:
- 사람의 fail 기준:
- false positive의 비용:
- false negative의 비용:
- 고정할 judge/model 설정:
- metric 버전:
- 데이터에서 제외할 오류:
```

환불 정책을 잘못 안내하는 false negative가 좋은 답변을 차단하는 false positive보다 비싼지 사전에 정한다. score를 본 뒤 비용 기준을 바꾸면 threshold에 맞춰 논리를 만드는 문제가 생긴다.

### 완료 조건

- [ ] 오류 비용을 사전에 결정했다.
- [ ] judge score 전에 사람 라벨을 작성할 절차가 있다.

## 세션 2: 10개 파일럿 calibration

> - 예상 시간: 60~90분
> - 선행 조건: calibration 계약

권장 파일:

```text
evals/calibration/refund_geval_pilot.jsonl
evals/calibration/refund_geval_pilot.md
```

### 데이터 구성

- [ ] 명백한 pass 3개
- [ ] 명백한 fail 3개
- [ ] 경계 사례 4개

각 행에 `case_id`, `human_label`, `label_reason`, `category`를 기록한다. metric score와 judge reason은 별도 실행 결과에 기록해 사람 판단이 score에 영향을 받지 않게 한다.

### 실행 순서

1. 사람 라벨과 근거를 확정한다.
2. judge/model/metric 설정을 고정한다.
3. 10개를 한 번 실행한다.
4. 사람과 judge가 불일치한 사례부터 검토한다.
5. 불일치를 `rubric`, `reference`, `human_label`, `judge_variance`로 분류한다.

이 단계에서는 threshold를 확정하지 않는다. 명백한 사례에서 불일치가 많으면 rubric이나 reference를 먼저 고친다.

### 완료 조건

- [ ] 10개에 사람 라벨, 사람 근거, score, reason이 있다.
- [ ] 불일치 원인이 분류되어 있다.

## 세션 3: 30개 calibration dataset

> - 예상 시간: 60~120분 또는 두 번으로 분할
> - 선행 조건: 파일럿의 rubric/reference 문제 해결

권장 파일:

```text
evals/calibration/refund_completeness_labels.jsonl
```

### 확장 원칙

- [ ] 파일럿을 포함해 총 30개를 준비한다.
- [ ] `10 + 10 + 10` 묶음으로 나눠 리뷰한다.
- [ ] pass/fail 숫자만 맞추지 않고 경계 사례를 충분히 포함한다.
- [ ] 의미가 같은 문장을 반복해 표본을 부풀리지 않는다.
- [ ] 라벨 기준이 바뀌면 이전 묶음도 다시 검토한다.
- [ ] production sample은 익명화한다.

### 권장 category

| category | 목적 |
| --- | --- |
| clear_pass | rubric의 상단 범위 확인 |
| clear_fail | 명백한 결함 감지 확인 |
| boundary_missing_detail | 중요 정보 일부 누락 |
| boundary_vague_action | 다음 행동이 모호함 |
| policy_contradiction | 반드시 실패해야 하는 위험 |

### 완료 조건

- [ ] 30개 모두 score보다 먼저 사람 라벨이 확정되었다.
- [ ] 명백한 사례와 경계 사례가 구분되어 있다.
- [ ] 중복과 개인정보를 검토했다.

## 세션 4: FP/FN으로 threshold 선택

> - 예상 시간: 60~90분
> - 선행 조건: 30개 사람 라벨과 metric score

권장 파일:

```text
evals/calibration/analyze_refund_threshold.py
evals/calibration/refund_threshold_decision.md
```

### 용어

- false positive: 사람이 pass한 좋은 답변을 metric이 fail 처리
- false negative: 사람이 fail한 나쁜 답변을 metric이 pass 처리

### 분석 작업

- [ ] 여러 threshold 후보에서 TP, TN, FP, FN을 계산한다.
- [ ] 각 오류를 숫자뿐 아니라 `case_id`로 검토한다.
- [ ] 정책 모순 같은 중요한 false negative가 통과하는지 확인한다.
- [ ] 세션 1에서 정한 오류 비용을 적용한다.
- [ ] 최종 threshold와 선택 근거를 문서화한다.

### threshold와 hard gate

개인정보 노출, 명백한 정책 모순, 금지된 도구 호출처럼 평균 score로 완화하면 안 되는 위험은 별도 deterministic 또는 case-level hard gate로 둔다.

결정 기록에는 다음을 포함한다.

- dataset 버전과 case 수
- metric 이름과 설정
- judge model
- 선택 threshold
- FP/FN 개수와 중요한 오류 사례
- 재보정 조건

### 완료 조건

- [ ] threshold를 오류 비용으로 설명할 수 있다.
- [ ] 중요한 단일 실패는 별도 hard gate로 보호된다.

## 세션 5: 반복성, 비용, API 오류

> - 예상 시간: 60~90분
> - 선행 조건: threshold 후보 확정

권장 테스트:

```text
tests/evals/test_week5_session5_flaky_eval.py
```

### 경계 사례 반복

경계 사례 3~5개만 좁게 반복한다.

```bash
.venv/bin/deepeval test run tests/evals/test_week5_session5_flaky_eval.py -r 3
```

- [ ] score의 최소, 최대, 평균을 기록한다.
- [ ] pass/fail이 뒤집힌 사례를 찾는다.
- [ ] threshold를 낮추기 전에 rubric과 사람 라벨의 모호함을 검토한다.
- [ ] judge model과 metric 설정을 고정한다.

### 비용과 시간

```bash
.venv/bin/deepeval test run tests/evals -c
.venv/bin/deepeval test run tests/evals -n 2
```

- [ ] `case 수 × metric 수 × 반복 수`로 호출량을 추정한다.
- [ ] cache 전후 실행 시간과 호출 수를 비교한다.
- [ ] 병렬 실행은 2개부터 시작해 rate limit을 관찰한다.

### 오류 triage

| 분류 | 예시 | 처리 |
| --- | --- | --- |
| 제품 품질 실패 | score가 threshold 미만 | 제품 회귀 실패 |
| 데이터 실패 | reference 오류, required field 누락 | 평가 무효, 데이터 수정 |
| judge/API 오류 | rate limit, quota, timeout, 구조화 출력 오류 | 평가 미완료, 재실행/인프라 조치 |

- [ ] `--ignore-errors`를 release gate 기본값으로 사용하지 않는다.
- [ ] API 오류를 제품 품질 통과로 집계하지 않는다.

## 5주차 완료 조건

- [ ] 30개 사람 라벨로 threshold를 보정했다.
- [ ] FP/FN과 중요한 오류 사례가 기록되어 있다.
- [ ] 경계 사례의 반복 안정성을 알고 있다.
- [ ] 품질, 데이터, judge/API 오류를 구분한다.
- [ ] 대략적인 호출량, 비용, 시간을 예측한다.

## 막히기 쉬운 지점

- score를 먼저 본 뒤 사람 라벨을 정한다.
- clear pass/fail만 사용해 threshold 근처 동작을 보지 못한다.
- 정확도 하나만 보고 중요한 false negative를 놓친다.
- flaky를 숨기기 위해 threshold만 낮춘다.
- API 오류가 ignored 상태라 release가 잘못 통과한다.

참고: [Flags and Configs](https://deepeval.com/docs/evaluation-flags-and-configs), [Unit Testing in CI/CD](https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd)

이전: [4주차 — RAG 평가](week4_rag_evaluation.md) · 다음: [6주차 — CI와 캡스톤](week6_ci_and_capstone.md)
