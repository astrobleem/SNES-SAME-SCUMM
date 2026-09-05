from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json
import unittest

from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5.engine import (
    ActorState,
    PrintMessageState,
    PrintSlotState,
    RoomObjectState,
    ScriptSlot,
)
from same.engines.scumm_v5.room import ScummV5RoomObject, ScummV5Walkbox
from same.errors import EngineExecutionError, SaveFormatError
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices
from same.video import HostEvidenceBackend, PresentRecord, PresentRequest, Rect

ROOT = Path(__file__).resolve().parents[1]
ROOM = (ROOT / "examples/resources/scumm_v5/room0.sc5r").read_bytes()


class ScummV5EngineTests(unittest.TestCase):
    def test_headless_fixture_retains_logical_message_lifetime_without_presentation(self) -> None:
        runtime = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
        talk_runtime = (ROOT / "runtime/snes/engines/scumm_v5_matrix_far.pasm").read_text()
        fixture = runtime.split("ScummV5_Op_Print__text_done:", 1)[1]
        fixture = fixture.split("ScummV5_Op_Print__text_no_talk:", 1)[0]
        self.assertNotIn("SAME_SCUMM_C23_MESSAGE_COUNT", fixture.split(".if SAME_BUILD_SCUMM_M23A", 1)[0])
        self.assertIn("ScummV5_Talk_Begin_Far", fixture)
        self.assertIn("ScummV5_Talk_FrameBegin_Far", talk_runtime)
        self.assertIn("ScummV5_Talk_FrameEnd_Far", talk_runtime)
        self.assertIn("headless fixture may decode", talk_runtime)
        self.assertIn("SAME_SCUMM_TALK_RAW_LENGTH", talk_runtime)
        self.assertIn("SAME_SCUMM_TALK_HAVE_MSG", talk_runtime)

    def test_scheduler_saves_the_selected_slot_after_nested_execution(self) -> None:
        runtime = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
        scheduler = runtime.split("ScummV5_C4_Scheduler_Frame:", 1)[1]
        scheduler = scheduler.split("ScummV5_C4_Scheduler_Frame__advance:", 1)[0]
        self.assertIn("jsr ScummV5_Engine_RunSelected", scheduler)
        self.assertIn("lda.l SAME_SCUMM_C4_SCHED_SLOT", scheduler)
        self.assertIn("sta.l SAME_SCUMM_C4_CURRENT_SLOT", scheduler)

        # Headless means presentation is optional; the existing talk lifecycle
        # still owns delay, waitForMessage completion, continuation, and clear
        # ordering.  The production path must remain the same lifecycle.
        self.assertIn("ScummV5_Talk_Begin_Far", runtime)
        talk_path = runtime.split(".if SAME_BUILD_SCUMM_M23A", 1)[1]
        self.assertIn("ScummV5_Talk_Begin_Far", talk_path)

    def test_scenario_class_overlay_uses_far_c16_lookup(self) -> None:
        generator = (ROOT / "tools/generate_snes_cooked_rooms.py").read_text()
        runtime = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()

        self.assertIn('"    jsl ScummV5_C16_FindRecord_Far"', generator)
        self.assertNotIn(
            '"    sta.l SAME_SCUMM_C16_OBJECT", "    jsr ScummV5_C16_FindRecord"',
            generator,
        )
        self.assertIn(
            "ScummV5_C16_FindRecord_Far:\n"
            "    jsr ScummV5_C16_FindRecord\n"
            "    rtl",
            runtime,
        )

    def test_generated_next_box_entry_follows_overlay_helpers(self) -> None:
        generator = (ROOT / "tools/generate_snes_cooked_rooms.py").read_text()

        # The route entry must not prefix the class/bit helper bodies.  A JSL
        # to NextBox otherwise executes those unrelated helpers and can RTL
        # before consulting the route table.
        bit_done = generator.index(
            '"ScummV5_Bit_ApplyScenarioOverlay_Far__done:"'
        )
        next_box = generator.index('"ScummV5_Movement_NextBox_Far:"')
        route_dispatch = generator.index(
            'f"    cmp #${index:02X}", f"    beq ScummV5_Movement_NextBox_Far__match_{index}"'
        )
        self.assertLess(bit_done, next_box)
        self.assertLess(next_box, route_dispatch)

    def test_movement_direction_conversion_establishes_word_width(self) -> None:
        runtime = (
            ROOT / "runtime/snes/engines/scumm_v5_matrix_far.pasm"
        ).read_text()
        body = runtime.split("ScummV5_Movement_OldToNewDir_Far:\n", 1)[1]
        body = body.split("ScummV5_GetActorWalkbox_FarEntry:", 1)[0]

        # The helper is called after reading an 8-bit actor direction.  A
        # source-only .a16 annotation is insufficient: without REP, AND/CMP
        # consume one-byte immediates and execute their high bytes as opcodes.
        self.assertIn(
            "    ; ABI: accepts the old direction with either M width and returns its\n"
            "    ; canonical 16-bit direction in A with M=16.  It deliberately does not\n"
            "    ; preserve P: callers consume a word result (UpdateActor immediately\n"
            "    ; establishes REP #$30 before storing it).  Establish the word contract\n"
            "    ; in the emitted instruction stream before using word immediates;\n"
            "    ; assembler width annotations alone do not change the 65816 M flag.\n"
            "    rep #$20\n"
            "    .a16\n"
            "    and #$03\n",
            body,
        )

        # This helper's ABI intentionally returns M=16.  The byte-oriented
        # caller explicitly establishes its word A/X contract again before
        # consuming the converted facing; changing either side would recreate
        # the historic high-immediate-byte-as-BRK failure.
        update = runtime.split("ScummV5_Movement_UpdateActor_Far__after_step:\n", 1)[1]
        update = update.split("ScummV5_Movement_ClampPosition_Far__done:", 1)[0]
        self.assertIn(
            "    jsr ScummV5_Movement_OldToNewDir_Far\n"
            "    rep #$30\n"
            "    .a16\n"
            "    .i16\n"
            "    sta.l SAME_SCUMM_MOVE_TEMP\n",
            update,
        )

        walk = runtime.split("ScummV5_Movement_WalkStep_Far:\n", 1)[1]
        walk = walk.split("ScummV5_Movement_LoadScaleX_Far:", 1)[0]
        # The actor-1 diagnostic temporarily selects M=8.  The production
        # X commit must restore M=16 before using the 16-bit position and
        # fixed-point fields, or crossing $00FF truncates the high byte.
        self.assertIn(
            "ScummV5_Movement_WalkStep_Far__product_no_probe:\n"
            "    plx\n"
            "    ; The actor probe above is byte-oriented and leaves M=8 on both the\n"
            "    ; taken and not-taken paths.  Re-establish the word ABI before the\n"
            "    ; fixed-point fraction/position arithmetic; otherwise a 16-bit X\n"
            "    ; coordinate crossing $00FF stores only its low byte and never reaches\n"
            "    ; the authored portal target.\n"
            "    rep #$20\n"
            "    .a16\n"
            "    lda.l SAME_SCUMM_MOVE_TEMP\n",
            walk,
        )

    def _host(
        self,
        script: bytes,
        *,
        max_ops: int | None = None,
        scripts: dict[int, bytes] | None = None,
        resources: dict[str, bytes] | None = None,
        include_room_zero: bool = True,
    ) -> EngineHost:
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        if max_ops is not None:
            profile = replace(profile, max_ops_per_tick=max_ops)
        payloads = {"script.boot": script}
        kinds = {"script.boot": "SCRP"}
        if include_room_zero:
            payloads["room.0"] = ROOM
            kinds["room.0"] = "ROOM"
        for number, program in (scripts or {}).items():
            payloads[f"script.{number}"] = program
            kinds[f"script.{number}"] = "SCRP"
        for key, data in (resources or {}).items():
            payloads[key] = data
            kinds[key] = "DATA"
        resources = MemoryResourceProvider(payloads, kinds=kinds)
        services = HostServices.create(profile, resources=resources)
        host = EngineHost(profile, default_registry(), services=services)
        host.boot()
        return host

    def test_bundled_real_opcode_loop(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/boot.scrp").read_bytes()
        host = self._host(script)
        for _ in range(5):
            host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["variables"], {"20": 5})
        self.assertEqual(state["room"], 0)
        self.assertEqual(host.services.audio.music_track, 1)

    def test_c22_room_zero_is_a_resource_less_null_scene_and_saves(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c22_null_room.scrp").read_bytes()
        host = self._host(
            script,
            resources={"room.1": ROOM},
            include_room_zero=False,
        )

        host.tick()
        self.assertEqual(host.engine.inspect_state()["room"], 0)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["room"], 1)
        host.engine.state.room_objects[100] = RoomObjectState(100, 8, 16, 24, 32, 40, 48, 1)
        host.engine.state.object_states[100] = 1
        host.engine.state.object_draw_queue.append(100)

        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["room"], 0)
        self.assertIsNone(state["video"])
        self.assertEqual(state["room_objects"], {})
        self.assertEqual(state["object_draw_queue"], [])
        self.assertEqual(state["object_states"], {"100": 1})
        self.assertEqual(set(host.services.video.surface.pixels), {0})

        saved = host.save(0)
        host.engine.state.current_room = 77
        host.engine.state.room_objects[101] = RoomObjectState(101, 0, 0, 8, 8, 0, 0)
        host.load(0)
        restored = host.engine.inspect_state()
        self.assertEqual(restored["room"], 0)
        self.assertIsNone(restored["video"])
        self.assertEqual(restored["room_objects"], {})

    def test_c22_missing_nonzero_room_still_fails_closed(self) -> None:
        host = self._host(bytes((0x72, 2)), include_room_zero=False)
        with self.assertRaisesRegex(EngineExecutionError, "room 2 has no resource binding"):
            host.tick()

    def test_get_dist_opcode_modes_metric_resolution_projection_and_purity(self) -> None:
        def configure(host: EngineHost) -> None:
            host.engine.state.actors[1] = ActorState(room=0, position=(1, 1))
            host.engine.state.actors[2] = ActorState(room=0, position=(6, 9))
            host.engine.state.variables[3] = 1
            host.engine.state.variables[4] = 2

        cases = (
            (bytes((0x34, 0, 0, 1, 0, 2, 0)), 7),
            (bytes((0x74, 0, 0, 1, 0, 4, 0)), 7),
            (bytes((0xB4, 0, 0, 3, 0, 2, 0)), 7),
            (bytes((0xF4, 0, 0, 3, 0, 4, 0)), 7),
        )
        for script, expected_pc in cases:
            with self.subTest(opcode=script[0]):
                host = self._host(script)
                configure(host)
                before = {key: value.to_dict() for key, value in host.engine.state.actors.items()}
                host.tick()
                self.assertEqual(host.engine.state.variables[0], 8)
                self.assertEqual(host.engine.inspect_state()["scripts"][0]["pc"], expected_pc)
                self.assertEqual(
                    {key: value.to_dict() for key, value in host.engine.state.actors.items()},
                    before,
                )

        host = self._host(bytes((
            0x34, 0, 0, 1, 0, 2, 0,
            0x34, 1, 0, 1, 0, 3, 0,
        )))
        host.engine.state.actors[1] = ActorState(room=0, position=(1, 1))
        host.engine.state.actors[2] = ActorState(room=0, position=(6, 1))
        host.engine.state.actors[3] = ActorState(room=0, position=(1, 9))
        host.tick()
        self.assertEqual([host.engine.state.variables[0], host.engine.state.variables[1]], [5, 8])

        host = self._host(bytes((
            0x34, 0, 0, 1, 0, 1, 0,       # same actor -> 0
            0x34, 1, 0, 1, 0, 2, 0,       # diagonal max(5,8) -> 8
            0x34, 2, 0, 1, 0, 20, 0,      # actor -> object, projected
            0x34, 3, 0, 20, 0, 1, 0,      # reverse is intentionally raw
            0x34, 4, 0, 20, 0, 21, 0,     # object -> object
            0x34, 5, 0, 99, 0, 1, 0,      # unresolved first
            0x34, 6, 0, 1, 0, 99, 0,      # unresolved second
        )))
        host.engine.state.actors[1] = ActorState(room=0, position=(10, 5))
        host.engine.state.actors[2] = ActorState(room=0, position=(6, 9))
        host.engine.state.room_objects[20] = RoomObjectState(20, 0, 0, 1, 1, 20, 5)
        host.engine.state.room_objects[21] = RoomObjectState(21, 0, 0, 1, 1, 23, 14)
        owners = bytearray(host.engine._object_owners)
        owners[20] = owners[21] = 15
        host.engine._object_owners = bytes(owners)
        assert host.engine._video.room is not None
        sentinel = ScummV5Walkbox(0, (0, 0), (0, 0), (0, 0), (0, 0), 0, 0, 255)
        box = ScummV5Walkbox(1, (0, 0), (10, 0), (10, 10), (0, 10), 0, 0, 255)
        host.engine._video.room = replace(
            host.engine._video.room,
            walkboxes=(sentinel, box),
            objects=(
                ScummV5RoomObject(20, 0, 0, 1, 1, 0, 0, 20, 5, 0),
                ScummV5RoomObject(21, 0, 0, 1, 1, 0, 0, 23, 14, 0),
            ),
        )
        actors_before = {key: value.to_dict() for key, value in host.engine.state.actors.items()}
        objects_before = {
            key: value.to_dict() for key, value in host.engine.state.room_objects.items()
        }
        host.tick()
        self.assertEqual(
            [host.engine.state.variables[index] for index in range(7)],
            [0, 4, 0, 10, 9, 0xFF, 0xFF],
        )
        self.assertEqual(
            {key: value.to_dict() for key, value in host.engine.state.actors.items()},
            actors_before,
        )
        self.assertEqual(
            {key: value.to_dict() for key, value in host.engine.state.room_objects.items()},
            objects_before,
        )

    def test_get_dist_inventory_owner_resolution_and_truncation(self) -> None:
        host = self._host(bytes((0x34, 0, 0, 30, 0, 2, 0)))
        host.engine.state.actors[2] = ActorState(room=0, position=(14, 7))
        owners = bytearray(host.engine._object_owners)
        owners[30] = 2
        host.engine._object_owners = bytes(owners)
        host.tick()
        self.assertEqual(host.engine.state.variables[0], 0)

        for script in (
            bytes((0x34, 0, 0, 1, 0)),
            bytes((0x74, 0, 0, 1, 0)),
            bytes((0xB4, 0, 0, 3, 0)),
            bytes((0xF4, 0, 0, 3, 0)),
        ):
            with self.subTest(opcode=script[0]):
                with self.assertRaisesRegex(EngineExecutionError, "ended at offset"):
                    self._host(script).tick()

    def test_c23_print_slots_text_font_projection_and_save(self) -> None:
        font = (ROOT / "examples/resources/scumm_v5/s3_font.char").read_bytes()
        script = bytes((
            0x1A, 10, 0, 253, 0,       # v10 = actor 253 -> text slot 2
            0x14, 252,                 # direct actor -> text slot 3
            0x00, 50, 0, 16, 0,       # at(50, 16)
            0x01, 31,                  # color 31
            0x04,                      # center
            0x0F, ord("S"), 0,        # emit text
            0x94, 10, 0,              # variable actor 253
            0x00, 70, 0, 20, 0,       # configure defaults only
            0x07, 0xFF,                # overhead; saveDefault
            0xD8, 0x0F, ord("F"), 0,  # printEgo through slot 0
            0x00,
        ))
        host = self._host(script, resources={"charset.0": font})
        requests: list[PresentRequest] = []
        host_backend = HostEvidenceBackend()

        class RecordingBackend:
            def present(self, request: PresentRequest) -> PresentRecord:
                requests.append(request)
                return host_backend.present(request)

        host.services.video.backend = RecordingBackend()
        before = host.services.video.surface.hash()
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual([item["actor"] for item in state["print"]["messages"]], [252, 1])
        self.assertEqual(state["print"]["messages"][0]["slot"], 3)
        self.assertEqual(state["print"]["messages"][0]["position"], [50, 16])
        self.assertTrue(state["print"]["messages"][0]["center"])
        self.assertEqual(state["print"]["slots"][2]["position"], [70, 20])
        self.assertTrue(state["print"]["slots"][2]["overhead"])
        self.assertNotEqual(host.services.video.surface.hash(), before)
        historical_direct_pixel_dirty = (
                Rect(17, 28, 1, 1),
                Rect(18, 28, 1, 1),
                Rect(19, 28, 1, 1),
                Rect(20, 28, 1, 1),
                Rect(16, 29, 1, 1),
                Rect(16, 30, 1, 1),
                Rect(17, 31, 1, 1),
                Rect(18, 31, 1, 1),
                Rect(19, 31, 1, 1),
                Rect(20, 32, 1, 1),
                Rect(20, 33, 1, 1),
                Rect(16, 34, 1, 1),
                Rect(17, 34, 1, 1),
                Rect(18, 34, 1, 1),
                Rect(19, 34, 1, 1),
        )
        # Phase 4 removes the physical-pixel raster path.  The final logical
        # composition is now projected by the existing clear/palette/blit
        # boundary, whose three rectangles cover every historical text pixel.
        text_projection_dirty = host.services.video.presented[-1].dirty[4:]
        self.assertEqual(
            text_projection_dirty,
            (Rect(0, 0, 256, 224),) * 3,
        )
        self.assertEqual(requests[-1].dirty[4:], text_projection_dirty)
        self.assertIs(requests[-1].surface, host.services.video.surface)
        self.assertTrue(all(
            any(rect.x <= point.x < rect.x + rect.width
                and rect.y <= point.y < rect.y + rect.height
                for rect in text_projection_dirty)
            for point in historical_direct_pixel_dirty
        ))
        self.assertEqual(
            tuple((point.x, point.y, host.services.video.surface.pixels[
                point.y * host.services.video.surface.pitch + point.x
            ]) for point in historical_direct_pixel_dirty),
            tuple((point.x, point.y, 31) for point in historical_direct_pixel_dirty),
        )
        composition = host.engine._video.composition_surface
        self.assertIsNotNone(composition)
        assert composition is not None
        self.assertEqual(composition.visible_bytes(), host.services.video.surface.visible_bytes())

        assert host.context is not None
        saved = host.engine.save_state(host.context)
        host.engine.state.print_messages.clear()
        host.engine.load_state(host.context, saved)
        self.assertEqual(host.engine.inspect_state()["print"], state["print"])

    def test_runtime_talk_text_replays_after_recomposition_and_clears_on_stop(self) -> None:
        font = (ROOT / "examples/resources/scumm_v5/s3_font.char").read_bytes()
        script = bytes((
            0x14, 1,
            0x00, 50, 0, 16, 0,
            0x01, 31,
            0x0F, ord("S"), 0,
            0x00,
        ))
        host = self._host(script, resources={"charset.0": font})
        host.engine.state.actors[1] = ActorState(room=0, visible=True)
        host.engine.state.variables[37] = 4
        host.tick()
        visible = host.services.video.surface.visible_bytes()
        logical = host.engine._video.composition_surface
        self.assertIsNotNone(logical)
        self.assertEqual(logical.visible_bytes(), visible)

        # An authentic actor/room recomposition restores the backdrop first;
        # the active message must then be replayed into final logical output.
        host.engine._actors_dirty = True
        assert host.context is not None
        host.engine.tick(host.context)
        self.assertEqual(host.services.video.surface.visible_bytes(), visible)
        self.assertTrue(host.engine.state.talk.active)

        while host.engine.state.talk.active:
            host.engine.tick(host.context)
        # stopTalk is a frame-end event.  Its rebuild is consumed by the next
        # logical frame, when the old glyphs disappear with no fake completion.
        still_visible = host.services.video.surface.visible_bytes()
        self.assertEqual(still_visible, visible)
        host.engine.tick(host.context)
        self.assertNotEqual(host.services.video.surface.visible_bytes(), visible)
        self.assertFalse(any(message.slot == 0 for message in host.engine.state.print_messages))

    def test_runtime_print_uses_screen_relative_composition_coordinates(self) -> None:
        font = (ROOT / "examples/resources/scumm_v5/s3_font.char").read_bytes()
        host = self._host(b"\x00", resources={"charset.0": font})
        adapter = host.engine._video
        self.assertEqual(adapter._projection, (0, 0, 0, 0, 256, 224))
        message = PrintMessageState(
            252,
            3,
            PrintSlotState(x=50, y=16, right=319, color=31),
            bytearray((ord("S"), 0)),
        )
        host.engine.state.print_messages.append(message)
        host.engine._presentation_dirty = True
        assert host.context is not None
        host.engine._compose_presentation(host.context)
        expected = {
            (19, 28), (20, 28), (21, 28), (22, 28),
            (18, 29), (18, 30),
            (19, 31), (20, 31), (21, 31),
            (22, 32), (22, 33),
            (18, 34), (19, 34), (20, 34), (21, 34),
        }
        self.assertTrue(all(
            host.services.video.surface.pixels[y * 256 + x] == 31
            for x, y in expected
        ))

    def test_c23_print_fails_closed_on_erase_and_voice(self) -> None:
        for script, message in (
            (bytes((0x14, 1, 0x03, 4, 0, 5, 0)), "print erase 4x5"),
            (bytes((0x14, 1, 0x08, 4, 0, 5, 0)), "sayVoice 4/5"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

    def test_actor_talk_uses_canonical_jiffy_lifecycle_and_glyph_count(self) -> None:
        font = (ROOT / "examples/resources/scumm_v5/s3_font.char").read_bytes()
        raw = bytearray(b"Well, here I am on\x10Thera.\0")
        host = self._host(bytes((0x14, 1, 0x0F)) + raw + b"\x00",
                          resources={"charset.0": font})
        host.engine.state.actors[1] = ActorState(room=0, visible=True)
        host.engine.state.variables[37] = 4
        host.tick()
        talk = host.engine.inspect_state()["talk"]
        self.assertEqual(talk["raw"], list(raw))
        self.assertEqual(talk["delay"], 160)
        self.assertEqual(host.engine.state.variables[3], 0xFF)
        self.assertEqual(host.engine.state.variables[25], 1)
        self.assertEqual(talk["events"], [{
            "kind": "start", "actor": 1, "animation": 4,
            "frame": 1, "generation": 1,
        }])

        # The first 39 subsequent loops leave four jiffies. On loop 40 the
        # post-script dialog phase stops talk; VAR_HAVE_MSG publishes zero on
        # the following loop, exactly like ScummVM's scummLoop ordering.
        for _ in range(39):
            assert host.context is not None
            host.engine.tick(host.context)
        self.assertEqual(host.engine.state.talk.delay, 4)
        self.assertTrue(host.engine.state.talk.active)
        host.engine.tick(host.context)
        self.assertFalse(host.engine.state.talk.active)
        self.assertEqual(host.engine.state.talk.completed_frame, 41)
        self.assertEqual(host.engine.state.variables[3], 1)
        self.assertEqual(host.engine.state.variables[25], 0xFF)
        self.assertEqual(host.engine.state.talk.events[-1].to_dict(), {
            "kind": "stop", "actor": 1, "animation": 5,
            "frame": 41, "generation": 1,
        })
        host.engine.tick(host.context)
        self.assertEqual(host.engine.state.variables[3], 0)
        self.assertEqual(len(host.engine.state.talk.events), 2)

    def test_wait_for_message_retries_then_resumes_after_published_completion(self) -> None:
        font = (ROOT / "examples/resources/scumm_v5/s3_font.char").read_bytes()
        host = self._host(bytes((0x14, 1, 0x0F, ord("A"), 0, 0)),
                          resources={"charset.0": font})
        host.engine.state.actors[1] = ActorState(room=0, visible=True)
        host.engine.state.variables[37] = 4
        host.tick()
        waiter = ScriptSlot("script.wait", bytes((
            0xAE, 0x02,                 # waitForMessage
            0x1A, 10, 0, 1, 0,         # Var[10] = 1
            0x00,
        )), number=2)
        host.engine.state.scripts.append(waiter)
        # 60 + 1*4 = 64 jiffies: stop on the 16th subsequent loop, publish
        # and resume the waiter on the 17th.
        for _ in range(15):
            assert host.context is not None
            host.engine.tick(host.context)
            self.assertEqual(waiter.pc, 0)
            self.assertEqual(host.engine.state.variables[10], 0)
        host.engine.tick(host.context)
        self.assertFalse(host.engine.state.talk.active)
        self.assertEqual(waiter.pc, 0)
        host.engine.tick(host.context)
        self.assertEqual(host.engine.state.variables[10], 1)
        self.assertFalse(waiter.active)

    def test_actor_talk_replacement_and_malformed_input_are_transactional(self) -> None:
        font = (ROOT / "examples/resources/scumm_v5/s3_font.char").read_bytes()
        host = self._host(bytes((0x14, 1, 0x0F, ord("A"), 0, 0)),
                          resources={"charset.0": font})
        host.engine.state.actors[1] = ActorState(room=0, visible=True)
        host.engine.state.actors[2] = ActorState(room=0, visible=True, talk_frames=(6, 7))
        host.engine.state.actors[3] = ActorState(room=7, position=(123, 45), facing=270)
        untouched = host.engine.state.actors[3].to_dict()
        assert host.context is not None
        host.engine.tick(host.context)
        host.engine.state.scripts.append(ScriptSlot(
            "script.replacement", bytes((0x14, 2, 0x0F, ord("B"), 0, 0)), number=2
        ))
        host.tick()
        self.assertEqual(
            [(event.kind, event.actor, event.animation, event.generation)
             for event in host.engine.state.talk.events],
            [("start", 1, 4, 1), ("stop", 1, 5, 1), ("start", 2, 6, 2)],
        )
        self.assertEqual(host.engine.state.talk.actor, 2)
        self.assertEqual(host.engine.state.actors[3].to_dict(), untouched)

        for payload in (bytes((0x14, 1, 0x0F, ord("X"))),
                        bytes((0x14, 1, 0x0F)) + b"X" * 32 + b"\0"):
            candidate = self._host(payload, resources={"charset.0": font})
            candidate.engine.state.actors[1] = ActorState(room=0, visible=True)
            with self.assertRaises(EngineExecutionError):
                candidate.tick()
            self.assertFalse(candidate.engine.state.talk.active)
            self.assertEqual(candidate.engine.state.talk.events, [])

    def test_arithmetic_subset_uses_real_opcode_numbers(self) -> None:
        script = bytes(
            [
                0x1A, 0x01, 0x00, 0x0A, 0x00,  # move v1 = 10
                0x5A, 0x01, 0x00, 0x05, 0x00,  # add v1 += 5
                0x1B, 0x01, 0x00, 0x03, 0x00,  # multiply v1 *= 3
                0x00,
            ]
        )
        host = self._host(script)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["variables"], {"1": 45})

    def test_independent_core_fixture_has_exact_five_frame_trace(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/core_conformance.scrp").read_bytes()
        host = self._host(script)
        expected = [
            (40, 0, True, True, {"1": 12, "2": 0x1111}, 7),
            (47, 2, True, True, {"1": 13, "2": 0x1111}, 9),
            (47, 1, True, True, {"1": 13, "2": 0x1111}, 9),
            (47, 0, True, True, {"1": 13, "2": 0x1111}, 9),
            (61, 0, False, False, {"1": 13, "2": 0x1111, "3": 13}, 12),
        ]
        for pc, delay, active, yielded, variables, operations in expected:
            host.tick()
            state = host.engine.inspect_state()
            slot = state["scripts"][0]
            self.assertEqual(slot["pc"], pc)
            self.assertEqual(slot["delay"], delay)
            self.assertEqual(slot["active"], active)
            self.assertEqual(slot["yielded"], yielded)
            self.assertEqual(state["variables"], variables)
            self.assertEqual(state["operations"], operations)

    def test_c2_extended_fixture_has_exact_signed_trace(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c2_extended.scrp").read_bytes()
        host = self._host(script)
        expected = [
            (96, 2, True, True, {"1": 13, "2": -2, "3": 0x1111, "5": 2}, 17),
            (96, 1, True, True, {"1": 13, "2": -2, "3": 0x1111, "5": 2}, 17),
            (96, 0, True, True, {"1": 13, "2": -2, "3": 0x1111, "5": 2}, 17),
            (102, 0, False, False, {"1": 13, "2": -2, "3": 0x1111, "5": 2, "6": 13}, 19),
        ]
        for pc, delay, active, yielded, variables, operations in expected:
            host.tick()
            state = host.engine.inspect_state()
            slot = state["scripts"][0]
            self.assertEqual((slot["pc"], slot["delay"], slot["active"], slot["yielded"]), (pc, delay, active, yielded))
            self.assertEqual(state["variables"], variables)
            self.assertEqual(state["operations"], operations)

    def test_c2_failure_fixtures_fail_closed(self) -> None:
        cases = {
            "unknown_opcode": r"opcode \$2F is not implemented",
            "bad_variable": "variable 2048 is outside",
            "truncated_operand": "ended at offset 1",
            "division_by_zero": "division by zero",
            "jump_escape": "jump leaves script",
        }
        for name, message in cases.items():
            with self.subTest(name=name):
                script = (ROOT / f"examples/resources/scumm_v5/c2_{name}.scrp").read_bytes()
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        budget = (ROOT / "examples/resources/scumm_v5/c2_budget_exhaustion.scrp").read_bytes()
        with self.assertRaisesRegex(EngineExecutionError, "exhausted the per-tick opcode budget"):
            self._host(budget, max_ops=32).tick()

    def test_c2_delay_range_documents_host_24_bit_support(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c2_delay_range.scrp").read_bytes()
        host = self._host(script)
        host.tick()
        slot = host.engine.inspect_state()["scripts"][0]
        self.assertEqual(slot["delay"], 0x10000)
        self.assertTrue(slot["yielded"])

    def test_c3_indexed_results_variable_operands_and_wrap_trace(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c3_operands.scrp").read_bytes()
        host = self._host(script)
        expected = [
            (35, True, {"0": 2, "1": -32768, "2": 1, "6": 5, "7": 0x1234}, 7),
            (41, True, {"0": 2, "1": 32767, "2": 1, "6": 5, "7": 0x1234}, 9),
            (134, False, {"0": 2, "1": 4681, "2": 1, "3": 7, "4": 255, "5": 255, "6": 6, "7": 0x1234}, 26),
        ]
        for pc, active, variables, operations in expected:
            host.tick()
            state = host.engine.inspect_state()
            slot = state["scripts"][0]
            self.assertEqual((slot["pc"], slot["active"]), (pc, active))
            self.assertEqual(state["variables"], variables)
            self.assertEqual(state["operations"], operations)

    def test_c3_bit_variable_result_is_supported(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c3_bit_variable.scrp").read_bytes()
        host = self._host(script)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["bits"], [0])

    def test_m23b_indexed_bit_reference_is_consumed_by_comparisons(self) -> None:
        # if Bit[417 + 1] == 1: Var[5] = 11 else Var[5] = 22
        script = bytes.fromhex(
            "48 a1 a1 01 00 01 00 06 00 "
            "1a 05 00 0b 00 a0 "
            "1a 05 00 16 00 a0"
        )
        positive = self._host(script)
        positive.engine.state.bit_variables[418] = True
        positive.tick()
        self.assertEqual(positive.engine.state.variables[5], 11)

        negative = self._host(script)
        negative.tick()
        self.assertEqual(negative.engine.state.variables[5], 22)

    def test_c7_cursor_command_and_bit_variables_are_exact_and_saved(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c7_cursor_bits.scrp").read_bytes()
        host = self._host(script)
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["bits"], [5])
        self.assertEqual(state["variables"], {"0": 1, "1": 7, "52": 1, "53": 1})
        self.assertEqual(
            state["cursor_command"],
            {
                "state": 1,
                "user_input": 1,
                "image": [3, 4],
                "hotspot": [3, 5, 6],
                "cursor_id": 9,
                "charset_id": 7,
                "charset_colors": [10, 7],
            },
        )
        saved = host.save(0)
        host.engine.state.bit_variables[5] = False
        host.engine.state.charset_colors.clear()
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["bits"], [5])
        self.assertEqual(host.engine.inspect_state()["cursor_command"]["charset_colors"], [10, 7])

    def test_c8_string_ops_preserve_controls_copy_mutate_and_save(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c8_string_ops.scrp").read_bytes()
        host = self._host(script)
        host.tick()
        state = host.engine.inspect_state()
        expected_raw = [0x41, 0x5A, 0xFF, 0x04, 0x34, 0x12, 0x43, 0x00]
        self.assertEqual(state["variables"], {"0": 5, "1": 1, "2": 90, "3": 12, "4": 66, "5": 90, "6": 4})
        self.assertEqual(state["strings"]["5"]["raw"], expected_raw)
        self.assertEqual(state["strings"]["6"]["raw"], expected_raw)
        self.assertNotIn("7", state["strings"])
        self.assertEqual(
            state["strings"]["5"]["tokens"],
            [
                {"kind": "glyph", "code": 0x41},
                {"kind": "glyph", "code": 0x5A},
                {"kind": "control", "code": 4, "arguments": [0x34, 0x12]},
                {"kind": "glyph", "code": 0x43},
            ],
        )
        saved = host.save(0)
        host.engine.state.strings[5][0] = 0
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["strings"]["5"]["raw"], expected_raw)

    def test_c8_string_ops_fail_closed_on_malformed_or_missing_state(self) -> None:
        cases = (
            ("unknown sub-op", bytes((0x27, 0x00)), r"sub-op 0 is not implemented"),
            ("identical copy", bytes((0x27, 0x02, 5, 5)), r"source and destination are identical"),
            ("missing get", bytes((0x27, 0x04, 0, 0, 5, 0)), r"string 5 does not exist"),
            ("missing set", bytes((0x27, 0x03, 5, 0, 65)), r"string 5 does not exist"),
            ("truncated control", bytes((0x27, 0x01, 5, 0xFF, 4, 0x34)), r"ended at offset 6"),
            (
                "oversized encoded string",
                bytes((0x27, 0x01, 5)) + b"A" * 255 + b"\0",
                r"encoded string exceeds 255 bytes",
            ),
        )
        for name, script, message in cases:
            with self.subTest(name=name):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

    def test_c8_out_of_bounds_character_access_matches_v5(self) -> None:
        # create(5, 2), ignored set at index 2, get index 2 -> zero.
        script = bytes((0x27, 0x05, 5, 2, 0x27, 0x03, 5, 2, 90,
                        0x27, 0x04, 0, 0, 5, 2, 0x80))
        host = self._host(script)
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["variables"], {})
        self.assertEqual(state["strings"]["5"]["raw"], [0, 0])

    def test_c9_set_var_range_byte_word_indexed_local_and_bits(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c9_set_var_range.scrp").read_bytes()
        host = self._host(script)
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(
            state["variables"],
            {"0": 2, "6": 1, "7": 255, "8": 128},
        )
        self.assertEqual(state["scripts"][0]["locals"][:3], [-1, 32767, -32768])
        self.assertEqual(state["bits"], [6, 7])

    def test_c9_zero_count_assigns_256_values(self) -> None:
        script = bytes((0x26, 0x00, 0x80, 0x00)) + bytes([1]) * 256 + bytes((0x80,))
        host = self._host(script)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["bits"], list(range(256)))

    def test_c9_bit_range_wraps_its_packed_index(self) -> None:
        host = self._host(bytes((0x26, 0xFF, 0x8F, 0x02, 1, 1, 0x80)))
        host.tick()
        self.assertEqual(host.engine.inspect_state()["bits"], [0, 4095])

    def test_c9_set_var_range_fails_closed_on_truncation_and_boundaries(self) -> None:
        cases = (
            ("missing count", bytes((0x26, 0x00, 0x00)), r"ended at offset 3"),
            ("truncated byte values", bytes((0x26, 0x00, 0x00, 0x02, 0x01)), r"ended at offset 5"),
            ("truncated word values", bytes((0xA6, 0x00, 0x00, 0x01, 0x34)), r"ended at offset 4"),
            ("global boundary", bytes((0x26, 0xFF, 0x07, 0x02, 1, 2)), r"variable 2048 is outside"),
            ("local boundary", bytes((0x26, 0x1F, 0x40, 0x02, 1, 2)), r"local variable 32 is outside"),
        )
        for name, script, message in cases:
            with self.subTest(name=name):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

    def test_c10_room_ops_intents_palette_auxiliary_string_and_save(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c10_room_ops.scrp").read_bytes()
        host = self._host(script)
        host.engine.state.room_ops.room_width = 640
        host.tick()
        state = host.engine.inspect_state()
        room = state["room_ops"]
        self.assertEqual(room["scroll"], [160, 480])
        self.assertEqual(room["screen"], [16, 184])
        self.assertTrue(room["shake"])
        self.assertEqual(room["scale_slots"], {"1": [100, 20, 200, 180]})
        self.assertEqual(room["intensity"], [128, 128, 128, 4, 9])
        self.assertEqual(room["fade_effect"], 0x1234)
        self.assertEqual(room["rgb_intensity"], [100, 110, 120, 2, 8])
        self.assertEqual(room["shadow"], [50, 60, 70, 3, 9])
        self.assertEqual(room["transform"], [6, 2, 10, 12])
        self.assertEqual(room["cycle_delays"][2], 107)
        self.assertEqual(room["palette_overrides"], {"7": [10, 20, 30]})
        self.assertEqual(room["save_load_request"], [1, 99])
        self.assertEqual(room["auxiliary_files"], {"aux": [65, 66, 67, 0]})
        self.assertEqual(state["strings"]["5"]["raw"], [65, 66, 67, 0])
        self.assertEqual(host.services.video.surface.palette[7], (10, 20, 30))

        saved = host.save(0)
        host.engine.state.room_ops.palette_overrides.clear()
        host.engine.state.room_ops.auxiliary_files.clear()
        host.engine.state.room_ops.shake_enabled = False
        host.load(0)
        restored = host.engine.inspect_state()["room_ops"]
        self.assertTrue(restored["shake"])
        self.assertEqual(restored["auxiliary_files"], {"aux": [65, 66, 67, 0]})
        self.assertEqual(host.services.video.surface.palette[7], (10, 20, 30))
        self.assertEqual(saved.schema, 6)

        assert host.context is not None
        malformed = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed["room_ops"]["auxiliary_files"] = {"\u2603": "00"}
        with self.assertRaises(SaveFormatError):
            host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

    def test_c10_room_ops_variable_operands(self) -> None:
        script = bytes((
            0x1A, 0x00, 0x00, 0x03, 0x00,
            0x1A, 0x01, 0x00, 0x02, 0x00,
            0x33, 0xD0, 0x00, 0x00, 0x01, 0x00,
            0x80,
        ))
        host = self._host(script)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["room_ops"]["cycle_delays"][2], 107)

    def test_c10_room_ops_fail_closed(self) -> None:
        cases = (
            ("unknown", bytes((0x33, 0)), r"sub-op 0 is not implemented"),
            ("v3 room color", bytes((0x33, 2)), r"room-color is invalid for v5"),
            ("empty filename", bytes((0x33, 0x0E, 5, 0)), r"filename is empty"),
            ("missing save string", bytes((0x33, 0x0D, 5, 65, 0)), r"string 5 does not exist"),
            ("bad scale slot", bytes((0x33, 7, 1, 2, 0, 3, 4, 0, 0)), r"scale slot 0 is outside"),
            ("reversed intensity", bytes((0x33, 8, 1, 9, 4)), r"color range 9..4 is reversed"),
            ("truncated palette", bytes((0x33, 4, 1, 0)), r"ended at offset"),
        )
        for name, script, message in cases:
            with self.subTest(name=name):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

    def test_c11_random_direct_variable_inclusive_and_saved(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c11_random.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(
            {key: state["variables"][key] for key in ("0", "1", "2", "4")},
            {"0": 9, "1": 6, "2": 3, "4": 28},
        )
        self.assertNotIn("3", state["variables"])
        self.assertEqual(state["scripts"][0]["locals"][0], 4)
        self.assertEqual(state["random_state"], 0x0E27)

        replay = self._host(bytes((
            0x16, 0x01, 0x00, 10, 0x80,
            0x16, 0x02, 0x00, 10, 0x80,
        )))
        replay.tick()
        saved = replay.save(0)
        replay.tick()
        expected = replay.engine.inspect_state()
        replay.load(0)
        self.assertEqual(replay.engine.inspect_state()["random_state"], 0xE270)
        replay.tick()
        replayed = replay.engine.inspect_state()
        for key in ("variables", "scripts", "random_state", "operations", "frames"):
            self.assertEqual(replayed[key], expected[key])
        self.assertEqual(saved.schema, 6)

    def test_c11_random_fails_closed_on_malformed_operands_and_state(self) -> None:
        cases = (
            (bytes((0x16, 0x01)), r"ended at offset"),
            (bytes((0x16, 0x00, 0x08, 1)), r"variable 2048 is outside"),
            (bytes((0x16, 0x01, 0x00)), r"ended at offset"),
            (bytes((0x96, 0x01, 0x00, 0x00)), r"ended at offset"),
        )
        for script, message in cases:
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        host = self._host(bytes((0x80,)))
        assert host.context is not None
        malformed = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed["random_state"] = 0
        with self.assertRaisesRegex(SaveFormatError, "random state"):
            host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

    def test_c12_pseudo_room_maps_overwrites_resolves_and_saves(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c12_pseudo_room.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        mapper = host.engine.inspect_state()["resource_mapper"]
        self.assertEqual((mapper[0], mapper[1], mapper[2], mapper[127]), (0x12, 0x12, 0, 0x12))

        saved = host.save(0)
        host.tick()
        expected = host.engine.inspect_state()
        mapper = expected["resource_mapper"]
        self.assertEqual((mapper[0], mapper[1], mapper[2], mapper[127]), (0x12, 0x34, 0x34, 0x12))
        host.engine.state.resource_mapper[1] = 0x99
        host.load(0)
        host.tick()
        replayed = host.engine.inspect_state()
        for key in ("resource_mapper", "scripts", "operations", "frames"):
            self.assertEqual(replayed[key], expected[key])
        self.assertEqual(saved.schema, 6)

        resolving = self._host(bytes((0xCC, 0, 0x80, 0, 0x72, 0x80, 0)))
        resolving.tick()
        self.assertEqual(resolving.engine.inspect_state()["room"], 0)

    def test_c12_pseudo_room_fails_closed_on_unterminated_list_and_bad_state(self) -> None:
        for script in (bytes((0xCC,)), bytes((0xCC, 1)), bytes((0xCC, 1, 0x80))):
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, r"ended at offset"):
                    self._host(script).tick()

        host = self._host(bytes((0x80,)))
        assert host.context is not None
        malformed = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        for value in ([0] * 127, [0] * 127 + [256]):
            with self.subTest(value=value[-1]):
                malformed["resource_mapper"] = value
                with self.assertRaisesRegex(SaveFormatError, "resource mapper"):
                    host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

    def test_c13_resource_routines_intent_mapping_variables_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c13_resource_routines.scrp").read_bytes()
        resources = {
            "script.5": b"\x00",
            "sound.6": b"sound-six",
            "sound.8": b"sound-eight",
            "costume.7": b"costume-seven",
            "room.42": b"room-forty-two",
            "charset.1": b"charset-one",
        }
        host = self._host(fixture, resources=resources)
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(first["scripts"][0]["pc"], 32)
        self.assertEqual(
            first["resource_ops"]["loaded"],
            {
                "script": [5], "sound": [6], "costume": [7],
                "room": [42], "charset": [1],
            },
        )
        self.assertEqual(
            first["resource_ops"]["locked"],
            {"script": [5], "sound": [6], "costume": [7], "room": [42]},
        )
        saved = host.save(0)

        host.tick()
        expected = host.engine.inspect_state()
        self.assertEqual(expected["scripts"][0]["pc"], 76)
        self.assertEqual(
            expected["resource_ops"],
            {
                "loaded": {
                    "script": [], "sound": [8], "costume": [],
                    "room": [42], "charset": [],
                },
                "locked": {"script": [], "sound": [], "costume": [], "room": []},
                "last_object": [42, 0x1234],
            },
        )
        host.engine.state.resource_ops.loaded["sound"].clear()
        host.load(0)
        host.tick()
        replayed = host.engine.inspect_state()
        for key in ("resource_ops", "resource_mapper", "scripts", "operations", "frames"):
            self.assertEqual(replayed[key], expected[key])
        self.assertEqual(saved.schema, 6)

    def test_c13_resource_routines_fail_closed_on_operands_resources_and_state(self) -> None:
        cases = (
            (bytes((0x0C,)), r"ended at offset"),
            (bytes((0x0C, 1)), r"ended at offset"),
            (bytes((0x0C, 0)), r"sub-op 0"),
            (bytes((0x0C, 21, 0)), r"sub-op 21"),
            (bytes((0x0C, 0x81, 0x00)), r"ended at offset"),
            (bytes((0x0C, 20, 0)), r"ended at offset"),
        )
        for script, message in cases:
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()
        with self.assertRaisesRegex(EngineExecutionError, r"unknown resource 'sound.9'"):
            self._host(bytes((0x0C, 2, 9))).tick()

        host = self._host(bytes((0x80,)))
        assert host.context is not None
        malformed = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed["resource_ops"]["loaded"]["sound"] = [256]
        with self.assertRaisesRegex(SaveFormatError, "resource loaded id"):
            host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

    def test_c14_actor_ops_full_header_state_variables_defaults_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c14_actor_ops.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        first = host.engine.inspect_state()
        actor1 = first["actors"]["1"]
        self.assertEqual(actor1["costume"], 7)
        self.assertEqual(actor1["walk_speed"], [3, 4])
        self.assertEqual(actor1["sound"], 5)
        self.assertEqual(actor1["frames"], [16, 17, 18, 19, 20])
        self.assertEqual(actor1["elevation"], -2)
        self.assertEqual(actor1["palette"], {"2": 33})
        self.assertEqual(actor1["talk_color"], 34)
        self.assertEqual(actor1["name"], list(b"Actor One\0"))
        self.assertEqual((actor1["width"], actor1["scale"], actor1["box_scale"]), (35, [36, 37], 36))
        self.assertEqual((actor1["force_clip"], actor1["ignore_boxes"]), (0, False))
        self.assertEqual((actor1["animation_speed"], actor1["shadow"]), (39, 40))
        saved = host.save(0)

        host.tick()
        expected = host.engine.inspect_state()
        actor2 = expected["actors"]["2"]
        self.assertEqual(actor2["costume"], 55)
        self.assertEqual(actor2["palette"], {"3": 44})
        self.assertEqual(actor2["name"], list(b"Actor Two\0"))
        self.assertEqual(actor2["walk_speed"], [8, 2])
        self.assertEqual(actor2["frames"], [1, 2, 3, 4, 5])
        self.assertEqual((actor2["force_clip"], actor2["ignore_boxes"]), (0, False))
        host.engine.state.actors.clear()
        host.load(0)
        host.tick()
        replayed = host.engine.inspect_state()
        for key in ("actors", "scripts", "operations", "frames"):
            self.assertEqual(replayed[key], expected[key])
        self.assertEqual(saved.schema, 6)

    def test_c14_actor_ops_fail_closed_on_actor_subop_operands_and_state(self) -> None:
        cases = (
            (bytes((0x13,)), r"ended at offset"),
            (bytes((0x13, 32, 0xFF)), r"actor 32"),
            (bytes((0x13, 1)), r"ended at offset"),
            (bytes((0x13, 1, 15)), r"sub-op 15"),
            (bytes((0x13, 1, 11, 32, 0, 0xFF)), r"palette slot"),
            (bytes((0x13, 1, 13, ord("X"))), r"ended at offset"),
        )
        for script, message in cases:
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        host = self._host(bytes((0x80,)))
        assert host.context is not None
        malformed = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed["actors"] = {"32": {}}
        with self.assertRaisesRegex(SaveFormatError, "actor entry"):
            host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

        malformed = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed["actors"] = {"1": ActorState().to_dict()}
        malformed["actors"]["1"]["ignore_boxes"] = "false"
        with self.assertRaisesRegex(SaveFormatError, "ignore-boxes"):
            host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

    def test_c15_actor_follow_camera_direct_variable_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c15_actor_follow_camera.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["camera_follow_actor"], 3)
        saved = host.save(0)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["camera_follow_actor"], 7)
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["camera_follow_actor"], 3)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["camera_follow_actor"], 7)
        self.assertEqual(saved.schema, 6)

    def test_c15_actor_follow_camera_fails_closed(self) -> None:
        for script, message in (
            (bytes((0x52,)), "ended at offset"),
            (bytes((0x52, 32)), "actor 32"),
            (bytes((0xD2, 0x00)), "ended at offset"),
        ):
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        host = self._host(bytes((0x80,)))
        assert host.context is not None
        malformed = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed["camera_follow_actor"] = True
        with self.assertRaisesRegex(SaveFormatError, "camera-follow"):
            host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

    def test_set_camera_at_immediate_then_normal_phase_publication(self) -> None:
        host = self._host(bytes((0x80,)))
        assert host.context is not None
        state = host.engine.state
        state.current_room = 1
        state.room_ops.room_width = 640
        state.room_ops.scroll_min_x = 160
        state.room_ops.scroll_max_x = 480
        state.camera_x = 320
        state.camera_destination_x = 320
        state.camera_last_x = 320
        state.camera_mode = 1
        state.camera_moving_to_actor = True
        state.screen_start_strip = 20
        state.screen_end_strip = 59
        state.virtual_screen_xstart = 160

        host.engine._set_camera_at_ex(0, host.context)
        self.assertEqual(state.camera_x, 160)
        self.assertEqual(state.camera_destination_x, 0)
        self.assertEqual(state.camera_mode, 0)
        self.assertFalse(state.camera_moving_to_actor)
        self.assertTrue(state.camera_update_pending)
        self.assertEqual(
            (state.screen_start_strip, state.screen_end_strip, state.virtual_screen_xstart),
            (20, 59, 160),
        )

        host.engine._move_camera(host.context)
        self.assertEqual(state.camera_destination_x, 160)
        self.assertEqual(state.camera_x, 160)
        self.assertEqual(
            (state.screen_start_strip, state.screen_end_strip, state.virtual_screen_xstart),
            (0, 39, 0),
        )
        self.assertFalse(state.camera_update_pending)
        self.assertEqual((state.camera_immediate_count, state.camera_publish_count), (1, 1))

    def test_set_camera_at_direct_variable_pc_clamping_and_zero_literal(self) -> None:
        for script, variable in (
            (bytes((0x32, 0x00, 0x00)), None),
            (bytes((0xB2, 0x02, 0x00)), 2),
        ):
            with self.subTest(opcode=script[0]):
                host = self._host(script)
                state = host.engine.state
                state.current_room = 1
                state.room_ops.room_width = 640
                state.room_ops.scroll_min_x = 160
                state.room_ops.scroll_max_x = 480
                state.camera_x = 320
                state.camera_destination_x = 320
                state.camera_mode = 1
                state.camera_moving_to_actor = True
                if variable is not None:
                    state.variables[variable] = 0
                host.tick()
                self.assertEqual(state.scripts[0].pc, 3)
                self.assertEqual(state.camera_x, 160)
                self.assertEqual(state.camera_destination_x, 160)
                self.assertEqual(state.camera_mode, 0)
                self.assertFalse(state.camera_moving_to_actor)
                self.assertEqual(state.virtual_screen_xstart, 0)

    def test_set_camera_at_scroll_script_and_talk_side_effects(self) -> None:
        host = self._host(
            bytes((0xB2, 0x02, 0x00)),
            scripts={14: bytes((0x80,))},
        )
        state = host.engine.state
        state.current_room = 1
        state.room_ops.room_width = 640
        state.room_ops.scroll_min_x = 160
        state.room_ops.scroll_max_x = 480
        state.camera_x = 320
        state.camera_last_x = 320
        state.variables[2] = 0
        state.variables[27] = 14
        state.talk.active = True
        state.talk.actor = 1
        state.talk.have_msg = 1
        state.actors[1] = ActorState(room=1)
        state.print_messages = [
            PrintMessageState(1, 0, PrintSlotState(), bytearray(b"x\0"))
        ]

        host.tick()
        self.assertEqual(state.camera_scroll_script_count, 1)
        self.assertEqual(state.variables[2], 160)
        self.assertFalse(state.talk.active)
        self.assertEqual(state.talk.actor, 0xFF)
        self.assertEqual(state.print_messages, [])

    def test_camera_lifecycle_round_trips_through_save(self) -> None:
        host = self._host(bytes((0x80,)))
        state = host.engine.state
        state.camera_x = 176
        state.camera_y = 100
        state.camera_destination_x = 240
        state.camera_destination_y = 101
        state.camera_last_x = 168
        state.camera_last_y = 99
        state.camera_mode = 1
        state.camera_moving_to_actor = True
        state.screen_start_strip = 2
        state.screen_end_strip = 41
        state.virtual_screen_xstart = 16
        state.camera_immediate_count = 3
        state.camera_publish_count = 4
        state.camera_scroll_script_count = 5
        state.camera_update_pending = True
        saved = host.save(0)

        state.camera_destination_x = 0
        state.camera_mode = 0
        state.virtual_screen_xstart = 0
        host.load(0)
        camera = host.engine.inspect_state()["camera_state"]
        self.assertEqual(camera["destination"], [240, 101])
        self.assertEqual(camera["last"], [168, 99])
        self.assertEqual(camera["mode"], 1)
        self.assertTrue(camera["moving_to_actor"])
        self.assertEqual(camera["screen_strips"], [2, 41])
        self.assertEqual(camera["virtual_screen_xstart"], 16)
        self.assertEqual(camera["immediate_count"], 3)
        self.assertEqual(camera["publish_count"], 4)
        self.assertEqual(camera["scroll_script_count"], 5)
        self.assertTrue(camera["update_pending"])
        self.assertEqual(saved.schema, 6)

    def test_c16_set_class_direct_variable_clear_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c16_set_class.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        expected = {"42": [5], "300": [2, 5]}
        self.assertEqual(host.engine.inspect_state()["object_classes"], expected)
        saved = host.save(0)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["object_classes"], {"300": [2, 3]})
        host.engine.state.object_classes.clear()
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["object_classes"], expected)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["object_classes"], {"300": [2, 3]})
        self.assertEqual(saved.schema, 6)

    def test_c16_set_class_fails_closed_on_stream_class_capacity_and_save(self) -> None:
        for script, message in (
            (bytes((0x5D,)), "ended at offset"),
            (bytes((0x5D, 1, 0, 1, 0x80, 0)), "class 0"),
            (bytes((0x5D, 1, 0, 1, 0xA1, 0)), "class 33"),
            (bytes((0x5D, 1, 0, 1, 0x81, 0)), "ended at offset"),
            (bytes((0xDD, 0)), "ended at offset"),
        ):
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        capacity_script = bytearray()
        for object_id in range(513):
            capacity_script.extend((0x5D, object_id & 0xFF, object_id >> 8, 1, 0x81, 0, 0xFF))
        with self.assertRaisesRegex(EngineExecutionError, "512 modified objects"):
            self._host(bytes(capacity_script), max_ops=1024).tick()

        recovery_script = bytearray(capacity_script[:-7])
        recovery_script.extend((0x5D, 0, 0, 1, 0, 0, 0xFF))
        recovery_script.extend((0x5D, 0, 2, 1, 0x81, 0, 0xFF, 0x80))
        recovered = self._host(bytes(recovery_script), max_ops=1024)
        recovered.tick()
        recovered_classes = recovered.engine.inspect_state()["object_classes"]
        self.assertEqual(len(recovered_classes), 512)
        self.assertNotIn("0", recovered_classes)
        self.assertEqual(recovered_classes["512"], [1])

        host = self._host(bytes((0x80,)))
        assert host.context is not None
        for invalid in (
            {"1": []},
            {"1": [2, 1]},
            {"1": [1, 1]},
            {"1": [33]},
            {"65536": [1]},
            {"01": [1]},
        ):
            malformed = json.loads(host.engine.save_state(host.context).decode("utf-8"))
            malformed["object_classes"] = invalid
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(SaveFormatError, "object-class|object classes"):
                    host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

    def test_m23c_if_class_of_is_canonical_lists_and_authentic_form(self) -> None:
        # Required-present classes 5 and 7; false jumps over the first move.
        prefix = bytes.fromhex("1d 2a00 01 8500 01 8700 ff 0600")
        script = prefix + bytes.fromhex("1a 0100 0b00 a0 1a 0100 1600 a0")
        matching = self._host(script)
        matching.engine.state.object_classes[42] = {5, 7}
        matching.tick()
        self.assertEqual(matching.engine.state.variables[1], 11)

        missing = self._host(script)
        missing.engine.state.object_classes[42] = {5}
        missing.tick()
        self.assertEqual(missing.engine.state.variables[1], 22)

        # Unflagged selectors require absence.
        absent = self._host(bytes.fromhex(
            "1d 2a00 01 0500 ff 0600 1a 0100 2100 a0 1a 0100 2c00 a0"
        ))
        absent.tick()
        self.assertEqual(absent.engine.state.variables[1], 33)

        # Exact room-63 operand form: object 595, required class 18, false
        # relative branch to ENCD +0x004F.
        authentic = bytes.fromhex("1d 5302 01 9200 ff 4600")
        exact = self._host(authentic + bytes(0x4F - len(authentic)) + b"\xA0")
        exact.tick()
        self.assertEqual(exact.engine.state.scripts[0].pc, 0x50)

    def test_m23c_if_class_of_is_fails_closed_on_malformed_lists(self) -> None:
        for script, message in (
            (bytes.fromhex("1d 0100 01 0000 ff 0000"), "class 0"),
            (bytes.fromhex("1d 0100 01 a100 ff 0000"), "class 33"),
            (bytes.fromhex("1d 0100 01 8100"), "ended at offset"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

    def test_c17_verb_ops_complete_surface_delete_new_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c17_verb_ops.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        expected = {
            "5": {
                "color": 6, "hicolor": 7, "dimcolor": 8, "background_color": 9,
                "kind": "text", "charset": 0, "mode": 1, "save_id": 0,
                "key": ord("L"), "center": True, "position": [100, 150],
                "original_left": 100, "image_index": 0, "image_source": None,
                "name": list(b"Look\0"),
            },
            "11": {
                "color": 2, "hicolor": 0, "dimcolor": 8, "background_color": 0,
                "kind": "image", "charset": 0, "mode": 2, "save_id": 0,
                "key": 0, "center": False, "position": [0, 0],
                "original_left": 0, "image_index": 0,
                "image_source": [0, 0x2222], "name": None,
            },
        }
        self.assertEqual(host.engine.inspect_state()["verbs"], expected)
        saved = host.save(0)
        host.tick()
        self.assertEqual(
            host.engine.inspect_state()["verbs"],
            {
                "5": {
                    "color": 2, "hicolor": 0, "dimcolor": 8,
                    "background_color": 9, "kind": "image", "charset": 0,
                    "mode": 0, "save_id": 0, "key": 0, "center": False,
                    "position": [100, 150], "original_left": 100,
                    "image_index": 0x3456, "image_source": [42, 0x3456],
                    "name": list(b"Use\0"),
                }
            },
        )
        host.engine.state.verbs.clear()
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["verbs"], expected)
        host.tick()
        self.assertEqual(set(host.engine.state.verbs), {5})
        self.assertEqual(saved.schema, 6)

    def test_c17_verb_ops_fails_closed_on_stream_name_and_save(self) -> None:
        cases = (
            (bytes((0x7A,)), "ended at offset"),
            (bytes((0xFA, 0)), "ended at offset"),
            (bytes((0x7A, 1, 0x0A)), "sub-op 10"),
            (bytes((0x7A, 1, 0x09)), "ended at offset"),
            (bytes((0x7A, 1, 0x09, 0x02, ord("X"))), "ended at offset"),
            (bytes((0x7A, 1, 0x09, 0x02, *([ord("X")] * 64), 0)), "64 bytes"),
        )
        for script, message in cases:
            with self.subTest(script=script[:8]):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        absent = self._host(bytes((0x7A, 2, 0x09, 0x14, 99, 0, 0xFF, 0x80)))
        absent.tick()
        self.assertIsNone(absent.engine.inspect_state()["verbs"]["2"]["name"])

        fixture = (ROOT / "examples/resources/scumm_v5/c17_verb_ops.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        assert host.context is not None
        base = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        mutations = (
            ("01", "verb entry", lambda verb: None),
            ("5", "kind", lambda verb: verb.__setitem__("kind", "sprite")),
            ("5", "center", lambda verb: verb.__setitem__("center", 1)),
            ("5", "coordinate", lambda verb: verb.__setitem__("position", [0x8000, 0])),
            ("5", "name", lambda verb: verb.__setitem__("name", "41")),
        )
        for key, message, mutate in mutations:
            malformed = json.loads(json.dumps(base))
            if key == "01":
                malformed["verbs"][key] = malformed["verbs"].pop("5")
            else:
                mutate(malformed["verbs"][key])
            with self.subTest(key=key, message=message):
                with self.assertRaisesRegex(SaveFormatError, message):
                    host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

    def test_c18_expression_stack_arithmetic_nested_opcode_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c18_expression.scrp").read_bytes()
        host = self._host(fixture)
        first = host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(first.operations, 6)
        self.assertEqual(state["scripts"][0]["pc"], 53)
        self.assertEqual(
            state["variables"],
            {"0": 2, "1": 7, "2": -3, "3": -7, "6": -20536},
        )
        saved = host.save(0)

        second = host.tick()
        terminal = host.engine.inspect_state()
        self.assertEqual(second.operations, 5)
        self.assertEqual(terminal["scripts"][0]["pc"], 93)
        self.assertEqual(terminal["variables"]["0"], 9)
        self.assertEqual(terminal["variables"]["7"], -3)
        self.assertEqual(terminal["scripts"][0]["locals"][0], 13)
        self.assertEqual(terminal["bits"], [6])

        host.load(0)
        host.tick()
        replay = host.engine.inspect_state()
        replay.pop("input")
        terminal.pop("input")
        self.assertEqual(replay, terminal)
        self.assertEqual(saved.schema, 6)

    def test_c18_expression_fails_closed_on_stack_stream_and_nested_opcode(self) -> None:
        overflow = bytes((0xAC, 0, 0)) + bytes((0x01, 1, 0)) * 257 + bytes((0xFF,))
        cases = (
            (bytes((0xAC,)), "ended at offset"),
            (bytes((0xAC, 0, 0, 0x01, 1)), "ended at offset"),
            (bytes((0xAC, 0, 0, 0x02, 0xFF)), "stack underflow"),
            (bytes((0xAC, 0, 0, 0x01, 1, 0, 0x01, 0, 0, 0x05, 0xFF)), "division by zero"),
            (bytes((0xAC, 0, 0, 0x06, 0x2F, 0xFF)), "inside expression"),
            (overflow, "stack overflow"),
        )
        for script, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

    def test_c19_cutscene_nested_override_and_save(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c19_cutscene.scrp").read_bytes()
        host = self._host(script)
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(first["scripts"][0]["pc"], 26)
        self.assertEqual(first["scripts"][0]["cutscene_override"], 2)
        self.assertEqual(first["cutscenes"]["stack_pointer"], 2)
        self.assertEqual([item["data"] for item in first["cutscenes"]["records"]], [0x1234, 7])
        self.assertEqual(first["cutscenes"]["records"][1]["override_pc"], 17)
        saved = host.save(0)
        host.engine.state.cutscenes.clear()
        host.engine.state.scripts[0].cutscene_override = 0
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["cutscenes"], first["cutscenes"])
        host.tick()
        terminal = host.engine.inspect_state()
        self.assertEqual(terminal["scripts"][0]["pc"], 31)
        self.assertEqual(terminal["scripts"][0]["cutscene_override"], 0)
        self.assertEqual(terminal["cutscenes"]["stack_pointer"], 0)
        self.assertEqual(terminal["variables"], {"0": 7, "4": 1})
        self.assertEqual(saved.schema, 6)

    def test_c19_cutscene_callbacks_and_skip_override(self) -> None:
        callback_main = bytes(
            [
                0x1A, 35, 0, 10, 0, 0x1A, 36, 0, 11, 0,
                0x1A, 1, 0, 7, 0,
                0x40, 0x01, 0x34, 0x12, 0x81, 1, 0, 0xFF,
                0xC0, 0x80,
            ]
        )
        start = bytes(
            [
                0x9A, 2, 0, 0, 0x40,
                0x9A, 3, 0, 1, 0x40,
                0x60, 1,
                0x00,
            ]
        )
        end = bytes([0x9A, 6, 0, 0, 0x40, 0x00])
        host = self._host(callback_main, scripts={10: start, 11: end})
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["variables"], {"1": 7, "2": 0x1234, "3": 7, "6": 0x1234, "35": 10, "36": 11})
        self.assertEqual(state["scripts"][0]["freeze_count"], 0)
        self.assertEqual(state["cutscenes"]["stack_pointer"], 0)

        skip_script = bytes(
            [
                0x40, 0x01, 0x34, 0x12, 0xFF,
                0x58, 1, 0x18, 8, 0,
                0x80,
                0x1A, 4, 0, 1, 0,
                0x58, 0,
                0xC0,
                0x1A, 8, 0, 9, 0,
                0x80,
            ]
        )
        host = self._host(skip_script)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["scripts"][0]["pc"], 11)
        host.tick(input_word=0x0040)
        skipped = host.engine.inspect_state()
        self.assertEqual(skipped["variables"], {"8": 9})
        self.assertEqual(skipped["cutscenes"]["stack_pointer"], 0)
        self.assertEqual(skipped["scripts"][0]["cutscene_override"], 0)

    def test_c24_zero_depth_override_sentinel_clear_skip_and_save(self) -> None:
        script = bytes((
            0x58, 1, 0x18, 8, 0,
            0x1A, 4, 0, 1, 0,
            0x80,
            0x58, 0,
            0x1A, 8, 0, 9, 0,
            0x80,
        ))
        host = self._host(script)
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(first["cutscenes"]["stack_pointer"], 0)
        self.assertEqual(
            first["cutscenes"]["sentinel"],
            {"data": 0, "override_pc": 2, "override_slot": 0},
        )
        saved = host.save(0)
        host.engine.state.cutscene_sentinel = type(host.engine.state.cutscene_sentinel)()
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["cutscenes"], first["cutscenes"])
        legacy_payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        legacy_payload.pop("cutscene_sentinel")
        host.engine.load_state(host.context, json.dumps(legacy_payload).encode("utf-8"))
        self.assertEqual(
            host.engine.inspect_state()["cutscenes"]["sentinel"],
            {"data": 0, "override_pc": None, "override_slot": None},
        )
        host.load(0)

        host.tick(input_word=0x0040)
        skipped = host.engine.inspect_state()
        self.assertEqual(skipped["variables"], {"4": 1, "5": 1, "8": 9})
        self.assertEqual(
            skipped["cutscenes"]["sentinel"],
            {"data": 0, "override_pc": None, "override_slot": None},
        )

        clear = self._host(bytes((0x58, 0, 0x80)))
        clear.tick()
        self.assertEqual(clear.engine.inspect_state()["scripts"][0]["pc"], 3)

    def test_c25_sound_kludge_queue_flush_audio_and_save(self) -> None:
        command = lambda *values: bytes((
            0x4C,
            *(byte for value in values for byte in (0, value & 0xFF, value >> 8 & 0xFF)),
            0xFF,
        ))
        variable_command = bytes((0x4C, 0, 8, 0, 0x80, 0, 0, 0xFF))
        script = b"".join((
            bytes((0x1A, 0, 0, 7, 0)), variable_command, bytes((0x80,)),
            command(0xFFFF), bytes((0x80,)),
            command(9, 7), command(6, 64), command(11), bytes((0x80,)),
            command(0xFFFF), bytes((0x80, 0x00)),
        ))
        host = self._host(script)
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(first["sound_kludge"], {
            "queue": [[8, 7]], "history": [], "result": 0,
            "imuse_queue_clear_count": 0,
        })
        self.assertEqual(host.services.audio.command_history, [])
        saved = host.save(0)
        host.engine.state.sound_queue.clear()
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["sound_kludge"], first["sound_kludge"])

        host.tick()
        self.assertEqual(
            [record["command"] for record in host.services.audio.command_history],
            ["sfx_play", "flush"],
        )
        host.tick()
        self.assertEqual(host.engine.inspect_state()["sound_kludge"]["queue"], [[9, 7], [6, 64], [11]])
        host.tick()
        state = host.engine.inspect_state()["sound_kludge"]
        self.assertEqual(state["queue"], [])
        self.assertEqual(state["history"], [[8, 7], [9, 7], [6, 64], [11]])
        self.assertEqual(host.services.audio.master_volume, 129)
        self.assertEqual(
            [record["command"] for record in host.services.audio.command_history],
            [
                "sfx_play", "flush", "sfx_stop", "master_volume",
                "music_stop", "sfx_stop", "speech_stop", "flush",
            ],
        )

    def test_c25_imuse_compatibility_commands_two_and_three_are_noops(self) -> None:
        def command(value: int) -> bytes:
            return bytes((0x4C, 0, value & 0xFF, value >> 8 & 0xFF, 0xFF))

        host = self._host(command(2) + command(3) + command(0xFFFF) + b"\x80")
        host.tick()
        self.assertEqual(host.engine.state.sound_result, 0)
        self.assertEqual(host.engine.state.sound_history, [[2], [3]])
        self.assertEqual(
            [record["command"] for record in host.services.audio.command_history],
            ["flush"],
        )

    def test_m23c_imuse_clear_queue_is_ordered_and_saved(self) -> None:
        def command(*values: int) -> bytes:
            return bytes((
                0x4C,
                *(byte for value in values for byte in (0, value & 0xFF, value >> 8 & 0xFF)),
                0xFF,
            ))

        host = self._host(command(0x0110) + command(0xFFFF) + b"\x80")
        host.tick()
        state = host.engine.inspect_state()["sound_kludge"]
        self.assertEqual(state["history"], [[0x0110]])
        self.assertEqual(state["imuse_queue_clear_count"], 1)
        saved = host.save(0)
        host.engine.state.imuse_queue_clear_count = 0
        host.load(0)
        self.assertEqual(
            host.engine.inspect_state()["sound_kludge"]["imuse_queue_clear_count"], 1
        )

        malformed = self._host(command(0x0110, 1) + command(0xFFFF))
        with self.assertRaisesRegex(EngineExecutionError, "clear-queue operands"):
            malformed.tick()

    def test_m24rb_sound_queue_abi_and_encoded_dispatch_field(self) -> None:
        # SNES ABI: u8 word count, then that many little-endian s16 words.
        def record(*words: int) -> bytes:
            return bytes((len(words),)) + b"".join(
                int(word & 0xFFFF).to_bytes(2, "little") for word in words
            )

        for encoded, operands in (
            (0x0101, (80, 7)),
            (0x0106, (80, 9)),
            (0x010D, (82, 0, 120)),
            (0x010E, (80, 8)),
            (0x010F, (8, 82)),
        ):
            with self.subTest(encoded=hex(encoded)):
                payload = record(encoded, *operands)
                self.assertEqual(payload[0], 1 + len(operands))
                self.assertEqual(int.from_bytes(payload[1:3], "little"), encoded)
                self.assertEqual(
                    [int.from_bytes(payload[index:index + 2], "little")
                     for index in range(3, len(payload), 2)],
                    list(operands),
                )

        source = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
        pre_copy, post_copy = source.split("ScummV5_C25_Flush__dispatch:", 1)
        command_present = pre_copy.split("ScummV5_C25_Flush__command_present:", 1)[1]
        for encoded in ("#$0101", "#$0106", "#$010D", "#$010E", "#$010F"):
            self.assertNotIn(encoded, command_present)
            self.assertIn(encoded, post_copy)
        self.assertLess(
            post_copy.index("lda.l SAME_SCUMM_C25_QUEUE,x"),
            post_copy.index("cmp #$0101"),
        )
        self.assertIn("cmp #(SAME_SCUMM_C25_MAX_WORDS + 1)", command_present)

    def test_c25_error_path_restores_byte_accumulator_mode_before_diagnostic(self) -> None:
        # The dispatch comparisons are 16-bit.  A byte-sized diagnostic LDA
        # must therefore emit a real SEP; `.a8` alone is assembler metadata.
        source = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
        dispatch_error = source.split("ScummV5_C25_Flush__dispatch_error:", 1)[1]
        diagnostic = dispatch_error.split("SAME_SCUMM_SCENARIO_C25_ERROR_SITE", 1)[1]
        self.assertIn("sep #$20", diagnostic[:160].lower())

    def test_c25_emit_audio_unconditionally_restores_byte_accumulator_abi(self) -> None:
        # Same_Event_Push runs in word mode.  C25 callers resume with byte
        # opcodes in every build flavor, including M21-disabled startup42;
        # leaving M=16 consumes the next immediate's high byte as an opcode.
        source = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
        emit = source.split("ScummV5_C25_EmitAudio:\n", 1)[1]
        emit = emit.split("\n.if SAME_BUILD_SCUMM_M21", 1)[0]
        tail = emit.split("jsr Same_Event_Push", 1)[1]
        self.assertIn("sep #$20", tail)
        self.assertNotIn(".if SAME_BUILD_SCUMM_M21", tail)
        self.assertLess(tail.index("sep #$20"), tail.index("rts"))

    def test_get_actor_position_dispatches_all_v5_word_operand_forms(self) -> None:
        runtime = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
        matrix = (ROOT / "runtime/snes/engines/scumm_v5_matrix_far.pasm").read_text()
        dispatch = runtime.split("ScummV5_Engine_Frame__check_animate_actor:", 1)[1]
        dispatch = dispatch.split("ScummV5_Engine_Frame__check_actor_room_opcode:", 1)[0]
        for opcode, target in (("#$43", "dispatch_get_actor_x"),
                               ("#$C3", "dispatch_get_actor_x"),
                               ("#$23", "dispatch_get_actor_y"),
                               ("#$A3", "dispatch_get_actor_y")):
            self.assertIn(opcode, dispatch)
            self.assertIn(target, dispatch)
        position = matrix.split("ScummV5_GetActorPosition_FarEntry__result_ok:", 1)[1]
        position = position.split("ScummV5_GetActorPosition_FarEntry__zero:", 1)[0]
        self.assertIn("jsl ScummV5_Movement_FarCall_FetchVarOrDirectWord", position)

    def test_c25_compatibility_commands_require_only_the_command_word(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
        compat = source.split("ScummV5_C25_Flush__compat_noop:", 1)[1]
        body = compat.split(".if !SAME_BUILD_M24RB", 1)[0]
        self.assertIn("cmp #$01", body)

    def test_m24rb_canonical_sound_command_forms_and_malformed_parity(self) -> None:
        def command(*values: int) -> bytes:
            return bytes((
                0x4C,
                *(byte for value in values
                  for byte in (0, value & 0xFF, value >> 8 & 0xFF)),
                0xFF,
            ))

        calls: list[tuple[object, ...]] = []

        class Audio:
            def tick(self) -> None:
                pass

            def set_priority(self, sound: int, value: int) -> bool:
                calls.append(("priority", sound, value)); return True

            def set_speed(self, sound: int, value: int) -> bool:
                calls.append(("speed", sound, value)); return True

            def fade_sound(self, sound: int, target: int, duration: int) -> bool:
                calls.append(("fade", sound, target, duration)); return True

            def install_trigger(self, sound: int, marker: int) -> bool:
                calls.append(("trigger", sound, marker)); return True

            def enqueue_deferred(self, payload: list[int]) -> bool:
                calls.append(("deferred", *payload)); return True

        valid = (
            command(0x0101, 80, 7) + command(0x0106, 80, 9)
            + command(0x010D, 82, 0, 120) + command(0x010E, 80, 8)
            + command(0x010F, 8, 82) + command(0xFFFF) + b"\x80"
        )
        host = self._host(valid)
        host.engine._audio = Audio()
        host.tick()
        self.assertEqual(calls, [
            ("priority", 80, 7), ("speed", 80, 9),
            ("fade", 82, 0, 120), ("trigger", 80, 8),
            ("deferred", 8, 82),
        ])

        malformed = (
            ((0x0101, 80), "priority/speed operands"),
            ((0x0106, 80, 9, 1), "priority/speed operands"),
            ((0x010D, 82, 128, 120), "fade operands"),
            ((0x010E, 80, 256), "trigger operands"),
            ((0x010F,), "deferred command is empty"),
        )
        for words, message in malformed:
            with self.subTest(words=words):
                candidate = self._host(command(*words) + command(0xFFFF))
                candidate.engine._audio = Audio()
                with self.assertRaisesRegex(EngineExecutionError, message):
                    candidate.tick()

        # 0x010F is variable length canonically; extra payload words are retained.
        calls.clear()
        variable = self._host(command(0x010F, 0x010D, 82, 0, 120) + command(0xFFFF))
        variable.engine._audio = Audio()
        variable.tick()
        self.assertEqual(calls, [("deferred", 0x010D, 82, 0, 120)])

        # The old SNES bug treated count byte 1 as command 0x0101. An unknown
        # one-word command must remain unknown, never execute priority.
        calls.clear()
        old_bug = self._host(command(0x1234) + command(0xFFFF))
        old_bug.engine._audio = Audio()
        with self.assertRaisesRegex(EngineExecutionError, r"command \$1234 is not implemented"):
            old_bug.tick()
        self.assertEqual(calls, [])

    def test_c25_sound_kludge_fails_closed_on_stream_command_capacity_and_save(self) -> None:
        command = lambda value: bytes((0x4C, 0, value & 0xFF, value >> 8 & 0xFF, 0xFF))
        cases = (
            (bytes((0x4C, 0xFF)), "command is empty"),
            (command(12) + command(0xFFFF) + bytes((0x80,)), "command 12 is not implemented"),
            (bytes((0x4C, 0, 8, 0, 0xFF, 0x4C, 0, 0xFF)), "ended at offset"),
            (command(11) * 17 + bytes((0x80,)), "queue exceeds 16 commands"),
        )
        for script, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        host = self._host(command(11) + bytes((0x80,)))
        host.tick()
        assert host.context is not None
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        payload["sound_kludge"]["queue"] = [[0x8000]]
        with self.assertRaisesRegex(SaveFormatError, "value must fit s16"):
            host.engine.load_state(host.context, json.dumps(payload).encode("utf-8"))

    def test_imuse_player_hook_command_dispatches_at_flush(self) -> None:
        def command(*values: int) -> bytes:
            return bytes((
                0x4C,
                *(byte for value in values for byte in (0, value & 0xFF, value >> 8 & 0xFF)),
                0xFF,
            ))

        host = self._host(command(0x010C, 80, 0, 15) + command(0xFFFF) + b"\x80")
        calls = []

        class Audio:
            def tick(self) -> None:
                pass

            def set_hook(self, sound: int, cls: int, value: int, channel: int) -> bool:
                calls.append((sound, cls, value, channel))
                return True

        host.engine._audio = Audio()
        host.tick()
        self.assertEqual(calls, [(80, 0, 15, 0)])
        self.assertEqual(host.engine.state.sound_result, 0)

    def test_imuse_player_rejects_noncanonical_jump_hook_channel(self) -> None:
        def command(*values: int) -> bytes:
            return bytes((
                0x4C,
                *(byte for value in values for byte in (0, value & 0xFF, value >> 8 & 0xFF)),
                0xFF,
            ))

        host = self._host(command(0x010C, 80, 0, 14, 0) + command(0xFFFF))
        with self.assertRaisesRegex(EngineExecutionError, "hook operands are invalid"):
            host.tick()

    def test_c26_save_restore_verbs_banks_replacement_delete_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c26_save_restore_verbs.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(first["verbs"], {})
        self.assertEqual(
            [(item["id"], item["bank"], item["verb"]["color"]) for item in first["saved_verbs"]],
            [(1, 5, 3), (2, 5, 4)],
        )
        saved = host.save(0)
        host.engine.state.saved_verbs.clear()
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["saved_verbs"], first["saved_verbs"])

        host.tick()
        second = host.engine.inspect_state()
        self.assertEqual(second["verbs"]["1"]["color"], 3)
        self.assertEqual([(item["id"], item["bank"]) for item in second["saved_verbs"]], [(2, 5)])
        host.tick()
        third = host.engine.inspect_state()
        self.assertEqual(third["verbs"]["1"]["color"], 3)
        self.assertEqual(third["saved_verbs"], [])
        host.tick()
        self.assertTrue(host.engine.inspect_state()["scripts"][0]["active"] is False)

    def test_c26_save_restore_verbs_fails_closed_on_stream_capacity_and_save(self) -> None:
        cases = (
            (bytes((0xAB, 4, 1, 2, 3, 0x80)), "sub-op 4 is invalid"),
            (bytes((0xAB, 1, 1)), "ended at offset"),
            (bytes((0xAB, 0x81, 1, 2, 3, 0x80)), "sub-op 129 is invalid"),
        )
        for script, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        define = lambda verb_id: bytes((0x7A, verb_id, 9, 0xFF))
        save = lambda verb_id: bytes((0xAB, 1, verb_id, verb_id, 1))
        host = self._host(
            b"".join(define(index) + save(index) for index in range(65)) + bytes((0x80,)),
            max_ops=200,
        )
        with self.assertRaisesRegex(EngineExecutionError, "exceeds 64 saved slots"):
            host.tick()

        valid = self._host(define(1) + save(1) + bytes((0x80,)))
        valid.tick()
        assert valid.context is not None
        payload = json.loads(valid.engine.save_state(valid.context).decode("utf-8"))
        saved_key = next(key for key in payload["verbs"] if ":" in key)
        malformed = (
            {**payload, "verbs": {"1:5:9": payload["verbs"][saved_key]}},
            {**payload, "verbs": {saved_key: {**payload["verbs"][saved_key], "save_id": 0}}},
        )
        for item in malformed:
            with self.assertRaisesRegex(SaveFormatError, "saved-verb identity is invalid"):
                valid.engine.load_state(valid.context, json.dumps(item).encode("utf-8"))

    def test_c28_animate_actor_direct_variable_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c28_animate_actor.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(first["actors"]["10"]["animation"], 250)
        self.assertEqual(first["scripts"][0]["pc"], 4)

        saved = host.save(0)
        host.engine.state.actors[10].animation = 99
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["actors"]["10"]["animation"], 250)

        host.tick()
        second = host.engine.inspect_state()
        self.assertEqual(second["actors"]["10"]["animation"], 6)
        self.assertEqual(second["scripts"][0]["pc"], 20)
        host.tick()
        self.assertFalse(host.engine.inspect_state()["scripts"][0]["active"])

    def test_c28_animate_actor_fails_closed_on_actor_stream_and_save(self) -> None:
        for script, message in (
            (bytes((0x11, 32, 1)), "actor 32 is outside"),
            (bytes((0x11, 10)), "ended at offset"),
            (bytes((0xD1, 0, 0, 1)), "ended at offset"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        host = self._host(bytes((0x11, 10, 1, 0x80)))
        host.tick()
        assert host.context is not None
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        payload["actors"]["10"]["animation"] = 256
        with self.assertRaisesRegex(SaveFormatError, "actor scalar must fit u8"):
            host.engine.load_state(host.context, json.dumps(payload).encode("utf-8"))

    def test_c29_actor_from_pos_order_touchability_variables_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c29_actor_from_pos.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        host.engine.state.actors = {
            1: ActorState(room=0, visible=True, hitbox=(10, 10, 30, 40)),
            2: ActorState(room=0, visible=True, hitbox=(10, 10, 30, 40)),
            3: ActorState(room=0, visible=True, hitbox=(40, 50, 70, 80)),
            4: ActorState(room=1, visible=True, hitbox=(10, 10, 30, 40)),
            5: ActorState(room=0, visible=False, hitbox=(10, 10, 30, 40)),
        }
        host.engine.state.object_classes[1] = {32}
        saved = host.save(0)
        host.engine.state.actors[2].hitbox = (0, 0, 0, 0)
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["actors"]["2"]["hitbox"], [10, 10, 30, 40])

        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["variables"], {"0": 2, "1": 3, "2": 50, "3": 60})
        self.assertEqual(state["scripts"][0]["pc"], 33)
        host.tick()
        self.assertFalse(host.engine.inspect_state()["scripts"][0]["active"])

    def test_c29_actor_from_pos_fails_closed_on_stream_and_spatial_save(self) -> None:
        for script in (
            bytes((0x15, 0, 0, 1)),
            bytes((0xD5, 0, 0, 1, 0, 2)),
        ):
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, "ended at offset"):
                    self._host(script).tick()

        host = self._host(bytes((0x80,)))
        host.tick()
        host.engine.state.actors[1] = ActorState()
        assert host.context is not None
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed = (
            ({**payload["actors"]["1"], "visible": 1}, "visible flag"),
            ({**payload["actors"]["1"], "room": 256}, "room must fit u8"),
            ({**payload["actors"]["1"], "hitbox": [0, 0, 32768, 1]}, "hitbox must contain s16"),
            ({**payload["actors"]["1"], "hitbox": [2, 0, 1, 1]}, "hitbox is reversed"),
        )
        for actor, message in malformed:
            with self.subTest(message=message):
                candidate = {**payload, "actors": {"1": actor}}
                with self.assertRaisesRegex(SaveFormatError, message):
                    host.engine.load_state(host.context, json.dumps(candidate).encode("utf-8"))

    def test_c30_find_object_order_hierarchy_wide_variables_and_bounds(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c30_find_object.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        host.engine.state.room_objects = {
            200: RoomObjectState(200, 0, 0, 20, 20, 0, 0, local_index=1),
            201: RoomObjectState(201, 0, 0, 20, 20, 0, 0, local_index=2),
            202: RoomObjectState(
                202, 288, 32, 32, 16, 0, 0,
                local_index=3, parent=5, parent_state=2,
            ),
            204: RoomObjectState(
                204, 288, 32, 32, 16, 0, 0,
                local_index=4, parent=5, parent_state=1,
            ),
            203: RoomObjectState(203, 400, 100, 8, 8, 0, 0, state=1, local_index=5),
        }
        host.engine.state.object_classes[200] = {32}
        host.engine.state.object_states[203] = 1
        host.save(0)
        host.engine.state.room_objects[204].parent_state = 2
        host.load(0)

        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(
            state["variables"], {"0": 201, "1": 204, "2": 300, "3": 40}
        )
        self.assertEqual(state["scripts"][0]["pc"], 29)
        host.tick()
        self.assertFalse(host.engine.inspect_state()["scripts"][0]["active"])

    def test_c30_find_object_fails_closed_on_stream_and_hierarchy_save(self) -> None:
        for script in (
            bytes((0x35, 0, 0, 1)),
            bytes((0xF5, 0, 0, 1, 0, 2)),
        ):
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, "ended at offset"):
                    self._host(script).tick()

        host = self._host(bytes((0x80,)))
        host.tick()
        host.engine.state.room_objects[100] = RoomObjectState(100, 0, 0, 8, 8, 0, 0)
        assert host.context is not None
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed = (
            ({**payload["room_objects"]["100"], "local_index": 2}, "hierarchy is invalid"),
            ({**payload["room_objects"]["100"], "parent": 2}, "hierarchy is invalid"),
            ({**payload["room_objects"]["100"], "parent_state": 256}, "hierarchy is invalid"),
            ({**payload["room_objects"]["100"], "parent": 1}, "contains a cycle"),
        )
        for room_object, message in malformed:
            with self.subTest(message=message):
                candidate = {**payload, "room_objects": {"100": room_object}}
                with self.assertRaisesRegex(SaveFormatError, message):
                    host.engine.load_state(host.context, json.dumps(candidate).encode("utf-8"))

    def test_c31_put_actor_in_room_direct_variable_zero_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c31_put_actor_in_room.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        host.engine.state.actors = {
            1: ActorState(
                room=4, visible=True, position=(100, 90), moving=3,
                hitbox=(88, 40, 112, 90),
            ),
            2: ActorState(
                room=0, visible=True, position=(200, 80), moving=1,
                hitbox=(188, 30, 212, 80),
            ),
        }

        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(first["scripts"][0]["pc"], 5)
        self.assertEqual(first["actors"]["1"]["room"], 75)
        self.assertTrue(first["actors"]["1"]["visible"])
        self.assertEqual(first["actors"]["1"]["position"], [100, 90])
        self.assertEqual(first["actors"]["1"]["moving"], 3)
        host.save(0)
        host.engine.state.actors[1].room = 2
        host.load(0)

        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["variables"], {"0": 2, "1": 331})
        self.assertEqual(state["scripts"][0]["pc"], 24)
        self.assertEqual(state["actors"]["2"]["room"], 75)
        self.assertEqual(state["actors"]["2"]["position"], [200, 80])
        self.assertEqual(state["actors"]["2"]["moving"], 1)
        self.assertEqual(state["actors"]["1"]["room"], 0)
        self.assertFalse(state["actors"]["1"]["visible"])
        self.assertEqual(state["actors"]["1"]["position"], [0, 0])
        self.assertEqual(state["actors"]["1"]["moving"], 0)
        self.assertEqual(state["actors"]["1"]["hitbox"], [88, 40, 112, 90])
        host.tick()
        self.assertFalse(host.engine.inspect_state()["scripts"][0]["active"])

    def test_m23c_get_actor_room_canonical_direct_variable_and_invalid(self) -> None:
        # v0 = room(actor 9), v1 = 9, v2 = room(actor v1), v3 = room(actor 32).
        script = bytes.fromhex(
            "03 0000 09 1a 0100 0900 83 0200 0100 03 0300 20 80"
        )
        host = self._host(script)
        host.engine.state.actors[9] = ActorState(room=49)
        host.tick()
        self.assertEqual(
            [host.engine.state.variables[index] for index in range(4)],
            [49, 9, 49, 0],
        )

        with self.assertRaisesRegex(EngineExecutionError, "ended at offset"):
            self._host(bytes((0x03, 0, 0))).tick()

    def test_c31_put_actor_in_room_fails_closed_on_stream_and_actor_save(self) -> None:
        for script in (bytes((0x2D, 1)), bytes((0xED, 0, 0, 1))):
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, "ended at offset"):
                    self._host(script).tick()

        with self.assertRaisesRegex(EngineExecutionError, "actor 32"):
            self._host(bytes((0x2D, 32, 1))).tick()

        host = self._host(bytes((0x80,)))
        host.tick()
        host.engine.state.actors[1] = ActorState()
        assert host.context is not None
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed = (
            ({**payload["actors"]["1"], "position": [0, 32768]}, "position must contain s16"),
            ({**payload["actors"]["1"], "moving": 256}, "moving flags must fit u8"),
        )
        for actor, message in malformed:
            with self.subTest(message=message):
                candidate = {**payload, "actors": {"1": actor}}
                with self.assertRaisesRegex(SaveFormatError, message):
                    host.engine.load_state(host.context, json.dumps(candidate).encode("utf-8"))

    def test_put_actor_decodes_all_v5_parameter_modes_and_16_bit_coordinates(self) -> None:
        program = bytearray()
        boundaries = []
        for opcode in (0x01, 0x21, 0x41, 0x61, 0x81, 0xA1, 0xC1, 0xE1):
            start = len(program)
            program.append(opcode)
            program.extend((0, 0) if opcode & 0x80 else (1,))
            program.extend((1, 0) if opcode & 0x40 else (0x47, 0x02))
            program.extend((2, 0) if opcode & 0x20 else (0x88, 0x00))
            boundaries.append((start, len(program)))
        program.append(0x80)
        host = self._host(bytes(program))
        host.engine.state.variables[:3] = [1, 583, 136]
        host.engine.state.actors = {
            1: ActorState(room=0, position=(7, 9), moving=3),
            2: ActorState(room=0, position=(111, 222)),
        }

        observed = []
        original = host.engine._op_put_actor

        def traced(slot, context):
            start = slot.pc - 1
            result = original(slot, context)
            observed.append((start, slot.pc))
            return result

        host.engine._handlers.update({opcode: traced for opcode in (
            0x01, 0x21, 0x41, 0x61, 0x81, 0xA1, 0xC1, 0xE1
        )})
        host.tick()
        self.assertEqual(observed, boundaries)
        self.assertEqual(host.engine.state.actors[1].position, (583, 136))
        self.assertEqual(host.engine.state.actors[2].position, (111, 222))

    def test_put_actor_replaces_position_isolates_actor_and_rejects_invalid(self) -> None:
        host = self._host(bytes.fromhex("01 01 2c 01 90 01 01 01 47 02 88 00 80"))
        host.engine.state.actors = {
            1: ActorState(room=0, position=(5, 6)),
            2: ActorState(room=0, position=(7, 8)),
        }
        host.tick()
        self.assertEqual(host.engine.state.actors[1].position, (583, 136))
        self.assertEqual(host.engine.state.actors[2].position, (7, 8))
        self.assertEqual(host.engine.state.scripts[0].pc, 13)

        with self.assertRaisesRegex(EngineExecutionError, "actor 32"):
            self._host(bytes.fromhex("01 20 47 02 88 00")).tick()
        for malformed in (bytes((0x01,)), bytes((0x01, 1, 2, 0))):
            with self.subTest(malformed=malformed):
                with self.assertRaisesRegex(EngineExecutionError, "ended at offset"):
                    self._host(malformed).tick()

    def test_set_state_decodes_modes_replaces_global_state_and_invalidates_local(self) -> None:
        program = bytearray()
        boundaries = []
        for opcode in (0x07, 0x47, 0x87, 0xC7):
            start = len(program)
            program.append(opcode)
            program.extend((0, 0) if opcode & 0x80 else (0x4E, 0x02))
            program.extend((1, 0) if opcode & 0x40 else (0xFF,))
            boundaries.append((start, len(program)))
        program.append(0x80)
        host = self._host(bytes(program))
        host.engine.state.variables[:2] = [590, 255]
        host.engine.state.object_states = {590: 1, 591: 7}
        host.engine.state.room_objects = {
            590: RoomObjectState(590, 8, 16, 24, 32, 0, 0, 1),
            591: RoomObjectState(591, 0, 0, 8, 8, 0, 0, 7, local_index=2),
        }
        host.engine.state.object_draw_queue = [590, 591]
        observed = []
        original = host.engine._op_set_state

        def traced(slot, context):
            start = slot.pc - 1
            result = original(slot, context)
            observed.append((start, slot.pc))
            return result

        host.engine._handlers.update({opcode: traced for opcode in (0x07, 0x47, 0x87, 0xC7)})
        host.tick()
        self.assertEqual(observed, boundaries)
        self.assertEqual(host.engine.state.object_states[590], 255)
        self.assertEqual(host.engine.state.room_objects[590].state, 255)
        self.assertEqual(host.engine.state.object_states[591], 7)
        self.assertEqual(host.engine.state.object_draw_queue, [])
        self.assertTrue(host.engine._background_needs_redraw)

    def test_set_state_zero_one_overwrite_invalid_and_truncated(self) -> None:
        host = self._host(bytes.fromhex("07 64 00 00 07 64 00 01 07 65 00 ff 80"))
        host.engine.state.object_states = {100: 9, 101: 3}
        host.tick()
        self.assertEqual(host.engine.state.object_states, {100: 1, 101: 255})
        self.assertEqual(host.engine.state.scripts[0].pc, 13)
        with self.assertRaisesRegex(EngineExecutionError, "outside global range"):
            self._host(bytes.fromhex("07 00 10 00")).tick()
        for malformed in (bytes((0x07,)), bytes((0x07, 1)), bytes((0x07, 1, 0))):
            with self.subTest(malformed=malformed):
                with self.assertRaisesRegex(EngineExecutionError, "ended at offset"):
                    self._host(malformed).tick()

    def test_get_actor_facing_canonical_boundaries_and_read_only_state(self) -> None:
        angles = (0, 70, 71, 90, 109, 110, 180, 250, 251, 270, 289, 290, 359)
        expected = (3, 3, 1, 1, 1, 2, 2, 2, 2, 0, 0, 3, 3)
        program = bytearray()
        boundaries = []
        for index, _angle in enumerate(angles):
            start = len(program)
            program.extend((0x63, index & 0xFF, index >> 8, index + 1))
            boundaries.append((start, len(program)))
        # Variable actor operand and a replacement of result variable zero.
        program.extend((0x1A, 30, 0, 13, 0, 0xE3, 0, 0, 30, 0, 0x80))
        host = self._host(bytes(program))
        host.engine.state.variables[31] = 0x5151
        host.engine.state.actors = {
            index + 1: ActorState(
                facing=angle, room=index & 3, position=(index * 7, index * 5),
                walkbox=index, moving=index & 1, visible=bool(index & 1),
            )
            for index, angle in enumerate(angles)
        }
        before = {actor_id: actor.to_dict() for actor_id, actor in host.engine.state.actors.items()}
        host.tick()
        self.assertEqual(host.engine.state.variables[:len(expected)], list(expected))
        self.assertEqual(host.engine.state.variables[31], 0x5151)
        self.assertEqual(host.engine.state.scripts[0].pc, len(program))
        self.assertEqual(
            {actor_id: actor.to_dict() for actor_id, actor in host.engine.state.actors.items()},
            before,
        )
        self.assertEqual(boundaries[0], (0, 4))
        self.assertEqual(boundaries[-1], (48, 52))

    def test_get_actor_facing_rejects_invalid_and_truncated_operands(self) -> None:
        with self.assertRaisesRegex(EngineExecutionError, "actor 32"):
            self._host(bytes.fromhex("63 00 00 20")).tick()
        for malformed in (bytes((0x63,)), bytes((0x63, 0)), bytes((0x63, 0, 0)),
                          bytes((0xE3, 0, 0, 1))):
            with self.subTest(malformed=malformed):
                with self.assertRaisesRegex(EngineExecutionError, "ended at offset"):
                    self._host(malformed).tick()

    def test_get_actor_walkbox_reads_stored_field_without_actor_mutation(self) -> None:
        program = bytearray()
        program.extend((0x7B, 0, 0, 1))       # Var[0] = actor 1, direct
        program.extend((0x7B, 5, 0, 2))       # Var[5] = actor 2, direct
        program.extend((0x7B, 9, 0, 3))       # Var[9] = actor 3, direct
        program.extend((0xFB, 12, 0, 30, 0))  # Var[12] = actor Var[30]
        program.append(0)
        host = self._host(bytes(program))
        host.engine.state.variables[0] = 0x7777
        host.engine.state.variables[5] = 0x5555
        host.engine.state.variables[9] = 0x9999
        host.engine.state.variables[12] = 0x1212
        host.engine.state.variables[30] = 3
        host.engine.state.variables[31] = 0x5151
        host.engine.state.actors = {
            1: ActorState(room=7, position=(900, 700), walkbox=0, facing=90,
                          moving=2, walk_destination=(1, 2), visible=True),
            2: ActorState(room=8, position=(-20, 300), walkbox=7, facing=180,
                          moving=4, walk_destination=(3, 4), visible=False),
            # Its position deliberately has no relationship to stored box 19.
            3: ActorState(room=9, position=(4, 1), walkbox=19, facing=270,
                          moving=6, walk_destination=(5, 6), visible=True),
        }
        before = {
            actor_id: actor.to_dict()
            for actor_id, actor in host.engine.state.actors.items()
        }
        host.tick()
        self.assertEqual(
            [host.engine.state.variables[index] for index in (0, 5, 9, 12)],
            [0, 7, 19, 19],
        )
        self.assertEqual(host.engine.state.variables[31], 0x5151)
        self.assertEqual(host.engine.state.scripts[0].pc, len(program))
        self.assertEqual(
            {actor_id: actor.to_dict() for actor_id, actor in host.engine.state.actors.items()},
            before,
        )

    def test_get_actor_walkbox_rejects_invalid_and_truncated_operands(self) -> None:
        with self.assertRaisesRegex(EngineExecutionError, "actor 32"):
            self._host(bytes.fromhex("7b 00 00 20")).tick()
        for malformed in (
            bytes((0x7B,)), bytes((0x7B, 0)), bytes((0x7B, 0, 0)),
            bytes((0xFB, 0, 0, 1)),
        ):
            with self.subTest(malformed=malformed):
                with self.assertRaisesRegex(EngineExecutionError, "ended at offset"):
                    self._host(malformed).tick()

    def test_c39_walk_actor_to_decodes_all_operand_variants(self) -> None:
        program = bytearray()
        for opcode in (0x1E, 0x3E, 0x5E, 0x7E, 0x9E, 0xBE, 0xDE, 0xFE):
            program.append(opcode)
            program.extend((0, 0) if opcode & 0x80 else (1,))
            program.extend((1, 0) if opcode & 0x40 else (200, 0))
            program.extend((2, 0) if opcode & 0x20 else (210, 0))
        program.append(0)
        host = self._host(bytes(program))
        host.engine.state.variables[:3] = [1, 200, 210]
        host.engine.state.actors[1] = ActorState(room=1)

        host.tick()
        actor = host.engine.state.actors[1]
        self.assertEqual((actor.position, actor.walkbox, actor.moving), ((200, 210), 0xFF, 0))
        self.assertFalse(host.engine.state.scripts[0].active)

    def test_c39_walk_actor_to_preserves_signed_word_coordinates(self) -> None:
        # Variable coordinates retain the complete target word; the movement
        # API interprets the bit pattern through the ordinary signed-coordinate
        # convention rather than truncating it to a byte.
        program = bytes((
            0xFE, 120, 0, 0, 1, 186, 1,
            0x00,
        ))
        host = self._host(program)
        host.engine.state.variables[120] = 1
        host.engine.state.variables[256] = -1
        host.engine.state.variables[442] = -0x8000
        host.engine.state.actors[1] = ActorState(room=1)

        host.tick()
        self.assertEqual(host.engine.state.actors[1].position, (-1, -0x8000))
        self.assertEqual(
            [host.engine.state.variables[index] for index in (120, 256, 442)],
            [1, -1, -0x8000],
        )

    def test_production_tick_preserves_one_scheduler_pass_per_frame(self) -> None:
        program = bytes((
            0x1A, 0, 0, 1, 0, 0x80,
            0x1A, 1, 0, 1, 0, 0x80,
            0x1A, 2, 0, 1, 0, 0x00,
        ))
        host = self._host(program)

        host.tick()
        self.assertEqual(host.engine.state.variables[:3], [1, 0, 0])
        self.assertEqual(host.engine.state.scripts[0].pc, 6)
        host.tick()
        self.assertEqual(host.engine.state.variables[:3], [1, 1, 0])
        self.assertEqual(host.engine.state.scripts[0].pc, 12)
        host.tick()
        self.assertEqual(host.engine.state.variables[:3], [1, 1, 1])
        self.assertFalse(host.engine.state.scripts[0].active)

    def test_production_tick_advances_actor_once_and_waiter_retries(self) -> None:
        waiter = bytes((
            0xAE, 0x01, 0x01,
            0x1A, 10, 0, 1, 0,
            0x00,
        ))
        host = self._host(waiter)
        host.engine.state.current_room = 0
        host.engine.state.actors[1] = ActorState(
            room=0, position=(0, 0), walkbox=0, moving=1,
            walk_destination=(100, 0), walk_destination_box=0,
            walk_current_box=0,
        )

        host.tick()
        actor = host.engine.state.actors[1]
        self.assertEqual(host.engine.state.scripts[0].pc, 0)
        self.assertEqual(host.engine.state.variables[10], 0)
        self.assertTrue(actor.moving)
        self.assertGreater(actor.position[0], 0)
        self.assertLess(actor.position[0], 100)
        first_position = actor.position

        host.tick()
        self.assertEqual(host.engine.state.scripts[0].pc, 0)
        self.assertGreater(host.engine.state.actors[1].position[0], first_position[0])
        while host.engine.state.actors[1].moving:
            host.tick()
        self.assertEqual(host.engine.state.variables[10], 0)
        host.tick()
        self.assertEqual(host.engine.state.variables[10], 1)
        self.assertFalse(host.engine.state.scripts[0].active)

    def test_stopping_actor_between_frames_releases_waiter(self) -> None:
        host = self._host(bytes((
            0xAE, 0x01, 0x01,
            0x1A, 10, 0, 1, 0,
            0x00,
        )))
        host.engine.state.actors[1] = ActorState(
            room=0, position=(0, 0), walkbox=0, moving=1,
            walk_destination=(100, 0), walk_destination_box=0,
            walk_current_box=0,
        )
        host.tick()
        self.assertEqual(host.engine.state.scripts[0].pc, 0)
        host.engine.state.actors[1].moving = 0
        host.tick()
        self.assertEqual(host.engine.state.variables[10], 1)
        self.assertFalse(host.engine.state.scripts[0].active)

    def test_c39_walk_state_save_validation_fails_closed(self) -> None:
        for script in (
            bytes((0x1E, 1, 2, 0, 3)),
            bytes((0xFE, 0, 0, 1, 0, 2)),
        ):
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, "ended at offset"):
                    self._host(script).tick()
        with self.assertRaisesRegex(EngineExecutionError, "actor 32"):
            self._host(bytes((0x1E, 32, 1, 0, 1, 0))).tick()

        host = self._host(bytes((0x80,)))
        host.tick()
        host.engine.state.actors[1] = ActorState()
        assert host.context is not None
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed = (
            ({**payload["actors"]["1"], "walk_destination": [0, 32768]}, "walk_destination must contain s16"),
            ({**payload["actors"]["1"], "walk_destination_box": 256}, "scalar must fit u8"),
            ({**payload["actors"]["1"], "walk_fraction": [0, 65536]}, "walk_fraction must contain u16"),
            ({**payload["actors"]["1"], "walk_delta": [0, 1 << 31]}, "walk_delta must contain s32"),
        )
        for actor, message in malformed:
            with self.subTest(message=message):
                candidate = {**payload, "actors": {"1": actor}}
                with self.assertRaisesRegex(SaveFormatError, message):
                    host.engine.load_state(host.context, json.dumps(candidate).encode("utf-8"))

    def test_c32_put_actor_at_object_walk_point_fallback_and_lifecycle(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c32_put_actor_at_object.scrp").read_bytes()
        host = self._host(fixture)
        host.engine.state.current_room = 75
        host.engine.state.room_objects = {
            100: RoomObjectState(100, 80, 60, 24, 24, 120, 80, local_index=1),
            101: RoomObjectState(101, 280, 60, 32, 24, 300, 90, local_index=2),
        }
        host.engine.state.actors = {
            1: ActorState(room=75, visible=False, position=(0, 0), moving=4),
            2: ActorState(room=76, visible=True, position=(5, 6), moving=3),
            3: ActorState(room=76, visible=False, position=(7, 8), moving=2),
        }

        host.tick()
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(first["scripts"][0]["pc"], 6)
        self.assertEqual(first["actors"]["1"]["position"], [120, 80])
        self.assertTrue(first["actors"]["1"]["visible"])
        self.assertEqual(first["actors"]["1"]["moving"], 0)
        host.save(0)
        host.engine.state.actors[1].position = (0, 0)
        host.load(0)

        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["scripts"][0]["pc"], 26)
        self.assertEqual(state["variables"], {"0": 2, "1": 101})
        self.assertEqual(state["actors"]["2"]["position"], [300, 90])
        self.assertFalse(state["actors"]["2"]["visible"])
        self.assertEqual(state["actors"]["2"]["moving"], 0)
        self.assertEqual(state["actors"]["3"]["position"], [240, 120])
        self.assertFalse(state["actors"]["3"]["visible"])
        self.assertEqual(state["actors"]["3"]["moving"], 2)
        host.tick()
        self.assertFalse(host.engine.inspect_state()["scripts"][0]["active"])

    def test_c32_put_actor_at_object_fails_closed_on_stream_and_actor(self) -> None:
        for script in (bytes((0x0E, 1)), bytes((0xCE, 0, 0, 1))):
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, "ended at offset"):
                    self._host(script).tick()
        with self.assertRaisesRegex(EngineExecutionError, "actor 32"):
            self._host(bytes((0x0E, 32, 100, 0))).tick()

    def test_c19_cutscene_fails_closed_on_stack_override_and_save(self) -> None:
        cases = (
            (bytes([0xC0]), "stack underflow"),
            (bytes([0x58, 1, 0x18]), "while reading 3 bytes"),
            (bytes([0x40, 0xFF, 0x58, 1, 0x18]), "while reading 3 bytes"),
            (bytes([0x40, 0xFF]) * 5, "stack overflow"),
            (bytes([0x40, 0xFF, 0x00]), "ended with active cutscene"),
        )
        for script, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        host = self._host(bytes([0x40, 0xFF, 0x80]))
        host.tick()
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        payload["cutscenes"][0]["override_pc"] = 1
        with self.assertRaisesRegex(SaveFormatError, "override is incomplete"):
            host.engine.load_state(host.context, json.dumps(payload).encode("utf-8"))
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        payload["cutscene_sentinel"]["override_pc"] = 1
        with self.assertRaisesRegex(SaveFormatError, "override is incomplete"):
            host.engine.load_state(host.context, json.dumps(payload).encode("utf-8"))

    def test_c20_do_sentence_operands_freeze_cancel_and_save(self) -> None:
        script = bytes(
            [
                0x1A, 0, 0, 7, 0,
                0x1A, 1, 0, 0x11, 0x11,
                0x1A, 2, 0, 0x22, 0x22,
                0x19, 1, 100, 0, 0, 0,
                0x39, 2, 101, 0, 0, 0,
                0x59, 3, 1, 0, 102, 0,
                0x79, 4, 1, 0, 2, 0,
                0x60, 1,
                0x80,
                0x60, 0,
                0x19, 0xFE,
                0x99, 0, 0, 103, 0, 0, 0,
                0xB9, 0, 0, 104, 0, 2, 0,
                0xD9, 0, 0, 1, 0, 105, 0,
                0xF9, 0, 0, 1, 0, 2, 0,
                0x60, 1,
                0x80,
            ]
        )
        host = self._host(script)
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(
            first["sentences"],
            [
                {"verb": 1, "object_a": 100, "object_b": 0, "preposition": False, "freeze_count": 1},
                {"verb": 2, "object_a": 101, "object_b": 7, "preposition": True, "freeze_count": 1},
                {"verb": 3, "object_a": 0x1111, "object_b": 102, "preposition": True, "freeze_count": 1},
                {"verb": 4, "object_a": 0x1111, "object_b": 0x2222, "preposition": True, "freeze_count": 1},
            ],
        )
        saved = host.save(0)
        host.engine.state.sentences.clear()
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["sentences"], first["sentences"])
        host.tick(pointer_buttons=((0, True),))
        second = host.engine.inspect_state()
        self.assertEqual(
            second["sentences"],
            [
                {"verb": 7, "object_a": 103, "object_b": 0, "preposition": False, "freeze_count": 1},
                {"verb": 7, "object_a": 104, "object_b": 0x2222, "preposition": True, "freeze_count": 1},
                {"verb": 7, "object_a": 0x1111, "object_b": 105, "preposition": True, "freeze_count": 1},
                {"verb": 7, "object_a": 0x1111, "object_b": 0x2222, "preposition": True, "freeze_count": 1},
            ],
        )
        self.assertEqual(second["input"]["pressed_buttons"], [])
        self.assertEqual(second["input"]["held_buttons"], ["primary"])
        self.assertEqual(saved.schema, 6)

    def test_c20_sentence_script_lifo_same_object_and_cancel(self) -> None:
        callback = bytes(
            [
                0x9A, 5, 0, 0, 0x40,
                0x9A, 6, 0, 1, 0x40,
                0x9A, 7, 0, 2, 0x40,
                0x00,
            ]
        )
        main = bytes(
            [
                0x1A, 33, 0, 10, 0,
                0x19, 5, 100, 0, 200, 0,
                0x80,
                0x00,
            ]
        )
        host = self._host(main, scripts={10: callback})
        host.tick()
        queued = host.engine.inspect_state()
        sentence_slots = [item for item in queued["scripts"] if item["number"] == 10]
        self.assertEqual(queued["sentences"], [])
        self.assertEqual(sentence_slots[0]["locals"][:3], [5, 100, 200])
        self.assertEqual(sentence_slots[0]["pc"], 0)
        host.tick()
        self.assertEqual(
            host.engine.inspect_state()["variables"],
            {"5": 5, "6": 100, "7": 200, "33": 10},
        )

        same_object = self._host(
            bytes([0x1A, 33, 0, 10, 0, 0x19, 5, 100, 0, 100, 0, 0x80]),
            scripts={10: callback},
        )
        same_object.tick()
        self.assertFalse(any(item["number"] == 10 for item in same_object.engine.inspect_state()["scripts"]))

        cancel = self._host(
            bytes([0x1A, 33, 0, 10, 0, 0x0A, 10, 0xFF, 0x19, 0xFE, 0x80]),
            scripts={10: bytes([0x80])},
        )
        cancel.tick(pointer_buttons=((0, True),))
        canceled = cancel.engine.inspect_state()
        self.assertFalse(any(item["number"] == 10 for item in canceled["scripts"]))
        self.assertEqual(canceled["input"]["pressed_buttons"], [])

    def test_c20_do_sentence_fails_closed_on_stream_capacity_and_save(self) -> None:
        for script in (bytes([0x19]), bytes([0x19, 1, 0]), bytes([0x99, 0])):
            with self.subTest(script=script.hex()):
                with self.assertRaisesRegex(EngineExecutionError, "ended at offset"):
                    self._host(script).tick()
        overflow = bytes([0x19, 1, 1, 0, 0, 0]) * 7
        with self.assertRaisesRegex(EngineExecutionError, "sentence queue overflow"):
            self._host(overflow).tick()

        host = self._host(bytes([0x19, 1, 1, 0, 0, 0, 0x60, 1, 0x80]))
        host.tick()
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        payload["sentences"][0]["preposition"] = True
        with self.assertRaisesRegex(SaveFormatError, "preposition is noncanonical"):
            host.engine.load_state(host.context, json.dumps(payload).encode("utf-8"))

    def test_c21_draw_object_operands_overlap_position_and_save(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c21_draw_object.scrp").read_bytes()
        host = self._host(script)
        host.engine.state.object_states = {102: 7}
        host.engine.state.room_objects = {
            100: RoomObjectState(100, 8, 16, 16, 24, 20, 30, local_index=1),
            101: RoomObjectState(101, 40, 48, 16, 24, 50, 60, local_index=2),
            102: RoomObjectState(102, 40, 48, 16, 24, 70, 80, 7, local_index=3),
        }
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["object_states"], {"100": 5, "101": 3, "102": 0})
        self.assertEqual(state["object_draw_queue"], [100, 101, 100])
        self.assertEqual(
            state["room_objects"]["100"],
            {
                "position": [96, 104], "size": [16, 24], "walk": [108, 118],
                "state": 5, "local_index": 1, "parent": 0, "parent_state": 0,
            },
        )
        saved = host.save(0)
        host.engine.state.object_draw_queue.clear()
        host.engine.state.room_objects[100].x = 0
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["room_objects"], state["room_objects"])
        self.assertEqual(host.engine.inspect_state()["object_draw_queue"], [100, 101, 100])
        self.assertEqual(saved.schema, 6)

    def test_c21_draw_object_fails_closed_on_stream_state_queue_and_save(self) -> None:
        cases = (
            (bytes((0x05,)), "ended at offset"),
            (bytes((0x05, 100, 0)), "ended at offset"),
            (bytes((0x05, 100, 0, 0)), "sub-op 0 is not implemented"),
            (bytes((0x05, 100, 0, 1, 2, 0)), "ended at offset"),
            (bytes((0x05, 100, 0, 2, 0, 1)), "state 256 must fit u8"),
        )
        for script, message in cases:
            with self.subTest(script=script.hex()):
                host = self._host(script)
                host.engine.state.room_objects[100] = RoomObjectState(100, 0, 0, 8, 8, 0, 0)
                with self.assertRaisesRegex(EngineExecutionError, message):
                    host.tick()

        host = self._host(bytes((0x05, 100, 0, 0xFF)))
        host.engine.state.room_objects[100] = RoomObjectState(100, 0, 0, 8, 8, 0, 0)
        host.engine.state.object_draw_queue = [100] * 200
        with self.assertRaisesRegex(EngineExecutionError, "queue overflow"):
            host.tick()

        host = self._host(bytes((0x80,)))
        host.engine.state.object_states[100] = 1
        host.engine.state.room_objects[100] = RoomObjectState(100, 0, 0, 8, 8, 0, 0, 1)
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        payload["room_objects"]["100"]["state"] = 2
        with self.assertRaisesRegex(SaveFormatError, "state is noncanonical"):
            host.engine.load_state(host.context, json.dumps(payload).encode("utf-8"))

    def test_c3_delayed_slot_does_not_starve_peer(self) -> None:
        slot0 = (ROOT / "examples/resources/scumm_v5/c3_slot0.scrp").read_bytes()
        slot1 = (ROOT / "examples/resources/scumm_v5/c3_slot1.scrp").read_bytes()
        host = self._host(slot0)
        host.engine.state.scripts.append(ScriptSlot("synthetic.slot1", slot1))
        expected = [
            (4, 2, 4, 1, 3),
            (4, 1, 4, 2, 6),
            (4, 0, 4, 3, 9),
            (8, 0, 4, 4, 14),
            (8, 0, 4, 5, 20),
        ]
        for slot0_pc, slot0_delay, slot1_pc, peer_count, operations in expected:
            host.tick()
            state = host.engine.inspect_state()
            first, second = state["scripts"]
            self.assertEqual((first["pc"], first["delay"]), (slot0_pc, slot0_delay))
            self.assertEqual(second["pc"], slot1_pc)
            self.assertEqual(state["variables"].get("11"), peer_count)
            self.assertEqual(state["operations"], operations)

    def test_c4_script_lifecycle_locals_and_slot_reuse(self) -> None:
        main = (ROOT / "examples/resources/scumm_v5/c4_lifecycle.scrp").read_bytes()
        children = {
            number: (ROOT / f"examples/resources/scumm_v5/c4_child{number}.scrp").read_bytes()
            for number in (2, 3, 4)
        }
        host = self._host(main, scripts=children)
        expected = [
            (12, True, 2, 9, True, 11, {"0": 1, "1": 10}, 6),
            (26, True, 0, 15, False, 21, {"0": 2, "1": 10, "2": 20, "3": 21}, 14),
            (35, False, 0, 6, False, 30, {"0": 2, "1": 10, "2": 20, "3": 21, "4": 30}, 19),
        ]
        for main_pc, main_active, child_number, child_pc, child_active, local0, variables, operations in expected:
            host.tick()
            state = host.engine.inspect_state()
            self.assertEqual(len(state["scripts"]), 2)
            parent, child = state["scripts"]
            self.assertEqual((parent["pc"], parent["active"]), (main_pc, main_active))
            self.assertEqual(
                (child["number"], child["pc"], child["active"], child["locals"][0]),
                (child_number, child_pc, child_active, local0),
            )
            self.assertEqual(state["variables"], variables)
            self.assertEqual(state["operations"], operations)

    def test_c4_script_slot_capacity_fails_closed(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c4_capacity.scrp").read_bytes()
        child = (ROOT / "examples/resources/scumm_v5/c4_child2.scrp").read_bytes()
        host = self._host(script, scripts={2: child})
        for number in range(32, 56):
            host.engine.state.scripts.append(ScriptSlot(f"synthetic.{number}", bytes([0x80]), number=number))
        self.assertEqual(len(host.engine.state.scripts), 25)
        with self.assertRaisesRegex(EngineExecutionError, r"capacity exhausted \(25 slots\)"):
            host.tick()

    def test_c5_recursive_freeze_resistant_scheduler_and_queries(self) -> None:
        main = (ROOT / "examples/resources/scumm_v5/c5_scheduler.scrp").read_bytes()
        children = {
            number: (ROOT / f"examples/resources/scumm_v5/c5_child{number}.scrp").read_bytes()
            for number in (5, 6, 7)
        }
        host = self._host(main, scripts=children)
        expected = [
            (11, [0, 0], [5, 5], {"0": 1, "10": 2}, 8),
            (31, [1, 1, 0], [5, 6, 7], {"0": 1, "1": 1, "2": 1, "10": 3, "11": 1, "12": 1}, 21),
            (40, [1, 1, 0], [5, 6, 7], {"0": 1, "1": 1, "2": 1, "3": 1, "10": 3, "11": 1, "12": 2}, 28),
            (51, [0, 0, 0], [5, 6, 7], {"0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "10": 4, "11": 2, "12": 3}, 41),
            (62, [0, 0, 0], [0, 0, 0], {"0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "10": 4, "11": 2, "12": 3}, 46),
        ]
        for pc, freeze_counts, numbers, variables, operations in expected:
            host.tick()
            state = host.engine.inspect_state()
            parent, *children_state = state["scripts"]
            self.assertEqual(parent["pc"], pc)
            self.assertEqual([item["freeze_count"] for item in children_state], freeze_counts)
            self.assertEqual([item["number"] for item in children_state], numbers)
            self.assertEqual(state["variables"], variables)
            self.assertEqual(state["operations"], operations)
            if pc == 31:
                assert host.context is not None
                payload = host.engine.save_state(host.context)
                host.engine.state.scripts[1].freeze_count = 0
                host.engine.state.scripts[3].freeze_resistant = False
                host.engine.load_state(host.context, payload)
                restored = host.engine.inspect_state()["scripts"]
                self.assertEqual([item["freeze_count"] for item in restored[1:]], [1, 1, 0])
                self.assertTrue(restored[3]["freeze_resistant"])
        self.assertTrue(all(not item["active"] for item in state["scripts"]))

    def test_c6_chain_script_handoff_reuses_slot_and_never_resumes_caller(self) -> None:
        main = (ROOT / "examples/resources/scumm_v5/c6_scheduler.scrp").read_bytes()
        children = {
            number: (ROOT / f"examples/resources/scumm_v5/c6_{kind}{number}.scrp").read_bytes()
            for number, kind in ((10, "chain"), (11, "chain"), (12, "target"), (13, "target"))
        }
        host = self._host(main, scripts=children)
        expected = [
            (15, 8, {"0": 111, "1": 111, "3": 1}),
            (30, 19, {"0": 111, "1": 111, "3": 1, "4": 13, "6": 1, "7": 222}),
            (43, 24, {"0": 111, "1": 111, "3": 1, "4": 13, "6": 1, "7": 222}),
        ]
        for frame, (parent_pc, operations, variables) in enumerate(expected, start=1):
            host.tick()
            state = host.engine.inspect_state()
            parent, *children_state = state["scripts"]
            self.assertEqual(parent["pc"], parent_pc)
            self.assertEqual(state["variables"], variables)
            self.assertEqual(state["operations"], operations)
            self.assertEqual(state["variables"].get("15", 0), 0)
            if frame == 1:
                self.assertEqual(len(children_state), 1)
                child = children_state[0]
                self.assertEqual((child["number"], child["pc"], child["locals"][0]), (12, 6, 111))
                self.assertTrue(child["freeze_resistant"])
                self.assertTrue(child["recursive"])
            elif frame == 2:
                self.assertEqual(len(children_state), 2)
                self.assertEqual(
                    [(item["number"], item["pc"], item["locals"][0]) for item in children_state],
                    [(12, 6, 111), (13, 6, 222)],
                )
                self.assertTrue(children_state[0]["freeze_resistant"])
                self.assertTrue(children_state[0]["recursive"])
                self.assertFalse(children_state[1]["freeze_resistant"])
                self.assertFalse(children_state[1]["recursive"])
            else:
                self.assertFalse(any(item["active"] for item in state["scripts"]))
                self.assertEqual([item["number"] for item in state["scripts"]], [0, 0, 0])

    def test_start_object_modes_varargs_and_independent_object_locals(self) -> None:
        cases = (
            # direct object/direct entry, one direct and one variable argument
            (bytes((0x37, 100, 0, 10, 0x00, 0xFE, 0xFF, 0x81, 2, 0, 0xFF, 0x00)), False),
            # variable object/variable entry, identical argument stream
            (bytes((0xF7, 0, 0, 1, 0, 0x00, 0xFE, 0xFF, 0x81, 2, 0, 0xFF, 0x00)), True),
        )
        for program, variable_modes in cases:
            with self.subTest(variable_modes=variable_modes):
                host = self._host(program)
                assert host.engine._video.room is not None
                obcd = bytes(8) + bytes((0x80, 0x00))
                item = ScummV5RoomObject(
                    100, 0, 0, 1, 1, 0, 0, 0, 0, 0,
                    verb_entries=((10, 8),), obcd=obcd,
                    obcd_room_offset=32, verb_table_offset=16, verb_table_length=4,
                )
                host.engine._video.room = replace(host.engine._video.room, objects=(item,))
                host.engine.state.variables[0] = 100
                host.engine.state.variables[1] = 10
                host.engine.state.variables[2] = 0x8001
                host.tick()
                state = host.engine.inspect_state()
                child = next(slot for slot in state["scripts"] if slot["script_kind"] == "OBCD")
                self.assertEqual(child["number"], 100)
                self.assertEqual(child["pc"], 9)
                self.assertEqual(child["locals"][:4], [-2, -32767, 0, 0])
                self.assertEqual(state["variables"]["0"], 100)
                self.assertEqual(state["variables"]["1"], 10)
                self.assertEqual(state["variables"]["2"], 0x8001)
                self.assertEqual(state["scripts"][0]["pc"], len(program))

    def test_start_object_entry_selection_failure_and_chain_namespace(self) -> None:
        # Exact entry 10 chains to room-local 200.  The earlier fallback must
        # not be selected because canonical VERB order puts the exact entry first.
        host = self._host(bytes((0x37, 100, 0, 10, 0xFF, 0x00)))
        assert host.engine._video.room is not None
        exact = bytes((0x42, 200, 0xFF))
        fallback = bytes((0x1A, 9, 0, 99, 0, 0x00))
        obcd = bytes(8) + exact + fallback
        item = ScummV5RoomObject(
            100, 0, 0, 1, 1, 0, 0, 0, 0, 0,
            verb_entries=((10, 8), (0xFF, 11)), obcd=obcd,
            obcd_room_offset=32, verb_table_offset=16, verb_table_length=7,
        )
        host.engine._video.room = replace(host.engine._video.room, objects=(item,))
        host.engine._room_scripts[200] = bytes((0x80, 0x00))
        host.tick()
        state = host.engine.inspect_state()
        chained = next(slot for slot in state["scripts"] if slot["number"] == 200)
        self.assertEqual(chained["script_kind"], "LSCR")
        self.assertEqual(chained["pc"], 1)
        self.assertFalse(any(slot["script_kind"] == "OBCD" for slot in state["scripts"]))
        self.assertNotIn("9", state["variables"])

        missing = self._host(bytes((0x37, 100, 0, 8, 0xFF, 0x00)))
        assert missing.engine._video.room is not None
        missing.engine._video.room = replace(
            missing.engine._video.room,
            objects=(replace(item, verb_entries=((10, 8),)),),
        )
        before_slots = len(missing.engine.state.scripts)
        missing.tick()
        self.assertEqual(len(missing.engine.state.scripts), before_slots)
        self.assertFalse(any(slot.script_kind == "OBCD" for slot in missing.engine.state.scripts))

        malformed = self._host(bytes((0x37, 100, 0, 10, 0x00)))
        assert malformed.engine._video.room is not None
        malformed.engine._video.room = replace(malformed.engine._video.room, objects=(item,))
        with self.assertRaisesRegex(EngineExecutionError, "ended at offset"):
            malformed.tick()
        self.assertFalse(any(slot.script_kind == "OBCD" for slot in malformed.engine.state.scripts))

    def test_c6_missing_target_retires_caller_before_failure(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c6_missing.scrp").read_bytes()
        host = self._host(script)
        with self.assertRaisesRegex(EngineExecutionError, r"script 14 has no resource binding"):
            host.tick()
        slot = host.engine.inspect_state()["scripts"][0]
        self.assertFalse(slot["active"])
        self.assertEqual(slot["number"], 0)

    def test_c6_capacity_does_not_reuse_reserved_boot_slot(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c6_capacity.scrp").read_bytes()
        target = (ROOT / "examples/resources/scumm_v5/c6_target12.scrp").read_bytes()
        host = self._host(script, scripts={12: target})
        for number in range(32, 56):
            host.engine.state.scripts.append(ScriptSlot(f"synthetic.{number}", bytes([0x80]), number=number))
        self.assertEqual(len(host.engine.state.scripts), 25)
        with self.assertRaisesRegex(EngineExecutionError, r"capacity exhausted \(25 slots\)"):
            host.tick()
        state = host.engine.inspect_state()
        self.assertFalse(state["scripts"][0]["active"])
        self.assertEqual(state["scripts"][0]["number"], 0)
        self.assertTrue(all(item["active"] for item in state["scripts"][1:]))

    def test_corrupt_save_payload_fails_closed(self) -> None:
        host = self._host(bytes([0x80, 0x18, 0xFC, 0xFF]))
        assert host.context is not None
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        payload["bits"] = [4096]
        with self.assertRaises(SaveFormatError):
            host.engine.load_state(
                host.context, json.dumps(payload).encode("utf-8")
            )

    def test_unknown_opcode_fails_loudly(self) -> None:
        host = self._host(bytes([0xA7]))
        with self.assertRaises(EngineExecutionError):
            host.tick()


if __name__ == "__main__":
    unittest.main()
