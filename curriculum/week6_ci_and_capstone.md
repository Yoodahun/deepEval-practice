# 6주차 — CI/CD와 누적형 캡스톤

> - 상태: 예정
> - 권장 분량: 4회
> - 핵심 질문: 로컬 eval을 비용과 실패 의미가 명확한 release gate로 어떻게 운영할 것인가?

6주차는 새 프로젝트를 처음부터 만드는 주차가 아니다. 2~5주차에서 만든 환불 고객지원 앱, custom metric, RAG test, Golden, threshold를 조립한다. 마지막에는 평가 결과로 실제 시스템을 한 번 개선하고 그 결함을 새로운 regression 사례로 보호한다.

## 주차 학습 지도

| 세션 | 난이도 | 핵심 산출물 |
| --- | ---: | --- |
| 1. smoke/full suite | 3/5 | 목적이 다른 두 실행 집합 |
| 2. CI workflow | 4/5 | secret을 사용하는 PR gate |
| 3. baseline 비교 | 3/5 | case별 regression 표 |
| 4. 캡스톤 | 3/5 | 재현 가능한 개선 loop |

## 세션 1: smoke/full suite 설계

> - 예상 시간: 60~90분
> - 선행 조건: reviewed Golden 20개, 보정된 metric

### suite 목적

| suite | 실행 시점 | 범위 | 우선 목표 |
| --- | --- | --- | --- |
| smoke | PR/push | 5~10개, 핵심 metric | 빠르게 치명적 회귀 차단 |
| full | nightly/manual | 전체 20개 이상 | 폭넓은 회귀와 경계 변화 탐지 |
| calibration/repeat | 수동 | 경계 사례와 반복 | metric 안정성 확인 |

### smoke 선택 기준

- [ ] 가장 흔한 정상 흐름을 포함한다.
- [ ] 정책 모순과 개인정보 위험처럼 반드시 막아야 할 사례를 포함한다.
- [ ] 과거 실제 결함을 최소 한 개 포함한다.
- [ ] 10개 이하로 유지한다.
- [ ] 비용 때문에 full보다 metric 수를 줄일 수 있지만 보호 위험은 유지한다.

### marker와 실행 명령

```bash
.venv/bin/deepeval test run tests/evals --mark "smoke" --exit-on-first-failure -- --tb=short
.venv/bin/deepeval test run tests/evals --mark "full" -- --tb=short
```

- [ ] marker 기준이 metadata 또는 pytest marker 중 한 방식으로 일관된다.
- [ ] `--collect-only`로 선택되는 test ID를 먼저 확인한다.
- [ ] smoke와 full의 예상 case 수를 문서화한다.

### 완료 조건

- [ ] smoke가 가장 중요한 사용자 위험을 5~10개로 보호한다.
- [ ] full, smoke, calibration 실행 목적을 구분한다.

## 세션 2: CI workflow와 secret 처리

> - 예상 시간: 60~90분
> - 선행 조건: 로컬 smoke 명령 통과

### workflow 원칙

- 로컬에서 검증한 명령을 CI에서도 그대로 실행한다.
- dependency와 judge 설정을 고정한다.
- secret이 없는 실행과 API 오류를 제품 품질 통과로 보지 않는다.

권장 workflow 위치:

```text
.github/workflows/deepeval-smoke.yml
```

### 구현 체크리스트

- [ ] Python 버전을 명시한다.
- [ ] `requirements-lock.txt`로 dependency를 설치한다.
- [ ] `OPENAI_API_KEY`를 repository secret에서 주입한다.
- [ ] secret 값, raw request, 실제 고객 데이터가 로그에 출력되지 않는다.
- [ ] 로컬 smoke 명령을 동일하게 실행한다.
- [ ] metric threshold 실패가 non-zero exit code를 반환한다.
- [ ] API/network 오류가 품질 실패와 구분된다.
- [ ] fork PR처럼 secret이 없는 실행을 skip, deterministic-only 또는 별도 status 중 하나로 명시한다.

### 처음부터 실제 API를 호출하지 않아도 되는 검증

1. YAML 문법과 workflow trigger를 검토한다.
2. dependency 설치와 pytest 수집까지만 실행한다.
3. 작은 smoke subset으로 한 번 judge를 호출한다.
4. 의도적인 metric 실패가 job을 실패시키는지 확인한다.

### 완료 조건

- [ ] 동일 smoke command가 로컬과 CI에서 재현된다.
- [ ] secret이 소스와 로그에 없다.
- [ ] 평가 미실행 또는 API 오류가 성공으로 보고되지 않는다.

## 세션 3: baseline과 변경 후보 비교

> - 예상 시간: 60~90분
> - 선행 조건: dataset, metric, threshold, judge 설정 고정

### 공정한 비교 조건

한 번에 하나만 바꾼다.

- baseline prompt와 candidate prompt
- baseline retriever top-k와 candidate top-k
- baseline model과 candidate model

dataset과 judge 설정까지 동시에 바꾸면 무엇이 score 변화의 원인인지 알 수 없다.

### 비교 작업

- [ ] baseline의 prompt/model/retriever 설정을 기록한다.
- [ ] candidate에서 변경한 한 요소를 기록한다.
- [ ] 같은 Golden, metric, threshold, judge로 두 실행을 수행한다.
- [ ] 평균뿐 아니라 각 `case_id`의 regression과 improvement를 비교한다.
- [ ] hard gate 사례가 모두 유지되는지 확인한다.
- [ ] 출력, score, reason, 설정, 시간, 비용을 함께 보관한다.

비교표:

| case_id | baseline | candidate | 판정 | 다음 행동 |
| --- | ---: | ---: | --- | --- |
| refund-normal-001 | 0.82 | 0.91 | improvement | candidate 유지 |
| refund-policy-003 | 0.88 | 0.61 | regression | 변경 원인 조사 |

### 평균이 가리는 문제

19개가 조금 좋아지고 개인정보 관련 한 사례가 크게 나빠지면 평균은 개선될 수 있다. 중요한 case는 평균과 별도의 hard gate를 가져야 한다.

### 완료 조건

- [ ] 중요한 case별 regression을 찾을 수 있다.
- [ ] 유지, 수정, 롤백 중 하나를 근거 있게 선택한다.

## 세션 4: 누적형 캡스톤과 개선 loop

> - 예상 시간: 약 90분
> - 선행 조건: 2~6주차 필수 산출물

캡스톤 주제는 지금까지 사용한 **환불 고객지원 RAG**로 고정한다. Agent나 multi-turn을 새로 추가하지 않는다.

### 필수 산출물

- [ ] 사용자 위험이 포함된 평가 계약
- [ ] 20개 이상의 reviewed Golden
- [ ] deterministic assertion 최소 1개
- [ ] RAG 표준 metric 2개
- [ ] custom `GEval` 1개
- [ ] 사람 라벨과 FP/FN으로 보정한 threshold
- [ ] smoke/full 선택 방법
- [ ] 재현 가능한 로컬/CI 명령
- [ ] 품질·데이터·API 오류 triage 문서

### 한 번의 실제 개선 loop

1. 실패 case 하나를 고른다.
2. `retriever`, `generator`, `data`, `unknown` 중 진단 가설을 세운다.
3. 근거를 확인한 후 prompt, retrieval 설정 또는 reference 중 실제 원인 하나만 수정한다.
4. baseline과 같은 조건으로 다시 실행한다.
5. 목표 case의 개선과 다른 case의 regression을 함께 확인한다.
6. 같은 결함이 재발하지 않게 Golden 또는 deterministic assertion을 추가한다.

### 최종 재현성 리뷰

- [ ] 다른 사람이 README만 보고 환경을 구성한다.
- [ ] API 없는 deterministic test를 실행한다.
- [ ] secret을 제공한 환경에서 smoke eval을 실행한다.
- [ ] 각 metric이 보호하는 위험을 설명한다.
- [ ] 실패한 `case_id`에서 데이터와 의심 컴포넌트를 찾는다.
- [ ] DeepEval 업그레이드 전 작은 compatibility suite를 실행하는 절차가 있다.

## 6주차 완료 조건

- [ ] smoke 실패가 로컬과 CI에서 non-zero exit code로 연결된다.
- [ ] baseline과 candidate를 같은 조건에서 비교했다.
- [ ] 평가 결과로 실제 시스템을 한 번 개선했다.
- [ ] 개선한 결함을 새로운 regression 사례가 보호한다.

## 최종 완료 정의

체크박스 개수가 아니라 다음 능력으로 판단한다.

새로운 LLM 기능 요구사항을 받았을 때 사용자 위험을 정의하고, 실제 앱 callback에서 runtime data를 수집하고, reviewed Golden과 적합한 metric을 만들고, 사람 판단으로 threshold를 보정하고, 실패 원인을 분류해 CI 회귀 테스트로 운영할 수 있으면 필수 커리큘럼을 완료한 것이다.

## 막히기 쉬운 지점

- smoke에 full suite를 그대로 넣어 PR이 느리고 비싸진다.
- secret이 없는 상태를 성공으로 처리한다.
- baseline과 candidate에서 dataset이나 judge까지 바꾼다.
- 평균 score만 보고 중요한 단일 regression을 놓친다.
- 캡스톤에서 새 Agent 프로젝트를 시작해 누적 산출물을 활용하지 못한다.

참고: [Unit Testing in CI/CD](https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd), [Flags and Configs](https://deepeval.com/docs/evaluation-flags-and-configs)

이전: [5주차 — 보정과 신뢰도](week5_calibration_and_reliability.md) · 다음(선택): [고급 트랙](optional_advanced_tracks.md)
