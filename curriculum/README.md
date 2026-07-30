# DeepEval 주차별 커리큘럼 안내

이 디렉터리는 `DEEPEVAL_CURRICULUM.md`의 주차별 상세 내용을 보관한다. 루트 문서는 전체 진행 현황과 학습 순서를 보여 주는 인덱스이고, 실제 세션의 목표·실습·완료 조건은 여기의 주차별 문서를 기준으로 한다.

전체 진행 상태는 [DeepEval 실습 커리큘럼 인덱스](../DEEPEVAL_CURRICULUM.md)에서 확인한다.

## 문서 구성

| 문서 | 상태 | 핵심 주제 |
| --- | --- | --- |
| [준비 단계](00_setup.md) | 완료 | 환경, API key, 첫 pass/fail eval |
| [1주차](week1_evaluation_foundations.md) | 완료 | 평가 계약, `LLMTestCase`, 실행 방법, assertion 분리 |
| [2주차](week2_metrics_and_geval.md) | 진행 중 | 표준 metric, custom `GEval`, reference 전략 |
| [3주차](week3_dataset_and_regression.md) | 예정 | 최소 앱, Golden, dataset, pytest regression |
| [4주차](week4_rag_evaluation.md) | 예정 | RAG end-to-end, retriever, generator 진단 |
| [5주차](week5_calibration_and_reliability.md) | 예정 | 사람 라벨, threshold, flaky, 비용과 오류 |
| [6주차](week6_ci_and_capstone.md) | 예정 | smoke/full suite, CI, 변경 비교, 캡스톤 |
| [선택 심화](optional_advanced_tracks.md) | 선택 | tracing, Agent, multi-turn, SDET 응용 |

## 한 세션을 진행하는 방법

각 세션은 원칙적으로 60~90분을 기준으로 한다. 5주차의 30개 calibration dataset 작성처럼 작업량이 큰 세션은 120분까지 걸릴 수 있으므로 두 번에 나누어도 된다.

1. 세션의 선행 조건과 “왜 배우는가”를 먼저 읽는다.
2. API를 호출하지 않는 구조 검사나 일반 pytest assertion부터 작성한다.
3. 명백한 pass/fail 소수 사례로 평가 방향을 확인한다.
4. 필요한 경우에만 LLM judge를 실행한다.
5. score뿐 아니라 reason과 실패 컴포넌트를 기록한다.
6. 완료 조건을 충족하면 루트 인덱스와 해당 주차 문서의 상태를 갱신한다.

## 상태 표기

- `완료`: 다시 수행할 필요가 없는 세션이다. 필요할 때 참고 자료로만 사용한다.
- `진행 중`: 일부 산출물이 있지만 완료 조건을 아직 검증 중이다.
- `예정`: 선행 세션이 끝난 후 순서대로 진행한다.
- `선택`: 필수 완료 정의에는 포함되지 않는다.

체크박스 하나하나보다 세션의 완료 조건을 우선한다. 이미 완료 처리된 세션 안에 미체크 기록이 남아 있어도 남은 필수 학습량에는 포함하지 않는다.

## 공통 산출물 위치

| 산출물 | 위치 |
| --- | --- |
| 평가 대상 예제 앱 | `app/` |
| pytest/DeepEval 평가 테스트 | `tests/evals/` |
| Golden과 JSONL dataset | `evals/data/` |
| 재사용 custom metric | `evals/metrics/` |
| 사람 라벨과 threshold 결정 | `evals/calibration/` |

## 공통 검증 순서

```bash
# 1. API 호출 없는 테스트
.venv/bin/python -m pytest tests/evals -v

# 2. 해당 세션의 judge 평가만 좁게 실행
.venv/bin/deepeval test run tests/evals/test_week{주차}_session{세션}_{주제}.py -v

# 3. 변경 범위 확인
git diff --check
git status --short
```

외부 judge 실행이 학습 목표가 아닌 세션에서는 두 번째 명령을 생략한다.

## 학습 기록 템플릿

```markdown
## YYYY-MM-DD — 주차/세션/주제

- 완료한 항목:
- 실행 명령:
- DeepEval / judge 설정:
- 사용한 case_id:
- 명백한 pass/fail 결과:
- 경계 사례 결과:
- 실패 분류(data/retriever/generator/judge/API):
- 예상과 달랐던 점:
- 비용/소요 시간:
- 다음에 추가할 golden:
- 남은 질문:
```
