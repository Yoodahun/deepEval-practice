"""여러 RAG 평가에서 재사용하는 환불 안내 완전성 metric."""

from __future__ import annotations

from typing import Final

from deepeval.metrics import GEval
from deepeval.test_case import SingleTurnParams


REFUND_COMPLETENESS_CRITERIA: Final = """
Evaluate only whether the actual output contains all decision-relevant and
action-relevant information in the expected output. Treat an answer as
incomplete when it omits or contradicts any required policy condition,
required information, or next action stated in the expected output. Do not
require details that are absent from the expected output. Do not evaluate
tone, writing style, retrieval quality, or factual claims beyond the expected
output.
"""


def make_refund_completeness_metric(
    *, threshold: float = 0.7,
) -> GEval:
    """기대 답변을 기준으로 필수 정보가 완전한지 평가한다."""
    return GEval(
        name="Refund Completeness",
        criteria=REFUND_COMPLETENESS_CRITERIA,
        evaluation_params=[
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.EXPECTED_OUTPUT,
        ],
        threshold=threshold,
        async_mode=False,
    )
