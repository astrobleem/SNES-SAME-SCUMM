from __future__ import annotations

from pathlib import Path
import unittest

from same.capabilities import EngineCapability
from same.engine import EngineHost, Lifecycle
from same.engines import default_registry
from same.errors import EngineCompatibilityError, EngineLifecycleError
from same.profile import load_profile
from same.services import HostServices
from same.video import HostEvidenceBackend, PresentRecord, PresentRequest

ROOT = Path(__file__).resolve().parents[1]


class EngineHostTests(unittest.TestCase):
    def test_video_present_event_is_emitted_after_backend_returns(self) -> None:
        profile = load_profile(ROOT / "examples/profiles/agi_v2_conformance.json")
        services = HostServices.create(profile)
        observed: list[tuple[tuple[tuple[int, int], ...], PresentRequest]] = []
        host_backend = HostEvidenceBackend()

        class OrderingBackend:
            def present(self, request: PresentRequest) -> PresentRecord:
                packets = tuple(
                    (int(packet.service), int(packet.opcode))
                    for packet in services.events.ring.snapshot()
                )
                observed.append((packets, request))
                return host_backend.present(request)

        services.video.backend = OrderingBackend()
        record = services.present()
        self.assertEqual(len(observed), 1)
        self.assertNotIn((1, 17), observed[0][0])
        packets_after = tuple(
            (int(packet.service), int(packet.opcode))
            for packet in services.events.ring.snapshot()
        )
        self.assertEqual(packets_after[-1], (1, 17))
        self.assertEqual(record, services.video.presented[-1])

    def test_registry_contains_independent_engines(self) -> None:
        identifiers = [item.identifier for item in default_registry().descriptors()]
        self.assertEqual(identifiers, ["agi_v2", "scumm_v5"])

    def test_lifecycle_rejects_tick_before_boot(self) -> None:
        profile = load_profile(ROOT / "examples/profiles/agi_v2_conformance.json")
        host = EngineHost(profile, default_registry())
        with self.assertRaises(EngineLifecycleError):
            host.tick()

    def test_missing_capabilities_fail_at_probe(self) -> None:
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        services = HostServices.create(
            profile, capabilities=EngineCapability.INDEXED8_SURFACE
        )
        host = EngineHost(profile, default_registry(), services=services)
        with self.assertRaises(EngineCompatibilityError):
            host.probe()

    def test_scumm_run_save_restore(self) -> None:
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        host = EngineHost(profile, default_registry())
        host.boot()
        for _ in range(3):
            host.tick()
        host.save(1)
        for _ in range(2):
            host.tick()
        self.assertEqual(host.engine.inspect_state()["variables"], {"20": 5})
        host.load(1)
        self.assertEqual(host.engine.inspect_state()["variables"], {"20": 3})
        host.tick()
        self.assertEqual(host.engine.inspect_state()["variables"], {"20": 4})
        self.assertEqual(len(host.services.events.ring), 0)
        host.shutdown()
        self.assertIs(host.lifecycle, Lifecycle.STOPPED)

    def test_agi_run_save_restore(self) -> None:
        profile = load_profile(ROOT / "examples/profiles/agi_v2_conformance.json")
        host = EngineHost(profile, default_registry())
        host.boot()
        host.tick()
        host.tick()
        host.save(0)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["variables"], {"20": 3})
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["variables"], {"20": 2})


if __name__ == "__main__":
    unittest.main()
