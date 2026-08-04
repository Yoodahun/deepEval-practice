# 5주차 — 사람 라벨, threshold, 반복성, 비용

> - 상태: 예정
> - 권장 분량: 5회
> - 핵심 질문: metric score를 release decision에 사용할 만큼 어떻게 신뢰할 수 있게 만드는가?

이번 주의 목표는 높은 score를 만드는 것이 아니라, metric score를 사람이 내릴
release decision에 연결할 수 있는지 검증하는 것이다. 사람 라벨을 기준으로
불일치를 관찰하고, 오류 비용에 맞춰 threshold를 정한 뒤, 같은 사례를 반복
평가해 그 결정이 안정적인지 확인한다.

여기서 calibration은 모델 답변을 개선하거나 score를 확률로 바꾸는 작업이
아니다. **이 과정에서는 metric score와 사람이 정한 pass/fail 기준이 어디서
일치하고 어긋나는지 확인해 threshold 운영 규칙을 정하는 threshold
calibration**을 뜻한다. `0.8`은 80% 확률로 정답이라는 뜻도, 품질이 80점이라는
뜻도 아니다.

5주차는 API 사용법보다 실험 설계와 데이터 검토가 어렵다. 30개 사례를 한 번에
라벨링하지 않고, 10개 파일럿으로 rubric 문제를 찾은 뒤 30개로 확장한다.
threshold는 보기 좋은 숫자가 아니라 false positive와 false negative의 비용으로
선택한다. 30개는 이 절차를 배우기 위한 교육용 표본이며 production 신뢰성을
통계적으로 보장하는 숫자는 아니다.

## 이번 주의 의사결정 흐름

```text
제품의 사람 pass/fail 기준과 오류 비용 정의
        ↓ score를 보기 전에 blind labeling
judge score/reason과 사람 라벨 비교
        ↓ 명백한 불일치면 rubric/reference 먼저 수정
여러 threshold 후보에서 FP/FN 비교
        ↓
provisional threshold 선택
        ↓ 경계 사례 반복성 확인
operational threshold 또는 manual-review band 결정
```

### 핵심 용어

| 용어 | 의미 | 주의할 오해 |
| --- | --- | --- |
| human label | 제품 요구사항 소유자가 정한 pass/fail 기준점 | 사람이 항상 무오류라는 뜻은 아님 |
| judge score | rubric과 입력 field를 judge가 해석한 결과 | 정답 확률이 아님 |
| threshold | score를 pass/fail 행동으로 바꾸는 경계 | 보기 좋은 기본값이 아님 |
| FP | 좋은 답변을 metric이 막은 경우 | 출시 지연과 검토 비용을 만듦 |
| FN | 나쁜 답변을 metric이 통과시킨 경우 | 사용자·정책 위험을 만듦 |
| repeatability | 같은 사례와 설정에서 판정이 얼마나 안정적인지 | API 오류와 같은 개념이 아님 |

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
- [ ] judge 실행 결과는 비결정적일 수 있지만 score 자체가 정답 확률은 아님을 기록한다.
- [ ] criteria, evaluation step, judge model, DeepEval 버전이 score에 영향을 준다고 기록한다.
- [ ] reason은 원문·reference·rubric과 함께 검토한다.
- [ ] 고위험 gate에는 deterministic assertion, 사람 라벨, judge를 함께 사용한다.

세 수단은 매 CI 실행에서 사람이 다시 판정한다는 뜻이 아니다. deterministic
assertion은 JSON schema나 금지값처럼 코드로 확정 가능한 조건을 실행마다
검사한다. 사람 라벨은 rubric과 threshold를 설계·보정하는 기준점이고, LLM
judge는 표현 차이를 허용해야 하는 의미 품질을 반복 평가한다.

### 왜 계약을 score보다 먼저 쓰는가

score를 본 뒤 pass 기준과 오류 비용을 바꾸면 현재 결과에 맞춰 평가 규칙을
합리화하게 된다. 먼저 “주문 번호 누락을 fail로 볼 것인가?”, “90일 정책 모순을
통과시키는 비용이 좋은 답변 하나를 막는 비용보다 큰가?”를 정해야 threshold의
선택 근거가 제품 요구사항에 남는다. 사람 라벨도 자동 정답은 아니므로 경계나
고위험 사례는 두 번째 reviewer 또는 재검토 규칙을 둔다.

### calibration 계약

`evals/calibration/refund_calibration_plan.md`에 작성한다.

```markdown
# Refund completeness calibration plan

- 보정할 metric:
- 사람의 pass 기준:
- 사람의 fail 기준:
- pass 판정 규칙: score >= threshold
- false positive의 비용:
- false negative의 비용:
- 고정할 judge/model 설정:
- metric 버전:
- labeling rubric 버전과 reviewer:
- 경계 사례 재검토 절차:
- 데이터에서 제외할 오류:
- 재보정할 변경 조건:
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

각 행에는 최소한 `case_id`, `input`, 고정된 `actual_output`, metric에 필요한
`expected_output` 또는 `context`, `human_label`, `label_reason`, `category`,
`rubric_version`을 기록한다. 사람과 judge가 **같은 고정 actual_output**을
판정해야 FP/FN 비교가 성립한다. calibration 중 앱을 다시 호출하면 generator
변동성과 judge 해석 차이가 섞인다. metric score와 judge reason은 `case_id`로
연결되는 별도 실행 결과에 기록해 사람 판단이 score에 영향을 받지 않게 한다.

`clear_pass`, `clear_fail`, `boundary`는 사례의 category이고 최종 사람 판정은
여전히 pass 또는 fail이다. 명백한 사례는 rubric이 기본 방향을 이해하는지
확인한다. 경계 사례는 score를 본 뒤 고르지 않고, 주문 번호 하나 누락처럼
**사람 rubric상 판정이 어려운 사례를 먼저 선정**한다. 그 후 judge를 실행해
실제로 threshold 부근에 놓이는지와 팀 기준과 judge 해석이 어디서 갈리는지
관찰한다.

### 실행 순서

1. 사람 라벨과 근거를 확정한다.
2. judge/model/metric 설정을 고정한다.
3. 10개를 한 번 실행한다.
4. 사람과 judge가 불일치한 사례부터 검토한다.
5. 불일치를 먼저 `rubric`, `reference`, `human_label`, `unclassified`로 분류한다.

이 단계에서는 threshold를 확정하지 않는다. 명백한 사례에서 불일치가 많으면 rubric이나 reference를 먼저 고친다.

한 번의 실행만으로 `judge_variance`라고 결론내릴 수 없다. 원문, reference,
rubric과 사람 라벨로 설명되지 않는 불일치만 같은 고정 출력과 설정으로 반복해
판정이 실제로 뒤집히는지 확인한다. rubric이나 reference를 수정했다면 version을
올리고 파일럿 전체를 다시 실행해 서로 다른 계약의 score를 섞지 않는다.

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

`10 + 10 + 10`은 통계 공식이 아니라 reviewer 피로와 라벨 기준의 drift를 줄이기
위한 작업 단위다. 각 묶음 후 기준이 바뀌면 앞선 묶음도 다시 검토한다. 가능하면
20개를 calibration split, 남은 10개를 작은 holdout으로 정한다. 20개의 score로
provisional threshold를 고정한 뒤에만 holdout score를 한 번 확인한다. holdout
결과가 나쁘다고 같은 10개에 다시 맞추지 않는다. rubric이나 데이터를 고쳐야
한다면 version을 올리고 새로운 validation 표본으로 다시 확인한다.

학습을 위해 category를 균형 있게 구성한 표본은 실제 production 발생 비율과
다를 수 있다. 따라서 전체 FP/FN 숫자만 보지 않고 `policy_contradiction` 같은
고위험 category 결과를 별도로 확인한다. 실제 운영에서는 production 분포와 더
큰 독립 validation dataset으로 다시 보정해야 한다.

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
> - 선행 조건: 30개 사람 라벨, calibration split 20개의 metric score

권장 파일:

```text
evals/calibration/analyze_refund_threshold.py
evals/calibration/refund_threshold_decision.md
```

### 용어

- false positive: 사람이 pass한 좋은 답변을 metric이 fail 처리
- false negative: 사람이 fail한 나쁜 답변을 metric이 pass 처리

이 문서에서는 **positive를 “실패 감지/배포 차단”**으로 정의한다. metric의
pass 규칙은 `score >= threshold`다. 이 convention을 먼저 고정하지 않으면
TP/TN/FP/FN을 반대로 계산하기 쉽다.

| 사람 판단 \ metric 판단 | fail/차단 (`score < threshold`) | pass (`score >= threshold`) |
| --- | --- | --- |
| fail | TP: 나쁜 답변을 차단 | FN: 나쁜 답변이 통과 |
| pass | FP: 좋은 답변을 차단 | TN: 좋은 답변이 통과 |

- threshold를 올리면 더 많은 사례가 fail이 되어 보통 FN은 줄고 FP는 늘어난다.
- threshold를 내리면 더 많은 사례가 pass가 되어 보통 FP는 줄고 FN은 늘어난다.

### 계산을 결정으로 바꾸는 예시

다음 숫자는 설명을 위한 예시다. FP 비용을 1, FN 비용을 5로 두면 단순 오류
비용은 `FP 수 × 1 + FN 수 × 5`로 비교할 수 있다.

| threshold | FP | FN | 정책 모순 FN | 단순 오류 비용 |
| ---: | ---: | ---: | ---: | ---: |
| 0.60 | 1 | 4 | 1 | 21 |
| 0.70 | 3 | 1 | 0 | 8 |
| 0.80 | 7 | 0 | 0 | 7 |

비용 숫자가 가장 낮다고 자동 선택하지 않는다. 0.80에서 좋은 답변 7개를 막는
운영 부담을 감수할 수 있는지, 0.70과 정책 모순 hard gate의 조합이 더 적절한지
`case_id`를 읽고 결정한다. 다른 사례의 높은 score로 개인정보 노출이나 명백한
정책 모순 한 건을 상쇄하지 않는다.

### 분석 작업

- [ ] 여러 threshold 후보에서 TP, TN, FP, FN을 계산한다.
- [ ] 각 오류를 숫자뿐 아니라 `case_id`로 검토한다.
- [ ] 정책 모순 같은 중요한 false negative가 통과하는지 확인한다.
- [ ] 세션 1에서 정한 오류 비용을 적용한다.
- [ ] provisional threshold와 선택 근거를 문서화한다.
- [ ] threshold를 고정한 뒤 holdout 10개를 한 번 평가해 일반화 신호를 확인한다.

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
- [ ] holdout과 세션 5 반복성 확인 전에는 provisional 값임을 명시했다.

## 세션 5: 반복성, 비용, API 오류

> - 예상 시간: 60~90분
> - 선행 조건: threshold 후보 확정

권장 테스트:

```text
tests/evals/test_week5_session5_flaky_eval.py
```

### 경계 사례 반복

경계 사례 3~5개만 좁게 반복한다.

같은 `input`, `actual_output`, `expected_output`, rubric과 judge model을 고정하고
judge만 반복해야 judge variance를 볼 수 있다. 앱까지 다시 호출하면 generator
변동성과 judge 변동성이 섞인다. 반복성 실험에서는 cache가 이전 결과를 재사용해
변동을 숨길 수 있으므로 cache를 사용하지 않는다. cache 효과는 아래 비용
실습에서 별도로 비교한다.

```bash
.venv/bin/deepeval test run tests/evals/test_week5_session5_flaky_eval.py -r 3
```

- [ ] score의 최소, 최대, 평균을 기록한다.
- [ ] pass/fail이 뒤집힌 사례를 찾는다.
- [ ] threshold 기준 pass 횟수와 threshold까지의 margin을 기록한다.
- [ ] threshold를 낮추기 전에 rubric과 사람 라벨의 모호함을 검토한다.
- [ ] judge model과 metric 설정을 고정한다.

예를 들어 threshold가 0.70이고 반복 score가 `0.68, 0.74, 0.69`라면 평균만
보고 안정적인 pass라고 할 수 없다. 세 번 중 한 번만 pass했으므로 CI hard gate로
사용하기 전에 rubric, reference와 사람 라벨의 모호함을 다시 본다. 필요하다면
명백한 위험을 deterministic hard gate로 분리하거나 manual-review band를
도입한다. threshold만 낮춰 판정 뒤집힘을 숨기지 않는다.

### 비용과 시간

```bash
.venv/bin/deepeval test run tests/evals -c
.venv/bin/deepeval test run tests/evals -n 2
```

- [ ] `case 수 × metric 수 × 반복 수`로 호출량을 추정한다.
- [ ] cache 전후 실행 시간과 호출 수를 비교한다.
- [ ] 병렬 실행은 2개부터 시작해 rate limit을 관찰한다.

`case 수 × metric 수 × 반복 수`는 1차 추정치다. GEval 내부 judge 단계,
재시도, prompt 길이와 provider 과금 방식 때문에 실제 API 호출 수와 비용은 더
클 수 있으므로 실행 로그의 실제 호출 수, token, 재시도와 시간을 함께 기록한다.

### 오류 triage

| 분류 | 예시 | 처리 |
| --- | --- | --- |
| 제품 품질 실패 | score가 threshold 미만 | 제품 회귀 실패 |
| 데이터 실패 | reference 오류, required field 누락 | 평가 무효, 데이터 수정 |
| judge/API 오류 | rate limit, quota, timeout, 구조화 출력 오류 | 평가 미완료, 재실행/인프라 조치 |

release 결과는 다음 세 상태로 생각한다.

- `PASS`: 모든 필수 평가가 정상 실행되어 통과
- `FAIL`: 유효한 평가에서 제품 품질 기준 미달
- `INCONCLUSIVE`: 데이터 오류나 judge/API 오류로 평가가 무효 또는 미완료

`INCONCLUSIVE`는 제품 실패는 아니지만 품질 통과의 증거도 아니다. 제한된
재시도, 데이터 수정 또는 사람 검토로 이어져야 한다.

- [ ] `--ignore-errors`를 release gate 기본값으로 사용하지 않는다.
- [ ] API 오류를 제품 품질 통과로 집계하지 않는다.

## 5주차 완료 조건

- [ ] 30개 라벨 dataset 중 calibration split으로 threshold를 보정하고 holdout으로 확인했다.
- [ ] FP/FN과 중요한 오류 사례가 기록되어 있다.
- [ ] 경계 사례의 반복 안정성을 알고 있다.
- [ ] 품질, 데이터, judge/API 오류를 구분한다.
- [ ] 대략적인 호출량, 비용, 시간을 예측한다.
- [ ] operational threshold, review band 또는 hard gate 조합을 선택한 근거가 있다.
- [ ] score가 의미하는 것과 의미하지 않는 것을 설명할 수 있다.

## 막히기 쉬운 지점

- score를 먼저 본 뒤 사람 라벨을 정한다.
- clear pass/fail만 사용해 threshold 근처 동작을 보지 못한다.
- 정확도 하나만 보고 중요한 false negative를 놓친다.
- flaky를 숨기기 위해 threshold만 낮춘다.
- API 오류가 ignored 상태라 release가 잘못 통과한다.

참고: [Flags and Configs](https://deepeval.com/docs/evaluation-flags-and-configs), [Unit Testing in CI/CD](https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd)

이전: [4주차 — RAG 평가](week4_rag_evaluation.md) · 다음: [6주차 — CI와 캡스톤](week6_ci_and_capstone.md)
