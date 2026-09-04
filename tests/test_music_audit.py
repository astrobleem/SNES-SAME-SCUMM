from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from same.music import SequenceAuditError, decode_sequence_audit
from same.music import load_profile_music_graph
from same.profile import load_profile


ROOT = Path(__file__).resolve().parents[1]


def _audit_fixture():
    from music_graph_adapters import default_music_graph_adapters

    profile = load_profile(
        ROOT / "examples/profiles/qtma_music_time_runtime_conformance.json",
        verify_resources=False,
    )
    graph = load_profile_music_graph(
        profile, dependency_reader=lambda path: (ROOT / path).read_bytes(),
    )
    registration = default_music_graph_adapters().resolve(
        profile.engine_id, graph.adapter,
    )
    adapter = registration.factory(None, graph)
    node = graph.nodes[0]
    adapter.render(node, adapter.read_source(node))
    return graph, node, adapter, adapter.audit(node)


class MusicSequenceAuditTests(unittest.TestCase):
    def test_strict_decode_reconstructs_normalized_ir_and_timing(self) -> None:
        graph, node, _adapter, raw = _audit_fixture()
        decoded = decode_sequence_audit(raw)
        self.assertEqual(decoded.imported.source_time_scale, 600)
        self.assertEqual(decoded.normalized.source_time_scale, graph.time_scale)
        self.assertEqual(decoded.normalized.end_tick, node.duration)
        self.assertEqual(
            (decoded.timing.max_error_numerator,
             decoded.timing.error_denominator),
            (300, 600),
        )
        self.assertEqual(
            [note.zone_name for note in decoded.realization],
            ["qtma_drum", "qtma_marimba", "qtma_marimba", "qtma_marimba"],
        )

    def test_schema_order_timing_and_realization_corruption_fail_closed(self) -> None:
        _graph, node, adapter, raw = _audit_fixture()
        original = json.loads(raw)

        changed = copy.deepcopy(original)
        changed["unexpected"] = 1
        with self.assertRaises(SequenceAuditError) as caught:
            decode_sequence_audit(json.dumps(changed).encode())
        self.assertEqual(caught.exception.code, "invalid_fields")

        changed = copy.deepcopy(original)
        changed["normalized"]["events"][5]["tick"] += 1
        with self.assertRaises(SequenceAuditError) as caught:
            decode_sequence_audit(json.dumps(changed).encode())
        self.assertIn(caught.exception.code, ("invalid_sequence", "timing_mismatch"))

        changed = copy.deepcopy(original)
        changed["normalized"]["events"][5:7] = reversed(
            changed["normalized"]["events"][5:7]
        )
        with self.assertRaises(SequenceAuditError):
            decode_sequence_audit(json.dumps(changed).encode())

        changed = copy.deepcopy(original)
        changed["normalized"]["events"][0]["provenance"]["byte_offset"] = -1
        with self.assertRaises(SequenceAuditError) as caught:
            decode_sequence_audit(json.dumps(changed).encode())
        self.assertEqual(caught.exception.code, "invalid_provenance")

        changed = copy.deepcopy(original)
        changed["realization"][0]["zone_name"] = "wrong_zone"
        with self.assertRaisesRegex(ValueError, "realization differs"):
            adapter.replay_audit(node, json.dumps(changed).encode())


if __name__ == "__main__":
    unittest.main()
