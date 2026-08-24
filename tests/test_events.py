from __future__ import annotations

import unittest

from same.abi import Packet, PacketFlag, Service, KernelOpcode
from same.errors import QueueFullError
from same.events import EventBus, EventRing


class EventTests(unittest.TestCase):
    def packet(self, sequence: int = 0, flags: int = 0) -> Packet:
        return Packet(
            service=Service.KERNEL,
            opcode=KernelOpcode.HEARTBEAT,
            sequence=sequence,
            flags=flags,
            arg0=sequence,
        )

    def test_fifo_wraparound(self) -> None:
        ring = EventRing(3)
        ring.push(self.packet(1))
        ring.push(self.packet(2))
        self.assertEqual(ring.pop().arg0, 1)
        ring.push(self.packet(3))
        ring.push(self.packet(4))
        self.assertEqual([packet.arg0 for packet in ring.drain()], [2, 3, 4])
        self.assertEqual(ring.stats.high_water, 3)

    def test_required_overflow_fails_closed(self) -> None:
        ring = EventRing(1)
        ring.push(self.packet())
        with self.assertRaises(QueueFullError):
            ring.push(self.packet(1))
        self.assertEqual(ring.stats.rejected, 1)

    def test_drop_ok_overflow_is_counted(self) -> None:
        ring = EventRing(1)
        ring.push(self.packet())
        accepted = ring.push(self.packet(1, PacketFlag.DROP_OK))
        self.assertFalse(accepted)
        self.assertEqual(ring.stats.dropped, 1)

    def test_bus_numbers_only_accepted_packets(self) -> None:
        bus = EventBus(1)
        first = bus.emit(service=Service.KERNEL, opcode=KernelOpcode.HEARTBEAT)
        self.assertEqual(first.sequence, 0)
        with self.assertRaises(QueueFullError):
            bus.emit(service=Service.KERNEL, opcode=KernelOpcode.HEARTBEAT)
        self.assertEqual(bus.next_sequence, 1)


if __name__ == "__main__":
    unittest.main()
