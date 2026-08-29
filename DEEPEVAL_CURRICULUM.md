# DeepEval 실습 커리큘럼

> - 대상: Python, pytest, Appium 경험이 있지만 LLM 평가와 DeepEval은 처음인 SDET
> - 전체 권장 기간: 준비 단계를 포함해 약 7~8주
> - 현재 남은 분량: 약 3~4주, 13회, 회당 60~90분
> - 기준 버전: DeepEval 4.x, 저장소 설치 버전 4.1.4
> - 상세 문서: [`curriculum/`](curriculum/README.md)

이 문서는 전체 학습 순서, 현재 진행 상태, 최종 완료 정의를 관리하는 인덱스다. 세션별 설명, 실습 단계, 권장 파일, 검증 명령과 완료 조건은 `curriculum/`의 주차별 문서를 기준으로 한다.

## 현재 진행 상태

준비 단계, 1주차 전체, 2주차 세션 1~3, 3주차 세션 1~3,
4주차 세션 1~2는 완료한 것으로 본다. 완료 세션 안에 과거 미체크 기록이
남아 있더라도 남은 필수 학습량에는 포함하지 않는다.

| 구간 | 상태 | 권장 분량 | 상세 문서 | 핵심 산출물 |
| --- | --- | ---: | --- | --- |
| 준비 단계 | 완료 | 2~3회 | [환경과 첫 평가](curriculum/00_setup.md) | pass/fail 첫 eval |
| 1주차 | 완료 | 4회 | [평가의 테스트 모델](curriculum/week1_evaluation_foundations.md) | field와 assertion 구분 |
| 2주차 세션 1~3 | 완료 | 3회 | [metric과 GEval](curriculum/week2_metrics_and_geval.md) | 결함-metric 매핑, custom rubric, 경계 사례 |
| 2주차 세션 4 | 예정 | 1회 | [metric과 GEval](curriculum/week2_metrics_and_geval.md) | reference 전략과 실패 진단 |
| 3주차 세션 1~3 | 완료 | 3회 | [dataset과 regression](curriculum/week3_dataset_and_regression.md) | 최소 앱, Golden, 로컬 dataset |
| 3주차 세션 4 | 진행 중 | 1회 | [dataset과 regression](curriculum/week3_dataset_and_regression.md) | pytest regression과 데이터 리뷰 |
| 4주차 세션 1~2 | 완료 | 2회 | [RAG 평가](curriculum/week4_rag_evaluation.md) | end-to-end 증상과 retriever 진단 |
| 4주차 세션 3 | 진행 중 | 1회 | [RAG 평가](curriculum/week4_rag_evaluation.md) | generator 관련성·충실성·완전성 격리 실험 |
| 4주차 세션 4 | 예정 | 1회 | [RAG 평가](curriculum/week4_rag_evaluation.md) | RAG suite 통합 |
| 5주차 | 예정 | 5회 | [보정과 신뢰도](curriculum/week5_calibration_and_reliability.md) | 사람 라벨 기반 threshold |
| 6주차 | 예정 | 4회 | [CI와 캡스톤](curriculum/week6_ci_and_capstone.md) | 재현 가능한 eval pipeline |
| 선택 심화 | 선택 | 2~3회/트랙 | [고급 트랙](curriculum/optional_advanced_tracks.md) | 관심 시스템 최소 예제 |

## 학습 순서

```text
완료: 환경과 첫 eval
  ↓
완료: LLMTestCase와 assertion 구분
  ↓
완료: 표준 metric, custom GEval, 경계 사례
  ↓
완료: 최소 앱 → Golden → EvaluationDataset
  ↓
완료: RAG end-to-end → retriever
  ↓
현재: generator 진단 → RAG suite 통합
  ├─ 병행 보완: 2주차 reference 전략
  └─ 병행 보완: 3주차 dataset 리뷰
  ↓
사람 라벨 → threshold → flaky/비용 관리
  ↓
smoke/full suite → CI → baseline 비교 → 개선 loop
  ↓
선택: tracing / Agent / multi-turn / SDET 응용
```

## 이 과정의 최종 산출물

- [ ] 사용자 위험과 interaction 범위를 정의한 평가 계약
- [ ] 20개 이상의 사람이 검토한 Golden으로 구성된 로컬 JSONL dataset
- [ ] 실제 앱 callback에서 runtime output을 생성하는 test pipeline
- [ ] 표준 metric 2~3개와 제품 요구사항용 custom `GEval` 1개
- [ ] 일반 pytest assertion을 사용하는 deterministic 검사
- [ ] 사람 라벨과 FP/FN으로 보정한 threshold 기록
- [ ] smoke/full suite를 선택 실행하는 pytest/DeepEval 회귀 테스트
- [ ] 데이터·retriever·generator·judge/API 실패를 구분하는 triage 규칙
- [ ] 로컬과 CI에서 동일하게 실행되는 smoke gate
- [ ] 평가 결과로 실제 시스템을 개선하고 추가한 regression 사례

## 학습 원칙

### 1. 사용자 위험이 metric보다 먼저다

metric 이름이 익숙하다는 이유로 추가하지 않는다. “이 score가 낮으면 어느 컴포넌트를 고칠 것인가?”에 답할 수 있어야 한다.

### 2. deterministic 검사가 judge보다 먼저다

JSON 파싱, 필수 key, 타입, 길이와 enum처럼 코드로 확정할 수 있는 조건은 일반 pytest assertion으로 검사한다. 의미, 관련성, 근거 충실성과 표현 차이를 허용해야 하는 조건만 LLM judge에 맡긴다.

### 3. 정적 reference와 runtime observation을 분리한다

- `expected_output`, `context`, `expected_tools`: 사람이 검토한 정적 reference
- `actual_output`, `retrieval_context`, `tools_called`: 앱 실행에서 나온 runtime observation

둘을 섞으면 실패 원인이 데이터인지 앱인지 구분하기 어렵다.

### 4. 소수의 명백한 사례에서 시작한다

새 metric은 pass 2개와 fail 2개로 방향을 확인한 후 경계 사례를 추가한다. Golden도 5개 smoke에서 시작해 10개, 20개로 확장한다.

### 5. score와 reason을 모두 검토한다

judge reason도 모델 출력이다. 그럴듯하다는 이유로 자동 수용하지 않고 원문, reference, rubric과 함께 확인한다.

### 6. 필수 트랙은 RAG 하나다

Agent, multi-turn, tracing을 모두 수행하지 않는다. 환불 RAG 필수 과정을 끝낸 뒤 실제 관심이 있는 선택 트랙 하나만 진행한다.

## 주차별 빠른 이동

1. [준비 단계 — 환경과 첫 평가](curriculum/00_setup.md)
2. [1주차 — LLM 평가의 테스트 모델](curriculum/week1_evaluation_foundations.md)
3. [2주차 — 표준 metric과 custom GEval](curriculum/week2_metrics_and_geval.md)
4. [3주차 — 최소 앱, Golden, dataset, 회귀 테스트](curriculum/week3_dataset_and_regression.md)
5. [4주차 — RAG end-to-end와 실패 원인 분리](curriculum/week4_rag_evaluation.md)
6. [5주차 — 사람 라벨, threshold, 반복성과 비용](curriculum/week5_calibration_and_reliability.md)
7. [6주차 — CI/CD와 누적형 캡스톤](curriculum/week6_ci_and_capstone.md)
8. [선택 심화 — tracing, Agent, multi-turn, SDET 응용](curriculum/optional_advanced_tracks.md)

## 공통 실행과 검증

가상환경의 실행 파일을 명시한다.

```bash
# API 호출 없는 일반 pytest부터 실행
.venv/bin/python -m pytest tests/evals -v

# judge가 필요한 세션만 좁게 실행
.venv/bin/deepeval test run tests/evals/test_week{주차}_session{세션}_{주제}.py -v

# 최종 변경 범위 확인
git diff --check
git status --short
```

LLM judge 호출은 비용과 변동성이 있으므로 학습 목표가 아닌 검증을 위해 전체 suite를 불필요하게 실행하지 않는다.

## 공식 자료 읽기 순서

1. 완료 구간 복습: [Introduction](https://deepeval.com/docs/introduction), [Single-Turn Test Case](https://deepeval.com/docs/evaluation-test-cases)
2. 2주차: [Metrics Introduction](https://deepeval.com/docs/metrics-introduction)
3. 3주차: [Evaluation Datasets](https://deepeval.com/docs/evaluation-datasets)
4. 4주차: [End-to-End Evaluation](https://deepeval.com/docs/evaluation-end-to-end-llm-evals), [RAG QA Tutorial](https://deepeval.com/tutorials/rag-qa-agent/evaluation)
5. 5~6주차: [Flags and Configs](https://deepeval.com/docs/evaluation-flags-and-configs), [Unit Testing in CI/CD](https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd)
6. 선택 심화: [LLM Tracing](https://deepeval.com/docs/evaluation-llm-tracing), [Component-Level Evaluation](https://deepeval.com/docs/evaluation-component-level-llm-evals)

문서와 API가 다르면 `.venv/bin/deepeval test run --help`, 설치된 package signature, 공식 문서와 release note 순서로 확인한다.

## 최종 완료 정의

체크박스 개수가 아니라 다음 능력을 기준으로 완료를 판단한다.

**새로운 LLM 기능 요구사항을 받았을 때 사용자 위험을 정의하고, 실제 앱 callback에서 runtime data를 수집하고, reviewed Golden과 적합한 metric을 만들고, 사람 판단으로 threshold를 보정하고, 실패 원인을 분류해 CI 회귀 테스트로 운영할 수 있다면 필수 커리큘럼을 완료한 것이다.**
