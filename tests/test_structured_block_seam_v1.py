from dataclasses import replace

import pytest
from mr_mem.point_runtime import SemanticPoint
from mr_mem.semantic_units import parse_units

from lce.integrations.mr_mem import map_canonical_semantic_block
from lce.integrations.mr_mem_runtime import MrMemProjectionRuntime
from tests.test_mr_mem_mapping import canonical_view


def test_public_block_structure_and_point_rejection(tmp_path):
    units = parse_units([{"predicate": "evaluate", "roles": {"actor": "user", "target": "B"},
                          "force": "question", "qualifiers": [
                              {"on": "unit", "kind": "scope", "value": "cost only"}],
                          "relations": [{"relation": "about", "target": 1}]},
                         {"predicate": "cost"}])
    view = replace(canonical_view(), units=units, unit_source_indices=((0,), (0,)))
    result = map_canonical_semantic_block(view, lineage_id="test")
    assert result.block.metadata["semantic_units"][0] == units[0].wire()
    with pytest.raises(TypeError, match="CanonicalSemanticBlockView"):
        map_canonical_semantic_block(SemanticPoint(units), lineage_id="test")
    runtime = MrMemProjectionRuntime(tmp_path, scope=view.scope)
    try:
        runtime.project_canonical_semantic_block(view)
        stored = runtime.projected.get_semantic_block(view.memory_id)
        assert stored.metadata["semantic_units"][0]["roles"] == {"actor": "user", "target": "B"}
        assert stored.metadata["semantic_units"][0]["force"] == "question"
        with pytest.raises(TypeError, match="Point"):
            runtime.project_canonical_semantic_block(SemanticPoint(units))
    finally:
        runtime.close()
    restarted = MrMemProjectionRuntime(tmp_path, scope=view.scope)
    try:
        assert restarted.project_canonical_semantic_block(view).receipt.replayed
        stored = restarted.projected.get_semantic_block(view.memory_id)
        assert stored.metadata["semantic_units"][0]["relations"][0]["relation"] == "about"
    finally:
        restarted.close()
