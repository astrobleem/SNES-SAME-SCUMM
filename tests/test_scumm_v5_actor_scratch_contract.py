from __future__ import annotations

import unittest
import zlib

from tools.scratch_contract import Busy, Owner, Phase, Scratch


class ActorScratchContractTests(unittest.TestCase):
    def test_actor_ticket_requires_idle_room_provider_and_free_owner(self) -> None:
        scratch = Scratch()
        data = b"pose"
        ticket = scratch.request_actor(
            room_epoch=4, costume_epoch=9, length=len(data),
            crc32=zlib.crc32(data) & 0xFFFFFFFF,
            provider_idle=True, room_idle=True,
        )
        self.assertEqual((scratch.owner, scratch.phase), (Owner.ACTOR, Phase.READING))
        with self.assertRaises(Busy):
            scratch.request_actor(room_epoch=4, costume_epoch=10, length=1,
                                  crc32=0, provider_idle=True, room_idle=True)
        self.assertTrue(scratch.complete_actor(
            ticket, data, current_room_epoch=4, current_costume_epoch=9))
        self.assertEqual(scratch.phase, Phase.READY)

    def test_room_priority_drains_inflight_actor_then_claims(self) -> None:
        scratch = Scratch()
        body = b"pose"
        ticket = scratch.request_actor(
            room_epoch=2, costume_epoch=3, length=len(body),
            crc32=zlib.crc32(body) & 0xFFFFFFFF,
            provider_idle=True, room_idle=True,
        )
        self.assertFalse(scratch.request_room())
        self.assertFalse(scratch.complete_actor(
            ticket, body, current_room_epoch=2, current_costume_epoch=3))
        self.assertEqual(scratch.owner, Owner.NONE)
        scratch.claim_room()
        self.assertEqual(scratch.owner, Owner.ROOM)
        scratch.release_room()
        self.assertFalse(scratch.room_requested)

    def test_ready_actor_data_waits_for_surface_before_release(self) -> None:
        scratch = Scratch()
        body = b"checked"
        ticket = scratch.request_actor(
            room_epoch=1, costume_epoch=2, length=len(body),
            crc32=zlib.crc32(body) & 0xFFFFFFFF,
            provider_idle=True, room_idle=True,
        )
        self.assertTrue(scratch.complete_actor(
            ticket, body, current_room_epoch=1, current_costume_epoch=2))
        self.assertIsNone(scratch.consume_actor(ticket, surface_writable=False))
        self.assertEqual(scratch.owner, Owner.ACTOR)
        self.assertEqual(scratch.consume_actor(ticket, surface_writable=True), body)
        self.assertEqual(scratch.owner, Owner.NONE)

    def test_stale_ticket_and_crc_are_rejected(self) -> None:
        scratch = Scratch()
        body = b"data"
        ticket = scratch.request_actor(
            room_epoch=1, costume_epoch=2, length=len(body),
            crc32=zlib.crc32(body) & 0xFFFFFFFF,
            provider_idle=True, room_idle=True,
        )
        self.assertFalse(scratch.complete_actor(
            ticket, b"bad!", current_room_epoch=1, current_costume_epoch=2))
        self.assertEqual(scratch.owner, Owner.NONE)


if __name__ == "__main__":
    unittest.main()
