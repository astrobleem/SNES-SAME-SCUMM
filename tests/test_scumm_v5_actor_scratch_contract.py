from __future__ import annotations

import unittest
from pathlib import Path
import itertools
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


class NativeActorProviderOwnershipTests(unittest.TestCase):
    def test_code_miss_preserves_actor_request_until_consumed(self):
        from test_scumm_controller_hud_text import HudMachine, ROOT
        source = (ROOT/'runtime/snes/engines/scumm_v5_msu_programs.pasm').read_text()
        admission = source.split('ScummV5_MsuProgram_EnsureSelected_Far__find_slot:', 1)[1].split(
            'ScummV5_MsuProgram_EnsureSelected_Far__read_idle:', 1)[0]
        code = 'php\n' + admission + '''
ScummV5_MsuProgram_EnsureSelected_Far__read_idle:
    rep #$20
    lda #$0800
    sta.l SAME_MSU1_REQUEST_LENGTH
ScummV5_MsuProgram_EnsureSelected_Far__pending:
    plp
    rtl
'''
        for owner, status in itertools.product((0, 1, 2), (3, 4, 5)):
            with self.subTest(owner=owner, status=status):
                m = HudMachine(1, 1)
                m.symbols.update(SAME_SCUMM_ACTOR_SCRATCH_OWNER=0x41E7A6,
                                 SAME_SCUMM_ACTOR_SCRATCH_OWNER_ACTOR=1,
                                 SAME_MSU1_STATE_READING=4)
                m.put('SAME_SCUMM_ACTOR_SCRATCH_OWNER', owner, 1)
                m.put('SAME_MSU1_STATUS', status, 1)
                m.put('SAME_MSU1_REQUEST_LENGTH', 550, 4)
                before = dict(m.mem)
                m.code=[]; m.labels={}; m.writes=[]
                for line in code.splitlines():
                    line=line.split(';', 1)[0].strip()
                    if not line or line.startswith('.'): continue
                    if line.endswith(':'): m.labels[line[:-1]]=len(m.code)
                    else: op,_,arg=line.partition(' '); m.code.append((op,arg))
                m.run()
                blocked = owner==1 or status==4
                self.assertEqual(m.get('SAME_MSU1_REQUEST_LENGTH',4), 550 if blocked else 2048)
                if blocked:
                    self.assertEqual(m.mem, before)
                    self.assertEqual(m.writes, [])

    def test_late_code_completion_allows_actor_without_unpinning_executable(self):
        from test_scumm_controller_hud_text import HudMachine, ROOT
        programs = (ROOT/'runtime/snes/engines/scumm_v5_msu_programs.pasm').read_text()
        reconcile = programs[programs.index('ScummV5_MsuProgram_ReconcileRead_Far:'):
                             programs.index('ScummV5_MsuProgram_ReconcileRead_Far__error:')]
        touch = programs[programs.index('ScummV5_MsuProgram_TouchSlot_Far:'):
                         programs.index('ScummV5_MsuProgram_EnsureSelected_Far__find_slot:')]
        actor = (ROOT/'runtime/snes/engines/scumm_v5_controller_far.pasm').read_text()
        admission = actor.split('ScummV5_ActorPose_Ensure__provider:', 1)[1].split(
            'ScummV5_ActorPose_Ensure__find:', 1)[0]
        from test_scumm_v5_actor_damage_boundaries import camera_source
        admission=camera_source(admission, enabled=True,cels=True)
        visual = (ROOT/'runtime/snes/engines/scumm_v5_visual.pasm').read_text()
        late = visual.split('ScummV5_Visual_Frame_Far:', 1)[1].split(
            '.elseif SAME_BUILD_SCUMM_CONTROLLER_FIXTURE', 1)[0]
        self.assertLess(late.index('ScummV5_MsuProgram_ReconcileRead_Far'),
                        late.index('ScummV5_Controller_RenderActor_Far'))
        self.assertIn('bcs ScummV5_Visual_Frame__skip_actor', late)
        # Run the actual completion and admission instructions. The sentinel
        # models only the next actor request's first descriptor write.
        code = '''
    php
    jsl ScummV5_MsuProgram_ReconcileRead_Far
    bcs Test_Done
    jsl ScummV5_MsuProgram_ReconcileRead_Far
    bcs Test_Done
''' + admission + '''
ScummV5_ActorPose_Ensure__find:
    rep #$20
    lda #$0226
    sta.l SAME_MSU1_REQUEST_LENGTH
ScummV5_ActorPose_Ensure__pending:
Test_Done:
    plp
    rtl
''' + reconcile + '''
ScummV5_MsuProgram_ReconcileRead_Far__error:
    sec
    rtl
''' + touch
        ahead_release = (ROOT/'runtime/snes/engines/scumm_v5_camera_lookahead.inc.pasm').read_text().split('ScummV5_Camera_AheadRelease_Far:',1)[1].split('; C clear is a hit.',1)[0]
        ahead_release = '\nScummV5_Camera_AheadRelease_Far:\n' + ahead_release
        code += ahead_release
        for page, status, room, owner in itertools.product(range(3), (4, 5), (0, 1, 2, 3), (0, 1, 2)):
            with self.subTest(page=page, status=status, room=room, owner=owner):
                m = HudMachine(1, 1)
                m.symbols.update(SAME_MSU1_STATE_READY=3, SAME_MSU1_STATE_READING=4,
                    SAME_MSU1_STATE_READ_OK=5, SAME_MSU1_STATE_ERROR=255,
                    SCUMM_MSU_CACHE_READY=2, SCUMM_MSU_ROOM_REQUESTED=1,
                    SCUMM_MSU_ROOM_READING=2, SAME_SCUMM_ACTOR_SCRATCH_OWNER=0x41E7A6)
                for p in range(3):
                    m.put(f'SAME_SCUMM_MSU_CACHE_STATE{p}', 1 if p==page else 2, 1)
                    m.put(f'SAME_SCUMM_MSU_CACHE_PINS{p}', p+1, 1)
                    m.put(f'SAME_SCUMM_MSU_CACHE_LRU{p}', p, 1)
                    m.put(f'SAME_SCUMM_MSU_CACHE_SIZE{p}', 107)
                    m.put(f'SAME_SCUMM_MSU_CACHE_WAITER_SLOT{p}', p+5, 1)
                m.put('SAME_SCUMM_MSU_CACHE_REQUEST_SLOT', page, 1)
                m.put('SAME_SCUMM_MSU_ROOM_STATE', room, 1)
                m.put('SAME_SCUMM_ACTOR_SCRATCH_OWNER', owner, 1)
                m.put('SAME_MSU1_STATUS', status, 1)
                m.put('SAME_MSU1_REQUEST_LENGTH', 107, 4)
                m.put('SAME_FRAME_COUNTER', 10)
                m.put('SAME_SCUMM_MSU_ROOM_START_FRAME', 8)
                m.code=[]; m.labels={}; m.writes=[]
                for line in code.splitlines():
                    line=line.split(';',1)[0].strip()
                    if not line or line.startswith('.'):continue
                    if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
                    else:op,_,arg=line.partition(' ');m.code.append((op,arg))
                m.run()
                completed = status==5
                self.assertEqual(m.get('SAME_SCUMM_MSU_CACHE_REQUEST_SLOT',1),255 if completed else page)
                self.assertEqual(m.get('SAME_SCUMM_MSU_CACHE_LOADS'),int(completed))
                self.assertEqual(m.get('SAME_SCUMM_MSU_CACHE_CURRENT_BYTES'),107*int(completed))
                for p in range(3):
                    self.assertEqual(m.get(f'SAME_SCUMM_MSU_CACHE_PINS{p}',1),
                                     (p+1) | (128 if completed and p==page else 0))
                    self.assertEqual(m.get(f'SAME_SCUMM_MSU_CACHE_WAITER_SLOT{p}',1),p+5)
                admitted = completed and room not in (1,2) and owner==0
                self.assertEqual(m.get('SAME_MSU1_REQUEST_LENGTH',4),550 if admitted else 107)

    def test_completed_read_does_not_release_room_or_code_ownership(self):
        from test_scumm_controller_hud_text import HudMachine, ROOT
        source = (ROOT/'runtime/snes/engines/scumm_v5_controller_far.pasm').read_text()
        block = source.split('ScummV5_ActorPose_Ensure__provider:', 1)[1].split(
            'ScummV5_ActorPose_Ensure__find:', 1)[0]
        from test_scumm_v5_actor_damage_boundaries import camera_source
        block=camera_source(block,enabled=True,cels=True)
        # Execute the production admission instructions. The lookup sentinel
        # stands in for its first writes to the shared provider descriptor.
        block += """
ScummV5_ActorPose_Ensure__find:
    rep #$20
    lda #$0226
    sta.l SAME_MSU1_REQUEST_LENGTH
ScummV5_ActorPose_Ensure__pending:
    plp
    rtl
"""
        ahead_release = (ROOT/'runtime/snes/engines/scumm_v5_camera_lookahead.inc.pasm').read_text().split('ScummV5_Camera_AheadRelease_Far:',1)[1].split('; C clear is a hit.',1)[0]
        ahead_release = '\nScummV5_Camera_AheadRelease_Far:\n' + ahead_release
        block += ahead_release
        for provider, code_slot, room, owner in itertools.product(
                (0, 1, 2, 3, 4, 5, 255), (0, 2, 255), (0, 1, 2, 3, 255), (0, 1, 2)):
            with self.subTest(provider=provider, code=code_slot, room=room, owner=owner):
                m = HudMachine(1, 1)
                m.symbols.update(SAME_MSU1_STATE_READY=3, SAME_MSU1_STATE_READ_OK=5,
                    SCUMM_MSU_ROOM_REQUESTED=1, SCUMM_MSU_ROOM_READING=2,
                    SAME_SCUMM_ACTOR_SCRATCH_OWNER=0x41E7A6)
                m.put('SAME_MSU1_STATUS', provider, 1)
                m.put('SAME_SCUMM_MSU_CACHE_REQUEST_SLOT', code_slot, 1)
                m.put('SAME_SCUMM_MSU_ROOM_STATE', room, 1)
                m.put('SAME_SCUMM_ACTOR_SCRATCH_OWNER', owner, 1)
                m.put('SAME_MSU1_REQUEST_LENGTH', 1880, 4)
                before = dict(m.mem)
                m.code = [('php', ''), ('sep', '#$20')]; m.labels = {}; m.writes = []
                for line in block.splitlines():
                    line = line.split(';', 1)[0].strip()
                    if not line or line.startswith('.'): continue
                    if line.endswith(':'): m.labels[line[:-1]] = len(m.code)
                    else:
                        op, _, arg = line.partition(' '); m.code.append((op, arg))
                m.run()
                allowed = provider in (3, 5) and code_slot == 255 and room not in (1, 2) and owner == 0
                self.assertEqual(m.get('SAME_MSU1_REQUEST_LENGTH', 4), 550 if allowed else 1880)
                if not allowed:
                    self.assertEqual(m.mem, before)
                    self.assertEqual(m.writes, [])

if __name__ == "__main__":
    unittest.main()
