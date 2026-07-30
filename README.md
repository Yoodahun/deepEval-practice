# DeepEval Practice

DeepEval을 활용해 LLM 애플리케이션의 품질을 체계적으로 평가하는 방법을 학습하고 실험하는 저장소입니다.

LLM의 출력은 표현이 매번 달라질 수 있어 일반적인 문자열 비교만으로 품질을 판단하기 어렵습니다. 이 프로젝트에서는 의미 기반 평가, LLM-as-a-Judge, 임계값 기반 검증을 활용해 답변의 정확성·관련성·충실성뿐 아니라 RAG 검색 결과와 에이전트의 도구 사용까지 테스트하는 방법을 다룹니다.

## 학습 목표

- `LLMTestCase`로 평가 입력, 실제 출력, 기대 결과와 문맥을 구조화합니다.
- `GEval`과 DeepEval 기본 메트릭으로 제품 요구사항을 평가 기준으로 표현합니다.
- `pytest` 및 `assert_test()`를 이용해 LLM 품질 검사를 반복 가능한 회귀 테스트로 만듭니다.
- Golden 데이터셋을 구성하고 사람이 판단한 결과를 기준으로 메트릭과 임계값을 보정합니다.
- RAG의 검색 품질, 답변의 근거 충실성, 에이전트의 도구 호출과 다중 턴 대화를 평가합니다.
- 빠른 PR 검사와 정기 평가를 분리해 신뢰할 수 있는 CI/CD 평가 파이프라인을 설계합니다.

## 핵심 개념

일반적인 소프트웨어 테스트에서 assertion이 실제 값과 기대 값을 비교한다면, DeepEval에서는 metric이 평가 기준에 따라 LLM의 동작을 점수화합니다.

```text
사용자 입력 + 실제 LLM 출력 + 기대 결과/근거
                     ↓
               DeepEval metric
                     ↓
               점수 + 판단 이유
                     ↓
              threshold와 비교
                     ↓
                 통과 / 실패
```

일부 메트릭은 별도의 LLM을 평가자(judge)로 사용합니다. 이때 평가 대상 모델과 평가 모델은 서로 다른 역할을 담당합니다.

- 평가 대상 모델: 사용자 요청에 대한 `actual_output`을 생성합니다.
- 평가 모델: `actual_output`이 정의된 기준을 만족하는지 채점합니다.

## 다루는 평가 영역

- 단일 턴 답변의 정확성, 관련성, 완전성 및 표현 품질
- 기대 답변이나 신뢰 가능한 문맥을 활용한 의미 기반 비교
- RAG retriever의 검색 정확도와 generator의 근거 충실성
- 에이전트의 도구 선택, 인자, 실행 결과 및 작업 완료 여부
- 다중 턴 대화의 일관성, 역할 준수 및 문맥 유지
- 평가 데이터셋 관리, flaky score 대응과 threshold calibration
- pytest 기반 회귀 테스트와 CI 품질 게이트

## 프로젝트 구조

```text
deepEval-practice/
├── app/                         # 평가 대상 예제 LLM 애플리케이션
├── evals/
│   ├── data/                    # Golden 및 평가 데이터셋
│   ├── metrics/                 # 재사용 가능한 custom metric
│   └── calibration/             # 사람 라벨과 임계값 보정 기록
├── tests/
│   └── evals/                   # pytest 기반 DeepEval 테스트
├── curriculum/                  # 준비 단계와 주차별 상세 커리큘럼
│   ├── README.md                 # 문서 사용법과 주차별 탐색
│   ├── 00_setup.md
│   ├── week1_evaluation_foundations.md
│   ├── week2_metrics_and_geval.md
│   ├── week3_dataset_and_regression.md
│   ├── week4_rag_evaluation.md
│   ├── week5_calibration_and_reliability.md
│   ├── week6_ci_and_capstone.md
│   └── optional_advanced_tracks.md
├── DEEPEVAL_CURRICULUM.md       # 전체 진행 현황과 주차별 문서 인덱스
└── requirements-lock.txt        # 고정된 Python 의존성
```

일부 디렉터리는 관련 실습이 진행되면서 채워집니다.

## 시작하기

### 1. 가상환경 생성 및 활성화

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 의존성 설치

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-lock.txt
```

### 3. 평가 모델 API 키 설정

OpenAI 모델을 judge로 사용하는 메트릭을 실행하려면 API 키가 필요합니다.

```bash
export OPENAI_API_KEY="your-api-key"
```

로컬 환경 파일을 사용한다면 `.env.local`에 저장할 수 있습니다.

```dotenv
OPENAI_API_KEY=your-api-key
```

실제 API 키는 Git에 커밋하지 않습니다.

### 4. 평가 실행

```bash
deepeval test run tests/evals -v
```

일반 pytest로도 실행할 수 있습니다.

```bash
pytest tests/evals -v
```

LLM-as-a-Judge 메트릭은 실행할 때 외부 모델 API를 호출하므로 비용이 발생할 수 있으며, 평가 결과에 소폭의 변동이 생길 수 있습니다.

## 기본 예시

```python
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams


correctness = GEval(
    name="Correctness",
    criteria="Determine whether the actual output is correct based on the expected output.",
    evaluation_params=[
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.EXPECTED_OUTPUT,
    ],
    threshold=0.7,
)

test_case = LLMTestCase(
    input="사용자의 질문",
    actual_output="평가 대상 애플리케이션이 생성한 답변",
    expected_output="사람이 검토한 기대 답변",
)

assert_test(test_case, [correctness])
```

`LLMTestCase`는 평가할 데이터를 담고, `GEval`은 평가 기준을 정의하며, `assert_test()`는 산출된 점수가 임계값을 충족하는지 검증합니다.

## 학습 로드맵

[DeepEval 실습 커리큘럼](DEEPEVAL_CURRICULUM.md)은 현재 진행 상태와 전체 학습 순서를 보여주는 인덱스입니다. 세션별 목표, 실습 단계, 권장 파일, 검증 명령과 완료 조건은 [`curriculum/` 주차별 문서](curriculum/README.md)에서 확인할 수 있습니다.

| 구간 | 상세 문서 | 핵심 내용 |
| --- | --- | --- |
| 준비 | [환경과 첫 평가](curriculum/00_setup.md) | 설치, API key, 첫 pass/fail eval |
| 1주차 | [평가의 테스트 모델](curriculum/week1_evaluation_foundations.md) | 평가 계약, test-case field, assertion 분리 |
| 2주차 | [metric과 GEval](curriculum/week2_metrics_and_geval.md) | 표준 metric, custom rubric, reference 전략 |
| 3주차 | [dataset과 regression](curriculum/week3_dataset_and_regression.md) | 최소 앱, Golden, JSONL, pytest |
| 4주차 | [RAG 평가](curriculum/week4_rag_evaluation.md) | end-to-end, retriever, generator 진단 |
| 5주차 | [보정과 신뢰도](curriculum/week5_calibration_and_reliability.md) | 사람 라벨, threshold, flaky와 비용 |
| 6주차 | [CI와 캡스톤](curriculum/week6_ci_and_capstone.md) | smoke/full, CI, 변경 비교, 개선 loop |
| 선택 | [고급 트랙](curriculum/optional_advanced_tracks.md) | tracing, Agent, multi-turn, SDET 응용 |

필수 심화 과정은 환불 고객지원 RAG 하나로 진행합니다. Agent, multi-turn과 tracing은 필수 캡스톤 이후 관심에 따라 하나만 선택합니다.

## 보안

- API 키와 토큰은 환경 변수나 Git에서 제외된 로컬 설정 파일로 관리합니다.
- 실제 사용자 데이터는 평가 데이터셋에 추가하기 전에 익명화합니다.
- 공개 저장소에 노출된 키는 파일에서 삭제하는 것만으로 충분하지 않으므로 즉시 폐기하고 재발급합니다.

## 참고 자료

- [DeepEval 공식 문서](https://deepeval.com/docs/getting-started)
- [DeepEval GitHub](https://github.com/confident-ai/deepeval)
