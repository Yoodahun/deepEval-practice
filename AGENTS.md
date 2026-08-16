# AGENTS.md

이 문서는 이 저장소에서 작업하는 사람과 코딩 에이전트가 따라야 할 기본 규칙이다. 저장소 전체에 적용하며, 하위 디렉터리에 더 구체적인 `AGENTS.md`가 생기면 해당 범위에서는 하위 문서가 우선한다.

## 저장소의 목적

이 저장소는 DeepEval을 이용해 LLM 애플리케이션 평가를 학습하고 실험하는 교육용 저장소다. 단순히 예제 테스트를 통과시키는 것보다 다음 능력을 단계적으로 익히는 것이 목적이다.

- `LLMTestCase`로 입력, 실제 출력, 기대 결과와 근거를 구분한다.
- 결정적 assertion과 의미 기반 LLM 평가를 구분한다.
- 표준 메트릭과 제품 요구사항용 `GEval`을 적절히 선택한다.
- RAG retriever, generator, agent와 대화 품질의 실패 원인을 분리한다.
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

- 루트 `DEEPEVAL_CURRICULUM.md`에는 전체 진행 상태, 주차별 링크, 공통 원칙과 최종 완료 정의만 둔다.
- 각 주차의 학습 목표, 선행 조건, 난이도, 예상 시간, 실습 단계, 권장 파일, 완료 조건과 흔한 실패는 해당 `curriculum/week...md`에 둔다.
- 주차별 문서는 `README.md`와 `DEEPEVAL_CURRICULUM.md` 양쪽에서 찾을 수 있어야 한다.
- 세션 상태를 바꾸면 루트 인덱스의 상태 표와 해당 주차 문서를 함께 갱신한다.
- 실습 파일을 새로 추가하거나 이름을 바꾸면 해당 주차 문서의 권장 파일과 실행 명령을 함께 갱신한다.
- 같은 상세 체크리스트를 루트 인덱스와 주차별 파일에 중복 작성하지 않는다.
- 필수 과정과 선택 심화를 명확히 구분하고, 선택 항목을 필수 완료 조건에 포함하지 않는다.
- 새 문서는 한국어 설명을 기본으로 하며 DeepEval/Python identifier는 원래 영문을 유지한다.

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

## 실습 파일 작성 원칙

- 새 개념은 가능한 한 기존 고객지원 또는 환불 시나리오에 연결해 학습 부담을 줄인다.
- 사용자가 직접 코딩하는 실습은 완성 코드 전체를 주기보다 2~4개의 명확한 `TODO`를 남긴다.
- TODO는 메트릭 선택, required field 구성, rubric 작성처럼 해당 세션의 학습 목표와 직접 관련되어야 한다.
- 학습 자료에서 사용하는 기능과 타입은 `DeepEval 공식 제공`, `학습용 커스텀`, `예제 애플리케이션 코드` 중 무엇인지 구분해서 설명한다.
- DeepEval이 직접 제공하지 않는 학습용 `Enum`, `dataclass`, Pydantic model, helper class, fixture model, 상수와 매핑에는 선언부 바로 위나 같은 줄에 최소한 `# 학습용 커스텀: DeepEval 제공 기능 아님` 형태의 inline comment를 작성한다.
- DeepEval 공식 클래스와 이름이 비슷한 커스텀 추상화를 만들지 않는다. 꼭 필요하면 이름에 교육용 또는 저장소 전용임이 드러나게 하고, 공식 API와의 차이를 주석이나 docstring으로 설명한다.
- 한 실습에 커스텀 추상화가 여러 개 등장하면 파일 상단 docstring이나 해당 세션 문서에 공식 DeepEval 기능과 커스텀 학습 장치를 구분한 목록을 제공한다.
- API를 호출하지 않는 구조 검사와 실제 LLM judge 실행을 가능하면 분리한다.
- 참고 답안은 실습과 같은 디렉터리에 두되 `_solution.py` 접미사를 사용하고 pytest 수집 대상에서 제외한다.
- 의도적인 pass/fail 사례와 실행 명령을 파일 상단 docstring에 기록한다.

## DeepEval 평가 원칙

- 메트릭 이름이 아니라 “점수가 낮으면 어느 컴포넌트를 고칠 것인가?”를 기준으로 메트릭을 선택한다.
- JSON 파싱, 필수 key, 타입과 길이처럼 코드로 확정할 수 있는 조건은 일반 pytest assertion으로 먼저 검사한다.
- 의미, 관련성, 근거 충실성처럼 표현 차이를 허용해야 하는 조건만 LLM judge에 맡긴다.
- `context`는 사람이 검토한 정적 ground truth, `retrieval_context`는 retriever가 런타임에 반환한 관측값으로 구분한다.
- 메트릭의 required test-case fields를 확인하고 필요한 필드만 정확히 제공한다.
- 하나의 `GEval`에 서로 독립적인 품질 요구사항을 과도하게 합치지 않는다.
- threshold는 임의의 보기 좋은 숫자가 아니라 사람 라벨과 경계 사례를 이용해 보정한다.

## 실행과 검증

가상환경의 실행 파일을 명시적으로 사용하는 것을 권장한다.

```bash
.venv/bin/python -m pytest tests/evals -v
.venv/bin/deepeval test run tests/evals -v
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
