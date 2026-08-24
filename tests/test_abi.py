from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from same.abi import (
    ABI_REVISION,
    PACKET_SIZE,
    Endpoint,
    Packet,
    PacketFlag,
    Service,
    VideoOpcode,
    generate_poppy_include,
    packet_stream,
    unpack_packet_stream,
)
from same.errors import AbiError


class AbiTests(unittest.TestCase):
    def test_packet_is_exactly_sixteen_bytes_and_roundtrips(self) -> None:
        packet = Packet(
            service=Service.VIDEO,
            opcode=VideoOpcode.SET_BACKDROP,
            flags=PacketFlag.ACK_REQUEST,
            source=Endpoint.SA1,
            destination=Endpoint.SCPU,
            sequence=0x1234,
            arg0=0x89ABCDEF,
            arg1=0x10203040,
        )
        raw = packet.pack()
        self.assertEqual(len(raw), PACKET_SIZE)
        self.assertEqual(Packet.unpack(raw), packet)
        self.assertEqual(packet.service_name, "VIDEO")
        self.assertEqual(packet.opcode_name, "SET_BACKDROP")

    def test_stream_roundtrip(self) -> None:
        packets = [
            Packet(service=Service.VIDEO, opcode=VideoOpcode.BEGIN_FRAME, sequence=i)
            for i in range(4)
        ]
        self.assertEqual(unpack_packet_stream(packet_stream(packets)), packets)

    def test_unknown_opcode_is_rejected(self) -> None:
        with self.assertRaises(AbiError):
            Packet(service=Service.VIDEO, opcode=0xFF)

    def test_wrong_length_is_rejected(self) -> None:
        with self.assertRaises(AbiError):
            Packet.unpack(b"\0" * 15)

    def test_poppy_include_contains_offsets_and_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "abi.inc.pasm"
            generate_poppy_include(path)
            text = path.read_text()
            self.assertIn(f"SAME_ABI_REVISION", text)
            self.assertIn("SAME_PACKET_SIZE", text)
            self.assertIn("SAME_PKT_ARG1", text)
            self.assertIn("SAME_VIDEO_OP_SET_BACKDROP", text)
            self.assertIn(f"${ABI_REVISION:02X}", text)


if __name__ == "__main__":
    unittest.main()
