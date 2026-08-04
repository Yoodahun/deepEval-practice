# 6주차 — CI/CD와 누적형 캡스톤

> - 상태: 예정
> - 권장 분량: 4회
> - 핵심 질문: 로컬 eval을 비용과 실패 의미가 명확한 release gate로 어떻게 운영할 것인가?

일반 unit test는 syntax, 타입과 API 계약을 잘 보호하지만 prompt, model,
retrieval 설정이나 색인 변경으로 생기는 의미 품질 회귀는 놓칠 수 있다. CI
eval은 2~5주차에서 사람이 검토한 사용자 위험을 merge 또는 release 전에 같은
조건으로 다시 확인하는 장치다.

여기서 release gate는 단순한 실행 명령이 아니다. **어떤 실패가 배포를 막고,
어떤 상태가 재실행이나 사람 검토로 가며, 어떤 증거가 있어야 통과로 인정되는지
정한 운영 규칙**이다. judge 변동성, API 오류, 비용, secret 부재와 오래된
Golden을 다루지 않으면 자동화가 오히려 잘못된 통과 또는 차단을 만들 수 있다.

6주차는 새 프로젝트를 처음부터 만드는 주차가 아니다. 2~5주차에서 만든 환불
고객지원 앱, custom metric, RAG test, Golden과 threshold를 조립한다. 마지막에는
평가 결과로 실제 시스템을 한 번 개선하고 그 결함을 regression 사례로 보호한다.

## 이번 주에 배우는 운영 흐름

```text
reviewed dataset + 고정된 metric/threshold
        ↓ 위험 기반 smoke/full 선택
로컬에서 동일 명령 검증
        ↓
CI에서 deterministic → judge eval 실행
        ↓
PASS / QUALITY_FAIL / DATA_ERROR / EVAL_ERROR / NOT_RUN 판정
        ↓
merge 차단, 제한 재시도, 사람 검토 또는 baseline 비교
        ↓
실패 진단 → 한 요소 수정 → red→green → regression 보호
```

### CI 결과의 다섯 상태

| 상태 | 의미 | gate 행동 |
| --- | --- | --- |
| `PASS` | 모든 필수 평가가 정상 실행되어 통과 | merge/release 허용 후보 |
| `QUALITY_FAIL` | 유효한 평가에서 제품 품질 기준 미달 | 차단하고 제품 수정 |
| `DATA_ERROR` | required field, reference, fixture 등 평가 데이터 오류 | 데이터 수정 후 전체 평가 재실행 |
| `EVAL_ERROR` | API, timeout, quota 등 평가 인프라 오류 | 제한 재시도 또는 인프라 조치 |
| `NOT_RUN` | secret 부재, 조건 불충족 등으로 실행되지 않음 | 별도 status로 표시하고 통과로 간주하지 않음 |

필수 gate는 `PASS`일 때만 green이다. `DATA_ERROR`, `EVAL_ERROR`와 `NOT_RUN`은
제품 결함은 아니지만 품질이 통과했다는 증거도 아니다. 앱의 실제
`actual_output` schema 위반은 제품 `QUALITY_FAIL`, fixture의 required field나
reference 손상은 `DATA_ERROR`로 구분한다.

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

smoke는 가장 쉬운 사례 모음이 아니라 **가장 큰 사용자 위험을 작은 비용으로
보호하는 risk-weighted subset**이다. 정상 흐름만 넣으면 빠르지만 중요한
회귀를 막지 못한다. 가능하면 `smoke ⊆ full` 관계를 유지하고, calibration은
제품 회귀가 아니라 metric/rubric의 안정성을 확인하는 별도 suite로 둔다.

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

DeepEval 4.1.4의 `--mark`는 pytest marker를 선택한다. 위 명령을 쓰려면
`@pytest.mark.smoke`, `@pytest.mark.full` 또는 parameter별 mark를 사용하고 marker를
pytest 설정에 등록한다. Golden metadata로 suite를 관리하려면 loader에서 먼저
subset을 만든 뒤 별도 테스트에 parameterize해야 하며 metadata만 추가해서
`--mark`가 자동으로 선택한다고 가정하지 않는다.

- [ ] pytest marker 또는 metadata loader 중 선택 방식을 구현과 명령에 일치시킨다.
- [ ] `--collect-only`로 선택되는 test ID를 먼저 확인한다.
- [ ] smoke와 full의 예상 case 수를 문서화한다.

### 완료 조건

- [ ] smoke가 가장 중요한 사용자 위험을 5~10개로 보호한다.
- [ ] full, smoke, calibration 실행 목적을 구분한다.
- [ ] smoke에서 제외한 사례와 그 이유를 비용·위험 기준으로 설명할 수 있다.

## 세션 2: CI workflow와 secret 처리

> - 예상 시간: 60~90분
> - 선행 조건: 로컬 smoke 명령 통과

### workflow 원칙

- 로컬에서 검증한 명령을 CI에서도 그대로 실행한다.
- dependency와 judge 설정을 고정한다.
- secret이 없는 실행과 API 오류를 제품 품질 통과로 보지 않는다.

CI는 먼저 싸고 결정적인 검사를 실행하고, 그다음 비용과 변동성이 있는 judge
평가를 실행한다. 이렇게 해야 JSONL schema나 import 오류를 발견하기 위해 API
비용을 쓰지 않고, 실패가 데이터 배선인지 의미 품질인지 구분할 수 있다.

### gate decision 예시

| 관찰 | 결과 상태 | 다음 행동 |
| --- | --- | --- |
| 금지값 등 제품 hard gate 실패 | `QUALITY_FAIL` | 제품 수정 후 재실행 |
| schema/reference 등 평가 데이터 검증 실패 | `DATA_ERROR` | 데이터 수정 후 전체 평가 재실행 |
| 안정적인 critical metric 실패 | `QUALITY_FAIL` | merge 차단 및 case 조사 |
| rate limit 또는 timeout | `EVAL_ERROR` | 제한된 재시도 후 계속 오류면 미완료 보고 |
| 경계 사례 판정 flip | 자동 통과/threshold 완화 금지 | repeat 또는 사람 검토 대상으로 분리 |
| fork PR에 secret 없음 | `NOT_RUN` | deterministic-only status와 judge 미실행을 구분 |

fork PR에서는 secret을 노출하지 않기 위해 deterministic check만 required로 둘 수
있다. 그러나 judge gate를 영구 생략하지 않는다. maintainer가 승인한 trusted
workflow, merge queue 또는 release branch 중 하나에서 같은 commit을 반드시
실행해 최종 `PASS` 증거를 얻는 경로를 정한다.

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
- [ ] 의도적인 품질 실패와 API 오류가 서로 다른 상태와 로그로 남는다.

## 세션 3: baseline과 변경 후보 비교

> - 예상 시간: 60~90분
> - 선행 조건: dataset, metric, threshold, judge 설정 고정

### 공정한 비교 조건

한 번에 하나만 바꾼다.

- baseline prompt와 candidate prompt
- baseline retriever top-k와 candidate top-k
- baseline model과 candidate model

dataset과 judge 설정까지 동시에 바꾸면 무엇이 score 변화의 원인인지 알 수 없다.

baseline은 단순히 직전 실행이 아니다. 팀이 승인한 현재 동작과 비교 조건의
묶음이다. 최소한 commit SHA, dataset version, prompt/model, retriever 설정,
judge model, metric/threshold, DeepEval 버전과 실행 시간을 기록한다. candidate는
그 조건에서 한 요소만 바꾼 제안이다.

```text
같은 dataset + 같은 judge + 같은 metric/threshold
                  ↓
         baseline과 candidate 비교
                  ↑
       prompt 또는 top-k 또는 model 하나만 변경
```

### 비교 작업

- [ ] baseline의 prompt/model/retriever 설정을 기록한다.
- [ ] candidate에서 변경한 한 요소를 기록한다.
- [ ] 같은 Golden, metric, threshold, judge로 두 실행을 수행한다.
- [ ] 평균뿐 아니라 각 `case_id`의 regression과 improvement를 비교한다.
- [ ] hard gate 사례가 모두 유지되는지 확인한다.
- [ ] 출력, score, reason, 설정, 시간, 비용을 함께 보관한다.

비교표:

| case_id | baseline 판정/score | candidate 판정/score | delta | hard gate | 결정 |
| --- | --- | --- | ---: | --- | --- |
| refund-normal-001 | pass / 0.82 | pass / 0.91 | +0.09 | no | improvement |
| refund-policy-003 | pass / 0.88 | fail / 0.61 | -0.27 | yes | regression, 변경 차단 |

regression은 모든 작은 score 하락을 뜻하지 않는다. pass에서 fail로 바뀌거나,
hard gate가 깨지거나, 사전에 정한 허용 delta를 넘은 경우처럼 decision rule을
위반한 변화다. 평균 score가 좋아도 critical case 한 건이 나빠지면 candidate를
그대로 채택하지 않는다.

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
   - 정상 완료된 평가의 `QUALITY_FAIL` 중 retriever 또는 generator 계열 실패를 선택한다.
   - `DATA_ERROR`, `EVAL_ERROR`, `NOT_RUN`은 triage 연습 대상이지만 시스템 개선 loop 완료로 세지 않는다.
2. input, reference, retrieval, output, score/reason과 실행 설정을 증거로 보관한다.
3. `retriever`, `generator_grounding`, `answer_composition`, `data/reference`, `unknown` 중 진단 가설과 반증 조건을 적는다.
4. 근거를 확인한 후 prompt 또는 retrieval 설정 등 실제 원인 한 요소만 수정한다.
5. 수정 전 실패와 수정 후 통과의 red→green 결과를 남긴다. 5주차에서 flaky로 분류한 경계 사례라면 고정 output judge 반복 또는 end-to-end 반복으로 안정성을 확인한다.
6. 목표 case, component suite, smoke, full 순서로 실행해 다른 regression을 확인한다.
7. 같은 결함이 재발하지 않게 기존 Golden을 유지하거나 새 production 실패를 reviewed Golden으로 추가한다.

reference가 틀렸다면 제품 개선과 섞지 않는다. 독립적인 정책·사람 검토를 거쳐
dataset version을 올리고 baseline을 다시 수립하는 **평가 데이터 repair**다.
현재 `actual_output`에 맞추기 위해 `expected_output`을 바꾸면 안 된다. 기존
Golden이 이미 결함을 잡았다면 같은 사례를 중복 추가할 필요도 없다.

예를 들어 `retrieval_context`에는 30일 정책이 있는데 `actual_output`이 90일이면
Faithfulness 실패를 근거로 generator grounding 가설을 세울 수 있다. grounding
prompt 하나만 수정한 뒤 수정 전에는 실패하고 수정 후에는 30일을 답하는지
확인한다. 그런 다음 전체 smoke/full에서 새로운 regression이 없는지 본다.

### 최종 재현성 리뷰

- [ ] 다른 사람이 README만 보고 환경을 구성한다.
- [ ] API 없는 deterministic test를 실행한다.
- [ ] secret을 제공한 환경에서 smoke eval을 실행한다.
- [ ] 각 metric이 보호하는 위험을 설명한다.
- [ ] 실패한 `case_id`에서 데이터와 의심 컴포넌트를 찾는다.
- [ ] DeepEval 업그레이드 전 작은 compatibility suite를 실행하는 절차가 있다.

### 운영 handoff에서 남길 것

캡스톤 완료는 실제 production readiness 인증이 아니라, 다른 사람이 모의 gate를
재현하고 실패의 다음 행동을 판단할 수 있다는 뜻이다. 최소한 다음을 runbook에
남긴다.

- suite, metric과 dataset owner 및 실행 주기
- 필요한 secret과 로그에서 보호할 데이터
- 결과 저장 위치와 보관 기간
- 품질 실패, 데이터 오류, API 오류의 triage 담당과 제한 재시도 규칙
- known flaky 격리 목록과 해제 조건
- Golden 승인·폐기와 threshold 재보정 조건
- judge/model/DeepEval 업그레이드 절차
- 비용 예산과 gate override 승인자·사유·만료 조건
- baseline artifact 위치와 owner, candidate 승격 승인 조건과 commit SHA
- 이전 baseline 보관·rollback 방법과 dataset version 변경 시 baseline 재수립 절차

## 6주차 완료 조건

- [ ] smoke 실패가 로컬과 CI에서 non-zero exit code로 연결된다.
- [ ] baseline과 candidate를 같은 조건에서 비교했다.
- [ ] 평가 결과로 실제 시스템을 한 번 개선했다.
- [ ] 기존 regression 사례의 red→green 보호를 확인했거나, 새 production 실패라면 reviewed Golden을 추가했다.
- [ ] 의도적인 품질 실패는 차단되고 API 오류나 미실행은 green으로 표시되지 않는다.
- [ ] 제3자가 runbook으로 실패 원인과 다음 행동을 판단할 수 있다.

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
