"""Compiler adapters for Issue #19 A/B/C/D benchmark."""

from research.benchmarks.semantic_block_v0_1.adapters.base import (
    BaseCompilerAdapter,
    prepare_visible_input,
)
from research.benchmarks.semantic_block_v0_1.adapters.arm_a_v1 import ArmAV1Adapter
from research.benchmarks.semantic_block_v0_1.adapters.arm_b_one_pass import ArmBOnePassAdapter
from research.benchmarks.semantic_block_v0_1.adapters.arm_c_recom import ArmCRecommendedAdapter
from research.benchmarks.semantic_block_v0_1.adapters.arm_d_frame import ArmDFullFrameAdapter

__all__ = [
    "BaseCompilerAdapter",
    "prepare_visible_input",
    "ArmAV1Adapter",
    "ArmBOnePassAdapter",
    "ArmCRecommendedAdapter",
    "ArmDFullFrameAdapter",
]
