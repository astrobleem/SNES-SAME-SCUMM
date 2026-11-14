#!/usr/bin/env python3
"""One bounded Linux diagnostic, with a private Xvfb display and no retries.

Wrap the EXISTING validator, which remains the ONLY MCP client and launches
Nexen with its existing arguments. This wrapper never opens the MCP socket.
It records process completion, NOT graphics/emulator acceptance.
Descendants are tracked by PID+starttime, including children using setsid.
"""
from __future__ import annotations
import argparse
import ctypes
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


def _proc_table() -> dict[int, tuple[int, int]]:
    rows = {}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
            rows[int(entry.name)] = (int(fields[1]), int(fields[19]))  # PPID, start ticks
        except (OSError, ValueError, IndexError):
            pass
    return rows


def _descendants(parent: int) -> dict[int, int]:
    table = _proc_table()
    parents = {parent}
    known: dict[int, int] = {}
    while True:
        found = {pid: start for pid, (ppid, start) in table.items()
                 if ppid in parents and pid not in known and pid != parent}
        if not found:
            return known
        known.update(found)
        parents = set(found)


def _signal_known(known: dict[int, int], sig: int) -> None:
    table = _proc_table()
    for pid, start in list(known.items()):
        if pid == os.getpid() or table.get(pid, (None, None))[1] != start:
            continue
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass


def _set_subreaper() -> None:
    # Adopt orphaned grandchildren so a daemonized emulator is still owned.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), 'cannot establish child ownership')


def run_once(command: list[str], out: Path, *, seconds: float = 600,
             use_xvfb: bool = True, grace: float = 2.0) -> int:
    if not sys.platform.startswith('linux'):
        raise RuntimeError('this supervisor requires Linux /proc and subreaper support')
    if not command or not 0.05 <= seconds <= 600:
        raise ValueError('provide one command and a deadline of 0.05..600 seconds')
    out.mkdir(parents=True, exist_ok=False)  # Do not overwrite an earlier attempt.
    _set_subreaper()
    env = os.environ.copy()
    env.pop('DISPLAY', None)
    env.pop('XAUTHORITY', None)
    env['PYTHONUNBUFFERED'] = '1'
    env['LIBGL_ALWAYS_SOFTWARE'] = '1'
    # This is a new X11 display, not a dependency on a stale Wayland session.
    if use_xvfb:
        missing = [name for name in ('Xvfb', 'xvfb-run', 'xauth') if not shutil.which(name)]
        if missing:
            (out / 'preflight.json').write_text(json.dumps({'missing': missing}, indent=2))
            raise RuntimeError('install the missing display tools through the normal permission flow: '
                               + ', '.join(missing))
        env.pop('WAYLAND_DISPLAY', None)
        env['GDK_BACKEND'] = 'x11'
        argv = ['xvfb-run', '--auto-servernum', '--server-args=-screen 0 1024x768x24 -nolisten tcp',
                '--', *command]
    else:
        argv = command
    # No SDL_AUDIODRIVER=dummy: suppressing audio would invalidate audio claims.
    if seconds < 2 * grace + 0.05:
        grace = min(grace, seconds / 8)
    work_seconds = max(0.01, seconds - 2 * grace - min(1.0, seconds / 8))
    began = time.monotonic()
    known: dict[int, int] = {}
    timed_out = interrupted = False
    result: int | None = None
    signal_events: list[dict] = []
    cleanup_survivors: list[dict] = []
    child = None
    # SIGTERM is a normal supervisor stop, not permission to orphan Xvfb or
    # a detached emulator. Convert it to the same bounded cleanup as Ctrl-C.
    def interrupted_by_signal(signum, frame):
        signal_events.append({
            'number': signum, 'name': signal.Signals(signum).name,
            'elapsed_seconds': round(time.monotonic() - began, 6),
            'supervisor_pid': os.getpid(),
            'direct_child_pid': None if child is None else child.pid,
            'direct_child_returncode': None if child is None else child.poll(),
            # Python's signal handler does not expose siginfo.si_pid/si_uid.
            'sender': 'NOT_CAPTURED',
        })
        raise KeyboardInterrupt
    previous_signals = {sig: signal.signal(sig, interrupted_by_signal)
                        for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        log = (out / 'process.log').open('wb')
        with log:
            child = None
            try:
                child = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT,
                                         start_new_session=True)
                while True:
                    known.update(_descendants(os.getpid()))
                    result = child.poll()
                    if result is not None:
                        break
                    if time.monotonic() - began >= work_seconds:
                        timed_out = True
                        break
                    time.sleep(min(0.05, seconds / 4))
            except KeyboardInterrupt:
                interrupted = True
            finally:
                # A second termination request cannot interrupt descendant cleanup.
                for sig in previous_signals:
                    signal.signal(sig, signal.SIG_IGN)
                known.update(_descendants(os.getpid()))
                _signal_known(known, signal.SIGTERM)
                deadline = time.monotonic() + grace
                while time.monotonic() < deadline:
                    known.update(_descendants(os.getpid()))
                    table = _proc_table()
                    alive = [pid for pid, start in known.items()
                             if table.get(pid, (None, None))[1] == start]
                    if not alive:
                        break
                    if child is not None:
                        child.poll()
                    time.sleep(0.025)
                _signal_known(known, signal.SIGKILL)
                try:
                    if child is not None:
                        child.wait(timeout=grace)
                except subprocess.TimeoutExpired:
                    pass
                # Reap adopted children; never wait indefinitely.
                deadline = time.monotonic() + grace
                while time.monotonic() < deadline:
                    try:
                        pid, _ = os.waitpid(-1, os.WNOHANG)
                    except ChildProcessError:
                        break
                    if pid == 0:
                        time.sleep(0.025)
                    else:
                        known.pop(pid, None)
                table = _proc_table()
                cleanup_survivors = [
                    {'pid': pid, 'start_ticks': start}
                    for pid, start in known.items()
                    if table.get(pid, (None, None))[1] == start
                ]
    finally:
        for sig, handler in previous_signals.items():
            signal.signal(sig, handler)
    exit_code = 124 if timed_out else 130 if interrupted else int(result if result is not None else 1)
    report = {
        'schema': 'astra-diagnostic-process-v1',
        'command': command,
        'private_xvfb': use_xvfb,
        'deadline_seconds': seconds,
        'elapsed_seconds': round(time.monotonic() - began, 3),
        'exit_code': exit_code,
        'timed_out': timed_out,
        'interrupted': interrupted,
        'attempts': 1,
        'termination_reason': ('supervisor_deadline' if timed_out else
                               'supervisor_signal' if signal_events else
                               'supervisor_interrupt_without_signal_record' if interrupted else
                               'validator_signal' if result is not None and result < 0 else
                               'normal_exit' if result == 0 else 'validator_failure'),
        'signals': signal_events,
        'validator_returncode_before_cleanup': result,
        'direct_child_returncode_after_cleanup': None if child is None else child.returncode,
        'cleanup_survivors': cleanup_survivors,
        'cleanup_complete': not cleanup_survivors,
        'native_acceptance': 'NOT_INFERRED_FROM_PROCESS_EXIT',
        'scope': 'Read the actual validator report; exit zero is not image correctness.'
    }
    (out / 'process-result.json').write_text(json.dumps(report, indent=2) + '\n')
    return exit_code


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-dir', type=Path, required=True)
    p.add_argument('--seconds', type=float, default=600)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    return run_once(command, a.run_dir, seconds=a.seconds,
                    use_xvfb=True)

if __name__ == '__main__':
    raise SystemExit(main())
