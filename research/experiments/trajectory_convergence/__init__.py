"""Experimental trajectory-convergence research helpers."""

from .experiment import (
    CandidateSignal,
    ConvergenceConfig,
    ConvergenceDecision,
    SupportProfile,
    evaluate_convergence,
)

__all__ = [
    "CandidateSignal",
    "ConvergenceConfig",
    "ConvergenceDecision",
    "SupportProfile",
    "evaluate_convergence",
]
