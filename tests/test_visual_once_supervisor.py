"""Process supervision only. These tests do not launch an emulator."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VisualSupervisorTests(unittest.TestCase):
    def run_command(self, root, command, seconds=5):
        runner = ('import sys;sys.path.insert(0,' + repr(str(ROOT/'tools')) + ');'
                  'from run_visual_once import run_once;from pathlib import Path;'
                  'raise SystemExit(run_once(sys.argv[2:],Path(sys.argv[1]),'
                  f'seconds={seconds},use_xvfb=False,grace=0.25))')
        return subprocess.Popen([sys.executable, '-c', runner, str(root), *command],
                                env={**os.environ, 'DISPLAY': 'user-desktop:0', 'XAUTHORITY': '/private/user-cookie'},
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def test_no_desktop_environment_is_inherited(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'run'
            p = self.run_command(root, [sys.executable, '-c',
                'import os;assert "DISPLAY" not in os.environ;assert "XAUTHORITY" not in os.environ'])
            out, err = p.communicate(timeout=8)
            self.assertEqual(p.returncode, 0, err)
            self.assertEqual(json.loads((root/'process-result.json').read_text())['attempts'], 1)

    def test_sigterm_cleans_detached_descendant(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'run'; pid_file = Path(d)/'child.pid'
            child = ('import os,time,signal;from pathlib import Path;'
                     'signal.signal(signal.SIGTERM,signal.SIG_IGN);'
                     f'Path({str(pid_file)!r}).write_text(str(os.getpid()));time.sleep(30)')
            parent = ('import subprocess,sys,time;'
                      f'subprocess.Popen([sys.executable,"-c",{child!r}],start_new_session=True);'
                      'time.sleep(30)')
            p = self.run_command(root, [sys.executable, '-c', parent])
            try:
                deadline = time.monotonic()+4
                while not pid_file.exists() and time.monotonic()<deadline: time.sleep(.02)
                self.assertTrue(pid_file.exists())
                child_pid = int(pid_file.read_text())
                p.send_signal(signal.SIGTERM)
                out, err = p.communicate(timeout=5)
                self.assertEqual(p.returncode, 130, err)
                self.assertFalse(Path(f'/proc/{child_pid}').exists())
                report=json.loads((root/'process-result.json').read_text())
                self.assertTrue(report['interrupted'])
                self.assertEqual(report['termination_reason'],'supervisor_signal')
                self.assertEqual(report['signals'][0]['name'],'SIGTERM')
                self.assertEqual(report['signals'][0]['sender'],'NOT_CAPTURED')
                self.assertTrue(report['cleanup_complete'])
            finally:
                if p.poll() is None:
                    p.send_signal(signal.SIGTERM);p.communicate(timeout=5)

    def test_deadline_is_not_retried(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'run'
            p=self.run_command(root,[sys.executable,'-c','import time;time.sleep(30)'],seconds=.5)
            out,err=p.communicate(timeout=4)
            self.assertEqual(p.returncode,124,err)
            report=json.loads((root/'process-result.json').read_text())
            self.assertTrue(report['timed_out']);self.assertEqual(report['attempts'],1)

    def test_observer_failure_is_distinct_from_signal_and_deadline(self):
        for code in (0,7):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as d:
                root=Path(d)/'run'
                p=self.run_command(root,[sys.executable,'-c',f'raise SystemExit({code})'])
                _,err=p.communicate(timeout=8)
                self.assertEqual(p.returncode,code,err)
                report=json.loads((root/'process-result.json').read_text())
                self.assertEqual(report['termination_reason'],'normal_exit' if code==0 else 'validator_failure')
                self.assertEqual(report['validator_returncode_before_cleanup'],code)
                self.assertEqual(report['signals'],[])
                self.assertTrue(report['cleanup_complete'])
