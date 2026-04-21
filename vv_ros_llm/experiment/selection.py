from __future__ import annotations
from vv_ros_llm.schemas import VerificationResult


def select_best(results: list[VerificationResult]) -> VerificationResult | None:
    """Pick the best verification result by (overall_pass, #passed methods, avg score)."""
    if not results:
        return None

    def key(v: VerificationResult):
        n_passed = sum(1 for m in v.methods if m.passed)
        scores = [m.score for m in v.methods if m.score is not None]
        avg = sum(scores) / len(scores) if scores else 0.0
        return (int(v.overall_pass), n_passed, avg)

    return max(results, key=key)
