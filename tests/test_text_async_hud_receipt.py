"""Accepted HUD work is not a BUSY rejection or a visible-frame claim."""
import re
import unittest
from test_scumm_camera_native_copy import StripMachine, ROOT


def load(m,source):
    m.code=[];m.labels={}
    for raw in source.splitlines():
        line=raw.split(';')[0].strip()
        if not line or line.startswith('.'):continue
        if line.endswith(':'):m.labels[line[:-1]]=len(m.code)
        else:m.code.append(line)


def accepted(hud,old=False):
    m=StripMachine()
    m.symbols.update(SAME_VIDEO_TEXT_STATE=0x400780,SAME_OVERLAY_STATE=0x400780,
                     SAME_OVERLAY_CURRENT_GENERATION=0x400782,SAME_OVERLAY_COMMITTED_GENERATION=0x400784)
    text=(ROOT/'runtime/snes/services/video_overlay_indexed.inc.pasm').read_text()
    for name,offset in re.findall(r'^(SAME_TEXT_\w+) = SAME_VIDEO_TEXT_STATE\+\$([0-9A-F]+)',text,re.M):
        m.symbols[name]=m.symbols['SAME_VIDEO_TEXT_STATE']+int(offset,16)
    body=text.split('Same_Text_Show_valid:',1)[1].split('; Called by the service frame hook',1)[0]
    if old:body=body[:body.index('    ; A validated HUD request')]+ '    jmp Same_Text_busy\n'
    footer=text.split('Same_Text_success:',1)[1].split('\n    rtl',1)[0]+'\n    rtl'
    load(m,'php\nrep #$30\npha\nphx\nphy\n'+body+'\nSame_Text_success:\n'+footer)
    m.put('SAME_VIDEO_TEXT_CONTROLLER_VALID',hud,1)
    m.put('SAME_SCUMM_TALK_GENERATION',9)
    m.put('SAME_VIDEO_SURFACE_ROOM',17)
    m.put('SAME_VIDEO_SURFACE_ROOM_GENERATION',4)
    m.consume()
    return m


class AsyncHudReceiptTests(unittest.TestCase):
    def test_hud_acceptance_and_talk_wait_are_not_presentation_acknowledgements(self):
        for hud,status in ((0,1),(1,0)):
            m=accepted(hud)
            self.assertEqual(m.get('SAME_SCUMM_TALK_VISUAL_STATUS',1),status)
            self.assertEqual(m.get('SAME_OVERLAY_STATE'),2) # queued, not drawn
            self.assertEqual(m.get('SAME_TEXT_TALK_GENERATION'),9)
            self.assertEqual(m.get('SAME_TEXT_ROOM'),17)
            self.assertEqual(m.get('SAME_TEXT_ROOM_GENERATION'),4)
            self.assertEqual(m.get('SAME_TEXT_VISIBLE'),0)
            self.assertEqual(m.get('SAME_OVERLAY_COMMITTED_GENERATION'),0)

    def controller(self,old=False):
        m=StripMachine();m.calls=[];m.service_writes=[]
        text=(ROOT/'runtime/snes/engines/scumm_v5_controller_far.pasm').read_text()
        body=text.split('ScummV5_Controller_Frame__hud:',1)[1].split('ScummV5_Controller_Frame__done:',1)[0]
        load(m,body+'\nScummV5_Controller_Frame__done:\nrtl')
        m.put('SAME_SCUMM_CONTROLLER_HUD_DIRTY',1,1)
        receipt=accepted(1,old).get('SAME_SCUMM_TALK_VISUAL_STATUS',1)
        def service(name,p,a):
            self.assertEqual(name,'ScummV5_Controller_ShowHud_Far');m.calls.append(name)
            # First two attempts are genuinely refused by an older request.
            m.put('SAME_SCUMM_TALK_VISUAL_STATUS',1 if len(m.calls)<=2 else receipt,1)
            return p,a
        m.service=service
        return m

    def test_busy_retry_ends_after_one_accepted_request_even_across_completion(self):
        m=self.controller()
        for frame in range(20):m.consume()
        self.assertEqual(len(m.calls),3) # two refusals, one accepted request
        self.assertEqual(m.get('SAME_SCUMM_CONTROLLER_HUD_DIRTY',1),0)
        # A later real content change still queues a new caption.
        m.put('SAME_SCUMM_CONTROLLER_HUD_DIRTY',1,1);m.consume()
        self.assertEqual(len(m.calls),4)
        old=self.controller(old=True)
        for frame in range(20):old.consume()
        self.assertEqual(len(old.calls),20) # reproduces repeated accepted work
