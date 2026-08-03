# 2주차 세션 3 — GEval 경계 사례 관찰 기록

이 문서는 threshold를 확정하는 calibration 결과가 아니다. 여섯 사례에서
사람의 평가 계약과 judge의 rubric 해석이 일치하는지 확인하는 학습 기록이다.

## 실행 조건

- 실행 날짜:
- DeepEval 버전: `4.1.4`
- judge model: `gpt-5.4`
- 임시 threshold: `0.7`
- 반복 실행 횟수: baseline 1회, 수정 rubric 1회

## 1. Judge 실행 전 사람 판정

| scenario_id | human_expected | 한 줄 근거 |
| --- | --- | --- |
| `clear_pass_001` | `pass` | 기간, 필요 정보, 요청 채널을 모두 안내한다. |
| `clear_pass_002` | `pass` | 표현 순서는 다르지만 세 필수 요소가 모두 있다. |
| `clear_fail_001` | `fail` | 주문 번호와 고객센터 접수 방법이 모두 빠졌다. |
| `clear_fail_002` | `fail` | 핵심 정책인 환불 가능 기간이 reference와 모순된다. |
| `boundary_missing_order_id` | `pass` | 주문 번호는 없지만 환불 방법을 안내해 다음 단계로 진행할 수 있다. |
| `boundary_vague_channel` | `fail` | 문의 창구와 고객센터는 서로 다른 채널일 수 있다. |

## 2. Baseline rubric 관찰

```bash
.venv/bin/python \
  tests/evals/week2_session3_geval_boundary_exercise.py --run-baseline
```

| scenario_id | human | judge | score | 일치 | reason 요약 |
| --- | --- | --- | ---: | --- | --- |
| `clear_pass_001` | pass | pass | 1.00 | yes | 기간, 주문 번호, 고객센터, 전액 환불을 모두 포함했다. |
| `clear_pass_002` | pass | pass | 1.00 | yes | 표현 순서는 다르지만 필수 정보를 모두 포함했다. |
| `clear_fail_001` | fail | pass | 0.72 | no | 여러 절차가 빠졌지만 부분적으로 유용하다는 이유로 통과했다. |
| `clear_fail_002` | fail | fail | 0.21 | yes | 환불 기간을 90일로 잘못 안내한 정책 모순을 발견했다. |
| `boundary_missing_order_id` | pass | pass | 0.88 | yes | 주문 번호 누락을 경미한 불완전성으로 판단했다. |
| `boundary_vague_channel` | fail | pass | 1.00 | no | 문의 창구를 고객센터와 의미상 같은 표현으로 판단했다. |

## 3. 불일치 진단과 한 번의 rubric 수정

- 선택한 문제: `clear_fail_001`
- 분류: `rubric`
- 판단 근거: Judge는 주문 번호와 고객센터 요청 방법이 빠졌음을 인식했지만
  `0.72`를 부여해 pass 처리했다.
- 변경 전 모호한 부분: 완전한 환불 안내에 포함되어야 하는 항목이 명시되지
  않았다.
- 변경 내용: 주문 번호, 고객센터, 환불 안내를 중요 정보로 명시했다.
- 바꾸지 않은 것: 사례, 사람 라벨, threshold

## 4. 수정 rubric 재실행

```bash
.venv/bin/python \
  tests/evals/week2_session3_geval_boundary_exercise.py --run-revised
```

| scenario_id | human | judge | score | 일치 | reason 요약 |
| --- | --- | --- | ---: | --- | --- |
| `clear_pass_001` | pass | pass | 0.94 | yes | 필수 정보를 모두 포함했지만 표현 차이를 소폭 감점했다. |
| `clear_pass_002` | pass | pass | 0.98 | yes | 기간, 주문 번호, 고객센터와 전액 환불 안내를 포함했다. |
| `clear_fail_001` | fail | fail | 0.30 | yes | 주문 번호와 고객센터 요청 방법 누락을 명확한 실패로 판단했다. |
| `clear_fail_002` | fail | fail | 0.34 | yes | 30일을 90일로 바꾼 정책 모순을 실패로 판단했다. |
| `boundary_missing_order_id` | pass | fail | 0.70* | no | 주문 번호 하나의 누락을 사람 기준보다 엄격하게 평가했다. |
| `boundary_vague_channel` | fail | pass | 0.79 | no | 문의 창구를 고객센터와 의미상 동등한 채널로 인정했다. |

`0.70*`은 소수점 둘째 자리로 반올림된 출력이다. 실제 score가 threshold보다
조금 낮아 fail로 판정됐을 가능성이 있으므로 이후 실행은 네 자리까지 기록한다.

## 5. 결론

- 수정으로 좋아진 점: 명백한 실패 사례인 `clear_fail_001`이 기대대로 fail로
  바뀌었다.
- 새로 나빠진 점: 주문 번호 하나만 빠진 경계 사례까지 fail이 되어 사람
  기준보다 엄격해졌다.
- 여전히 모호한 점: 문의 창구와 고객센터를 동등한 요청 채널로 볼지 합의가
  필요하다.
- 5주차 calibration 후보: `boundary_missing_order_id`,
  `boundary_vague_channel`
- 현재 threshold가 임시 값인 이유: 여섯 사례를 한 번씩 실행한 결과만으로는
  사람 기준과 judge 변동성을 충분히 추정할 수 없다.
