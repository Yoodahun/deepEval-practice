# AGENTS.md

이 문서는 이 저장소에서 작업하는 사람과 코딩 에이전트가 따라야 할 기본 규칙이다. 저장소 전체에 적용하며, 하위 디렉터리에 더 구체적인 `AGENTS.md`가 생기면 해당 범위에서는 하위 문서가 우선한다.

## 저장소의 목적

이 저장소는 DeepEval을 이용해 LLM 애플리케이션 평가를 학습하고 실험하는 교육용 저장소다. 단순히 예제 테스트를 통과시키는 것보다 다음 능력을 단계적으로 익히는 것이 목적이다.

- `LLMTestCase`로 입력, 실제 출력, 기대 결과와 근거를 구분한다.
- 결정적 assertion과 의미 기반 LLM 평가를 구분한다.
- 표준 메트릭과 제품 요구사항용 `GEval`을 적절히 선택한다.
- 필수 RAG 과정에서 retriever와 generator의 실패 원인을 분리하고, 선택 심화에서는
  agent와 대화 품질의 실패 원인을 확장해 다룬다.
- Golden 데이터셋, 임계값 보정, pytest와 CI를 이용해 재현 가능한 회귀 테스트를 만든다.

프로젝트 소개와 실행 방법은 `README.md`, 전체 학습 순서와 진행 상태는 `DEEPEVAL_CURRICULUM.md`, 세션별 상세 학습 내용과 완료 조건은 `curriculum/`의 주차별 문서를 기준으로 한다. 의존성 버전은 `requirements-lock.txt`를 따른다.

## 디렉터리 역할

- `app/`: 평가 대상이 되는 예제 LLM 애플리케이션
- `tests/evals/`: 주차별 실습과 pytest/DeepEval 평가 테스트
- `evals/data/`: Golden, JSON, JSONL 등 평가 데이터
- `evals/metrics/`: 여러 테스트에서 재사용하는 custom metric
- `evals/calibration/`: 사람 라벨, threshold 선정 근거와 보정 결과
- `curriculum/`: 준비 단계, 1~6주차와 선택 심화의 상세 학습 문서

`DEEPEVAL_CURRICULUM.md`는 상세 세션을 중복 작성하지 않고 주차별 문서로 연결하는 인덱스로 유지한다. 기존 구조로 표현할 수 있는 파일을 위해 다른 최상위 디렉터리를 추가하지 않는다. 구조 변경이 필요하면 `README.md`의 프로젝트 구조도 함께 갱신한다.

## 커리큘럼 문서 규칙

주차별 상세 문서는 다음 이름을 사용한다.

```text
curriculum/00_setup.md
curriculum/week{주차}_{주제}.md
curriculum/optional_advanced_tracks.md
```

세부 규칙:

- 루트 `DEEPEVAL_CURRICULUM.md`를 과정 상태와 남은 분량의 단일 원본으로 삼고,
  전체 진행 상태, 주차별 링크, 공통 원칙과 최종 완료 정의만 둔다.
- 각 주차의 학습 목표, 선행 조건, 난이도, 예상 시간, 실습 단계, 권장 파일, 완료 조건과 흔한 실패는 해당 `curriculum/week...md`에 둔다.
- 주차별 문서는 `README.md`와 `DEEPEVAL_CURRICULUM.md` 양쪽에서 찾을 수 있어야 한다.
- 세션 상태를 바꾸면 루트 인덱스, 해당 주차 문서와 `curriculum/README.md`의
  요약을 함께 갱신하고 남은 회차도 다시 계산한다. 세 문서의 상태가 다르면 루트
  인덱스를 기준으로 불일치를 수정한다.
- 실습 파일을 새로 추가하거나 이름을 바꾸면 해당 주차 문서의 권장 파일과 실행 명령을 함께 갱신한다.
- 같은 상세 체크리스트를 루트 인덱스와 주차별 파일에 중복 작성하지 않는다.
- 필수 과정과 선택 심화를 명확히 구분하고, 선택 항목을 필수 완료 조건에 포함하지 않는다.
- 새 문서는 한국어 설명을 기본으로 하며 DeepEval/Python identifier는 원래 영문을 유지한다.
- 과거 기준으로 완료된 세션을 수정하지 않을 때는 기존 완료 상태를 유지할 수 있다.
  그러나 개념, 실습 또는 완료 조건을 실질적으로 변경하면 수정한 세션은 현재
  `AGENTS.md`의 완성 기준으로 다시 검토하고, 증거가 부족하면 `진행 중`으로 둔다.

### 교육자료 공통 완성도 기준

새 세션을 만들거나 기존 세션을 보완할 때는 코드와 TODO부터 작성하지 않는다.
먼저 학습자가 해당 세션 문서만 순서대로 읽어도 아래 질문에 답할 수 있도록
개념 설명을 완성한다.

1. **무엇인가:** 새 개념, 컴포넌트 또는 metric을 처음 등장하는 위치에서 쉬운
   말로 정의하고 입력, 출력, 책임과 인접 개념의 경계를 설명한다.
2. **왜 필요한가:** 이 개념이 해결하는 사용자 위험이나 품질 문제와, 평가하지
   않았을 때 놓치는 실패를 설명한다.
3. **무엇이 만들어지는가:** 선행 세션에서 가져오는 입력 산출물, 이번 세션에서
   새로 만드는 산출물과 다음 세션이 재사용할 결과를 구분한다.
4. **어떻게 수행하는가:** 데이터와 상태의 통제 조건, 작업 순서, 관찰·기록
   방법을 단계별로 설명하고 실행 대상이 있는 세션에만 실행 명령을 제공한다.
5. **어떻게 해석하고 행동하는가:** 대표적인 정상/실패 사례, 결과가 뜻하는 것,
   원문과 근거를 확인하는 방법, 다음 조사·수정·운영 행동을 설명한다.
6. **무엇을 확정할 수 없는가:** 현재 방법의 blind spot, 사람 검토나 다른
   실험이 필요한 범위, 비용·변동성·운영 제약을 설명한다.

추가 규칙:

- 선행 세션에서 다룬 용어라도 현재 세션의 핵심 개념이면 한 문단으로 다시 정의하고
  상세 설명이 있는 위치를 연결한다. 학습자가 이전 내용을 기억한다고 가정한 채
  핵심 정의를 생략하지 않는다.
- 세션 본문은 원칙적으로 `핵심 개념 정의 → 구체 사례와 전체 흐름 → 평가·운영
  설계 → 실습 산출물과 TODO 또는 관찰·리뷰 과제 → 실행 대상이 있으면 명령 →
  결과 해석 → 완료 조건` 순서로 쓴다. 아직 정의하지 않은 용어, field나 도구를
  먼저 사용하게 하지 않는다.
- 최소 한 개의 구체적인 end-to-end 흐름을 먼저 보여 준다. 흐름은 세션에 맞게
  `질문 → 검색 → 답변`, `production sample → 사람 검토 → reviewed Golden`,
  `고정 출력과 사람 라벨 → judge 결과 → FP/FN → threshold`, `commit → suite
  선택 → 실행 상태 → gate 행동`처럼 표현하고, 모든 세션에 generator식
  입력·출력 도식을 억지로 적용하지 않는다.
- 실행 명령과 TODO가 있다는 이유로 수행 방법이 설명됐다고 보지 않는다. 명령 전에
  설계와 통제 조건을, 명령 뒤에는 예상 관찰값, 해석과 다음 행동을 설명한다.
- 핵심 개념과 평가 방법은 `curriculum/` 문서에 둔다. 코드 docstring과 inline
  comment는 이를 가까운 위치에서 보강해야 하며, 문서 설명을 대신할 수 없다.
- `예상 신호`, `설명용 예시`, `실제 실행 결과`를 명시적으로 구분한다. judge,
  workflow 또는 외부 시스템을 실행하지 않았다면 score, reason, pass/fail과 CI
  상태를 실제 관찰 사실처럼 기록하지 않는다.
- 기존 자료를 수정할 때는 요청받은 문장만 국소적으로 덧붙이지 말고, 해당 세션의
  개념 → 구체 흐름 → 수행 방법 → 해석과 행동 → 실습 흐름 전체가 이어지는지
  함께 점검한다.

### 세션 유형별 추가 완성 기준

아래 항목은 해당 유형의 세션에만 적용한다. 관련 없는 세션에 metric, dataset,
threshold 또는 CI 설명을 억지로 추가하지 않는다.

- **metric과 RAG 평가:** 평가할 품질 축과 선택 이유, 제외한 축, required field,
  개념적인 판정·점수 흐름, 높은/낮은 score의 의미와 blind spot을 설명한다. 여러
  metric은 같은 사례를 어떻게 다르게 읽는지와 동시에 실패할 수 있음을 보여 준다.
  낮은 score는 원인 확정이 아니라 첫 조사 가설이며, 수정 전에 원문과 reference,
  runtime observation 및 reason으로 가설을 확인하게 한다.
- **reference와 dataset:** reference의 출처, reviewer, 승인 상태·시점과 version,
  stable `case_id`, provenance, 보호 위험과 중복 여부를 다룬다. runtime output을
  reference로 자동 승격하지 않으며, 개수만 채운 dataset을 완료로 보지 않는다.
  Golden의 정적 reference와 앱 callback의 runtime observation 연결을 예로 든다.
- **RAG 통합과 triage:** 동일 `case_id`에서 input, reference, retrieval,
  generation과 metric evidence가 이어져야 한다. component fixture를 단순히 합치지
  않고 `retriever`, `generator`, `data`, `unknown` 분류의 근거와 반증 조건을
  기록한다. runnable artifact와 좁은 실행 명령이 없으면 완성된 자료로 보지 않는다.
- **calibration과 신뢰도:** judge score를 보기 전에 고정 actual output에 대한 사람
  라벨과 근거를 확정하고 reviewer와 rubric version을 기록한다. calibration split과
  holdout을 분리하고, FP/FN의 positive convention과 오류 비용을 명시하며 holdout에
  반복 과적합하지 않는다. 반복 실험은 앱 output과 설정을 고정하고 judge만 반복하며
  cache 상태, raw case별 score/reason, 변동, 호출량·비용과 오류 상태를 기록한다.
- **suite, CI와 baseline:** suite별 실행 목적과 위험 기반 선택, 로컬/CI 명령의
  일치, secret 처리, exit code와 `PASS`·품질 실패·데이터 오류·API 오류·미실행
  상태를 구분한다. 이전 세션의 상태 분류를 확장하면 old → new 매핑을 설명한다.
  baseline과 candidate는 한 변수만 바꾸고 동일 dataset, judge, metric, threshold와
  version을 사용하며 평균뿐 아니라 case별 regression과 hard gate를 확인한다.
- **캡스톤:** 이전 주차의 canonical 산출물을 조립하고 실제 실패 한 건의
  red → green 개선과 전체 suite의 비회귀 증거를 남긴다. 새 예제 프로젝트를 만들어
  누적 산출물을 우회하지 않는다.
- **선택 심화:** 선택 트랙이라는 이유로 공통 완성 기준을 생략하지 않는다. 선택한
  트랙 하나에만 정의, 데이터 모델, 책임 경계, 대표 사례, 실행과 해석을 갖춘다.

### 누적 산출물과 완료 증거

- 후속 주차는 선행 산출물을 복사한 별도 상수로 재작성하지 않고 canonical dataset,
  reusable metric과 calibration 결정 기록을 import 또는 load해 재사용한다. 세션
  문서에는 재사용하는 입력 산출물과 새 출력 산출물을 명시한다.
- 3주차 Golden에는 정적 reference를 저장하고, 5주차 calibration에는 judge
  변동을 격리하기 위한 고정 `actual_output` snapshot을 별도 artifact로 저장한다.
  calibration snapshot을 reviewed reference나 Golden으로 자동 승격하지 않는다.
- dataset, reference, rubric, metric, judge model 또는 threshold를 변경하면 영향받는
  calibration, baseline과 CI gate를 함께 검토하고 version 변경 여부를 기록한다.
- 세션 `완료`는 다음 세 층이 모두 충족될 때만 표시한다.
  1. 설명: 학습자가 핵심 개념, 책임 경계와 blind spot을 설명할 수 있다.
  2. 산출물: TODO형이면 TODO가 완성되어 있고, 해당 세션의 필수 파일·데이터·결정
     또는 관찰·리뷰 기록이 완성되어 있다.
  3. 증거: 필요한 구조 검사, 대표 실행과 실제 결과 기록이 존재한다.
- API 비용, secret 또는 외부 CI 권한 때문에 완료 조건의 실행을 못 했다면 미실행
  항목과 이유를 기록하고 해당 세션을 `완료`로 표시하지 않는다. `예정` 문서는
  설계 outline일 수 있지만, `진행 중`이나 `완료`로 바꾸기 전에는 권장 파일 존재,
  관찰·리뷰 기록을 확인하고, 실행 가능한 산출물이 있으면 좁은 실행 명령과 검증
  증거도 확인한다.

## 테스트 파일 명명 규칙

새로운 주차별 평가 테스트의 기본 형식은 다음과 같다.

```text
tests/evals/test_week{주차}_session{세션}_{주제}.py
```

예시:

```text
test_week1_session3_metric_methods.py
test_week1_session4_deterministic_vs_semantic.py
test_week2_session1_metric_selection.py
test_week4_session2_rag_faithfulness.py
```

세부 규칙:

- 주차와 세션은 1부터 시작하는 숫자를 사용하고 zero padding은 하지 않는다.
- `{주제}`는 영문 `snake_case`로 작성하고 파일의 핵심 학습 목표나 평가 대상을 나타낸다.
- `test_session5_...`처럼 전체 과정 기준인지 주차 내부 기준인지 불분명한 번호는 새 파일에 사용하지 않는다.
- 하나의 세션을 여러 파일로 나누면 공통 접두사 뒤에 평가 축을 붙인다. 예: `test_week4_session2_rag_retriever.py`, `test_week4_session2_rag_generator.py`.
- 준비 단계처럼 주차/세션 번호가 없는 테스트는 `test_setup_{주제}.py` 형식을 사용한다.
- 준비 단계 테스트에는 `test_setup_...`, 주차별 테스트에는 `test_week..._session...` 접두사를 일관되게 적용한다.

`pytest` 또는 `deepeval test run`이 수집해야 하는 파일만 `test_` 접두사를 사용한다. 보조 파일은 다음처럼 구분한다.

```text
week2_session1_metric_selection_exercise.py  # CLI 전용 실습
week2_session1_metric_selection_solution.py  # 참고 답안
```

참고 답안이나 실행 보조 모듈에는 `test_` 접두사를 붙이지 않아 pytest가 중복 수집하지 않게 한다.

## 테스트 함수와 코드 이름

- 테스트 함수는 `test_{평가대상}_{기대동작}` 형식으로 의도를 드러낸다.
- `test_case1`, `test_example`처럼 실패 원인을 알 수 없는 이름은 피한다.
- 모든 학습용 테스트 함수에는 한국어 docstring을 작성하고, 최소한 다음 두 내용을 명시적으로 구분해 기록한다.
  - `확인 결과`: 이 테스트를 실행하고 통과하거나 실패했을 때 어떤 사실을 확인할 수 있는지 작성한다.
  - `실행 목적`: 해당 사실을 왜 확인해야 하며, 어떤 품질 위험이나 학습 목표와 연결되는지 작성한다.
- docstring은 테스트 구현을 그대로 읽어주는 설명이 아니라, 학습자가 결과의 의미와 테스트의 필요성을 이해할 수 있도록 작성한다.
- parameterize된 테스트는 공통 docstring에 평가 목적을 기록하고, 각 사례는 안정적인 test ID로 어떤 조건을 확인하는지 드러낸다.
- 메트릭 생성 함수는 `make_{품질축}_metric()` 형식을 사용한다.
- 테스트 케이스 생성 함수는 `make_test_case()` 또는 `make_{시나리오}_case()` 형식을 사용한다.
- 여러 시나리오를 parameterize할 때는 리포트에서 바로 식별할 수 있는 안정적인 test ID를 제공한다.
- 환경 변수로 의도적 실패를 켤 때는 `DEEPEVAL_WEEK{주차}_SESSION{세션}_{목적}` 형식을 사용한다.

예시:

```python
def test_refund_answer_is_faithful() -> None:
    """
    확인 결과: 답변의 주장이 검색 근거에 의해 뒷받침되는지 확인한다.
    실행 목적: 근거 없이 생성된 환불 정책이 사용자에게 전달되는 회귀를 방지한다.
    """
    ...


def make_faithfulness_metric() -> FaithfulnessMetric:
    ...
```

### 교육용 테스트 최소화 원칙

- 이 절의 `교육용 검사`는 pytest 함수뿐 아니라 CLI `--check`, 참고 답안의
  validation assertion과 임시 검증 helper를 모두 포함한다.
- 검사를 추가하기 전에 “학습자가 구현한 동작이나 저장소의 지속 계약 중 무엇이
  깨질 때 실패하며, 실패 후 무엇을 수정하는가?”에 답할 수 있어야 한다. DeepEval
  라이브러리 자체나 같은 파일에 직접 쓴 값을 확인하는 것뿐이면 만들지 않는다.
- 학습을 위해 직접 만든 상수, 매핑 또는 설명 문자열을 같은 파일의 예상 literal과
  다시 비교하는 자기검증 테스트를 만들지 않는다. 예를 들어
  `PRIMARY_SIGNAL_BY_FIXTURE`가 작성한 예상 문자열과 같은지, 진단 문장에
  `"grounding"` 같은 단어가 들어 있는지 검사하지 않는다. 이런 내용은 문서,
  주석, 실행 전 기록 질문으로 설명한다.
- metric의 개념적 한계나 blind spot을 학습용 매핑에 대한 assertion으로 증명하지
  않는다. 실제 public API 동작이나 대조 사례로 증명할 수 없다면 테스트가 아니라
  커리큘럼 설명으로 둔다.
- 학습용 dispatcher, helper 또는 타입의 방어 로직은 그 구현 자체가 세션의 학습
  목표이거나 여러 실습에서 재사용되는 실제 계약일 때만 테스트한다. 단일 실습을
  위한 metric key의 unknown 분기처럼 부수적인 커스텀 코드는 테스트하지 않는다.
- inline fixture 문자열에 의도한 단어가 있는지 literal로 다시 검사하지 않는다.
  fixture 무결성 검사는 외부 JSONL 로드, 변환 또는 앱 callback 과정에서 사례의
  결함·ID·reference가 손실될 위험이 있을 때만 둔다.
- metric 클래스 타입, threshold, `include_reason`, `async_mode` 또는 학습용
  required-field 매핑을 그대로 읽어 assert하는 독립 검사를 만들지 않는다.
  learner가 작성한 배선이 대표 `LLMTestCase`의 실제 평가 흐름에 필요하거나,
  버전 업그레이드 시 깨질 공개 API 계약을 작은 compatibility test로 보호할 때만
  검증한다.
- 결정적 검사는 최소 개수로 유지한다. 대표적으로 다음은 허용한다.
  - 외부 로드, 데이터 변환이나 앱 callback으로 drift할 수 있는 비교 실험의 격리 조건
  - 외부 dataset의 schema, provenance, stable ID와 reference/runtime 분리
  - 데이터 변환, callback과 parameterization에서 보존되어야 하는 실제 계약
  - FP/FN, threshold 후보와 상태 전이처럼 코드로 계산하는 실제 결과
  - 평가 대상 앱의 실제 입력·출력 계약
- 하나의 테스트가 학습 목표를 충분히 보호하면 같은 학습용 fixture를 여러
  관점에서 반복 assertion하는 테스트를 추가하지 않는다. pytest 수와 코드량보다
  학습자가 DeepEval의 test case, metric, score와 reason을 직접 다루는 시간을
  우선한다.

## 실습 파일 작성 원칙

- 새 개념은 가능한 한 기존 고객지원 또는 환불 시나리오에 연결해 학습 부담을 줄인다.
- TODO 방식의 코딩 실습에는 서로 다른 학습 단계에 해당하는 명확한 `TODO`를 최소
  3개 남긴다. 학습 목표를 구현하는 데 필요하면 4개 이상으로 늘릴 수 있으며 숫자
  상한은 두지 않되 권장 시간과 세션 범위를 넘기지 않는다. 의미 있는 TODO 세 개가
  나오지 않으면 한 작업을 억지로 분할하지 말고 관찰·리뷰형 실습으로 설계한다.
- 각 TODO는 세션 학습 목표 하나 이상과 연결되고 완료 후 관찰 가능한 결과가 있어야
  한다. 커리큘럼의 TODO 표에는 `구현 대상`, `왜 하는가`, `완료 후 관찰할 것`을
  기록한다.
- 학생용 TODO와 참고 답안은 1:1로 대응한다. 참고 답안에 학생 자료에서 설명하지
  않은 핵심 추상화나 우회 구현을 새로 추가하지 않는다.
- 학습 자료에서 사용하는 기능과 타입은 `DeepEval 공식 제공`, `학습용 커스텀`, `예제 애플리케이션 코드` 중 무엇인지 구분해서 설명한다.
- DeepEval이 직접 제공하지 않고 공식 API로 오인할 수 있는 학습용 `Enum`,
  `dataclass`, Pydantic model, helper class와 공유 추상화에는 선언부 바로 위나 같은
  줄에 최소한 `# 학습용 커스텀: DeepEval 제공 기능 아님` 형태의 inline comment를
  작성한다. 명백한 시나리오 문자열과 단순 상수는 파일 상단의 기능 구분에서 묶어
  설명할 수 있으며 같은 주석을 매번 반복하지 않는다.
- DeepEval 공식 클래스와 이름이 비슷한 커스텀 추상화를 만들지 않는다. 꼭 필요하면 이름에 교육용 또는 저장소 전용임이 드러나게 하고, 공식 API와의 차이를 주석이나 docstring으로 설명한다.
- 한 실습에 커스텀 추상화가 여러 개 등장하면 파일 상단 docstring이나 해당 세션 문서에 공식 DeepEval 기능과 커스텀 학습 장치를 구분한 목록을 제공한다.
- API 없는 검사와 실제 LLM judge 실행이 모두 필요한 경우에는 두 실행을 분리한다.
  분리 형식을 갖추기 위해 불필요한 `--check`나 pytest 테스트를 새로 만들지 않는다.
- 참고 답안은 실습과 같은 디렉터리에 두되 `_solution.py` 접미사를 사용하고 pytest 수집 대상에서 제외한다.
- 의도적인 pass/fail 사례와 실행 명령을 파일 상단 docstring에 기록한다.

## DeepEval 평가 원칙

- 메트릭 이름이 아니라 “점수가 낮으면 어느 컴포넌트·데이터·rubric을 먼저
  조사하고, 수정 전에 어떤 원문과 증거를 확인할 것인가?”를 기준으로 메트릭을
  선택한다. score만으로 원인을 확정하거나 곧바로 코드를 수정하지 않는다.
- JSON 파싱, 필수 key, 타입과 길이처럼 코드로 확정할 수 있는 조건은 일반 pytest assertion으로 먼저 검사한다.
- 의미, 관련성, 근거 충실성처럼 표현 차이를 허용해야 하는 조건만 LLM judge에 맡긴다.
- `context`는 사람이 검토한 정적 ground truth, `retrieval_context`는 retriever가 런타임에 반환한 관측값으로 구분한다.
- `actual_output`은 runtime observation이다. 단, calibration에서는 judge 변동만
  격리하기 위해 별도 snapshot artifact에 고정할 수 있으며 이를 reference로
  취급하지 않는다.
- 한 실행에 연결한 metric 전체와 추적성에 필요한 test-case field를 제공하되,
  사용하지 않는 field를 관성적으로 추가하지 않는다.
- 하나의 `GEval`에 서로 독립적인 품질 요구사항을 과도하게 합치지 않는다.
- 탐색 실습에서는 provisional threshold를 사용할 수 있지만 임시 값임을 표시하고
  release gate에 사용하지 않는다. operational threshold는 사람 라벨, 경계 사례와
  오류 비용으로 보정하고 holdout과 반복성 확인 결과를 기록한다.
- DeepEval API, required field, CLI flag와 metric 판정 흐름을 교육자료에 쓸 때는
  `requirements-lock.txt`의 설치 버전, 로컬 signature/help와 호환되는 공식 문서를
  확인한다. 확인하지 못한 내부 동작은 사실처럼 단정하지 않고 추정임을 표시하며,
  버전 의존 동작은 문서에 기준 버전을 남긴다.

## 실행과 검증

가상환경의 실행 파일을 명시하고 변경한 세션부터 좁게 검증한다.

```bash
# 변경한 세션의 API 없는 검사부터 실행
.venv/bin/python -m pytest \
  tests/evals/test_week{주차}_session{세션}_{주제}.py \
  -k "not judge" -v

# 해당 세션에 judge 실행이 필요할 때만 좁게 실행
.venv/bin/deepeval test run \
  tests/evals/test_week{주차}_session{세션}_{주제}.py -v

# 전체 API 없는 suite는 변경 영향 확인이 필요할 때 실행
.venv/bin/python -m pytest tests/evals -k "not judge" -v
```

작업 검증 시 다음 순서를 따른다.

1. Python 구문 및 import 오류를 확인한다.
2. API 호출이 없는 결정적 테스트를 먼저 실행한다.
3. 변경한 파일 또는 세션만 좁게 실행한다.
4. LLM judge가 필요한 테스트는 API 비용과 점수 변동 가능성을 인지하고 실행한다.
5. 마지막으로 `git diff --check`와 `git status --short`로 변경 범위를 확인한다.

LLM judge 호출이 요청의 핵심이 아니면 검증을 위해 불필요하게 외부 API 비용을 발생시키지 않는다. 실행하지 못한 judge 테스트가 있다면 최종 보고에 명시한다.

## 문서와 보안

- 학습 문서, 주석과 사용자 안내는 기본적으로 한국어로 작성한다.
- Python 클래스, 함수, 필드명처럼 코드 식별자는 원래 영문 명칭을 유지한다.
- 새 실습을 추가하면 해당 `curriculum/week...md`의 세션에서 파일과 실행 명령을 찾을 수 있게 연결한다.
- 주차별 문서를 추가하거나 이름을 바꾸면 `DEEPEVAL_CURRICULUM.md`, `curriculum/README.md`, `README.md`의 링크를 함께 갱신한다.
- 실행 방식이나 프로젝트 구조가 달라지면 `README.md`도 함께 수정한다.
- API 키, 토큰과 실제 사용자 데이터는 소스, 테스트 데이터와 로그에 기록하지 않는다.
- `.env.local` 등 로컬 비밀 파일은 Git 추적 대상에 추가하지 않는다.
