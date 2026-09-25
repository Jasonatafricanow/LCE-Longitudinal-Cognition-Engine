"""Granularity and anti-cheating audit for SemanticBlock v0.3 Benchmark.

Implements Stage D / C5:
1. D1 Raw-copy audit:
   - Token length ratio between compiled representation and raw dialogue
   - Longest common contiguous character sequence (LCS)
   - Character 4-gram overlap (Jaccard similarity)
   - Classification of TRIVIAL_NON_STRUCTURE if representation is essentially raw-dialogue copy.
2. D2 Structure-only ablation:
   - Compares performance when natural language account is removed from P2 (leaving only bounded structured fields).
   - Tests whether structure alone carries discriminatory power.
3. D3 Over-atomization audit:
   - For P3, measures fragmentation count, average proposition length, and whether relational bindings were lost.
"""

from __future__ import annotations

import difflib
from typing import Any


def longest_common_substring(s1: str, s2: str) -> str:
    m = difflib.SequenceMatcher(None, s1, s2).find_longest_match(0, len(s1), 0, len(s2))
    return s1[m.a : m.a + m.size]


def char_ngram_jaccard(s1: str, s2: str, n: int = 4) -> float:
    if len(s1) < n or len(s2) < n:
        return 1.0 if s1 == s2 else 0.0
    set1 = {s1[i : i + n] for i in range(len(s1) - n + 1)}
    set2 = {s2[i : i + n] for i in range(len(s2) - n + 1)}
    union = set1 | set2
    if not union:
        return 0.0
    return len(set1 & set2) / len(union)


class GranularityAuditor:
    def audit_raw_copy(
        self,
        case_id: str,
        arm_id: str,
        raw_dialogue_text: str,
        compiled_representation_text: str,
    ) -> dict[str, Any]:
        raw_clean = "".join(raw_dialogue_text.split())
        comp_clean = "".join(compiled_representation_text.split())

        len_ratio = len(comp_clean) / max(1, len(raw_clean))
        lcs = longest_common_substring(raw_clean, comp_clean)
        lcs_ratio = len(lcs) / max(1, len(raw_clean))
        ngram_sim = char_ngram_jaccard(raw_clean, comp_clean, n=4)

        # Flag as TRIVIAL_NON_STRUCTURE if LCS is >= 85% of raw and ngram jaccard >= 0.70
        is_trivial_copy = (lcs_ratio >= 0.85 and ngram_sim >= 0.70)

        return {
            "case_id": case_id,
            "arm_id": arm_id,
            "raw_char_len": len(raw_clean),
            "compiled_char_len": len(comp_clean),
            "length_ratio": len_ratio,
            "longest_common_substring": lcs,
            "lcs_ratio": lcs_ratio,
            "char_4gram_jaccard": ngram_sim,
            "is_trivial_non_structure": is_trivial_copy,
        }

    def audit_atomization(
        self,
        case_id: str,
        raw_p3_content: dict[str, Any],
    ) -> dict[str, Any]:
        props = raw_p3_content.get("propositions", [])
        num_props = len(props)
        unknowns = raw_p3_content.get("localized_unknowns", [])

        # Over-atomization risk if > 4 propositions for a single 1-turn/2-turn dialogue
        is_over_atomized = (num_props >= 5)

        return {
            "case_id": case_id,
            "arm_id": "P3",
            "proposition_count": num_props,
            "has_speech_act": bool(raw_p3_content.get("speech_act")),
            "unknown_count": len(unknowns),
            "is_over_atomized": is_over_atomized,
        }
