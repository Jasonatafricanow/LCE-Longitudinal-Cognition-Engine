"""LEGACY / STANDALONE semantic compilation. Integrated LCE consumes MR-Mem Blocks."""

from lce.semantic.compiler import CompilerResult, SemanticCompiler
from lce.semantic.contracts import (
    SemanticDecision,
    SemanticDecisionProvider,
    SemanticGroup,
)
from lce.semantic.providers import RuleBasedSemanticProvider

__all__ = [
    "CompilerResult",
    "RuleBasedSemanticProvider",
    "SemanticCompiler",
    "SemanticDecision",
    "SemanticDecisionProvider",
    "SemanticGroup",
]
