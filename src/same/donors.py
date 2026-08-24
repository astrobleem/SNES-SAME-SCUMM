"""Safe inventory/import tooling for Chad's existing SAME donor projects."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
from collections.abc import Mapping
from typing import Iterable

from .errors import DonorError


@dataclass(frozen=True, slots=True)
class DonorSpec:
    name: str
    repository: str
    default_posix_path: str
    default_windows_path: str
    required_ancestor: str | None
    include: tuple[str, ...]

    def default_path(
        self,
        *,
        platform: str | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> Path:
        """Return the workstation default, with an explicit environment override."""

        environ = os.environ if environ is None else environ
        override = environ.get(f"SAME_DONOR_{self.name.upper()}_PATH")
        if override:
            return Path(override)
        platform = os.name if platform is None else platform
        return Path(
            self.default_windows_path if platform == "nt" else self.default_posix_path
        )


DONORS: dict[str, DonorSpec] = {
    "bor": DonorSpec(
        name="bor",
        repository="astrobleem/snes-bor",
        default_posix_path="/home/chad/snes-bor",
        default_windows_path=r"E:\gh\snes-bor",
        required_ancestor=None,
        include=(
            "src/core/input.pasm",
            "src/core/dma.pasm",
            "src/core/dma_channel.pasm",
            "src/core/nmi.pasm",
            "src/core/oam.pasm",
            "src/core/screen.pasm",
            "src/core/stream_cache.pasm",
            "src/core/stream_cache_fp.pasm",
            "soundwork/tad/port/**",
            "tools/rom_audit/**",
        ),
    ),
    "monkey": DonorSpec(
        name="monkey",
        repository="astrobleem/SNES-SuperMonkeyIsland",
        default_posix_path="/home/chad/SNES-SuperMonkeyIsland",
        default_windows_path=r"E:\gh\SNES-SuperMonkeyIsland",
        required_ancestor=None,
        include=(
            "src/core/**",
            "src/object/scummvm/**",
            "tools/scumm/**",
            "tools/gen_dispatch_table.py",
            "tools/scumm_opcode_audit.py",
            "tests/scumm_vm/**",
            "tests/integration/**",
            "docs/v5_behavior_matrix.md",
            "CLAUDE.md",
            "HANDOFF.md",
        ),
    ),
    "scummvm": DonorSpec(
        name="scummvm",
        repository="scummvm/scummvm",
        default_posix_path="/home/chad/scummvm",
        default_windows_path=r"E:\gh\scummvm",
        required_ancestor=None,
        include=(
            "common/system.h",
            "engines/engine.h",
            "engines/scumm/script_v5.cpp",
            "engines/scumm/scumm_v5.h",
            "engines/agi/opcodes.cpp",
            "engines/agi/op_cmd.cpp",
            "engines/agi/logic.cpp",
            "engines/agi/picture.cpp",
        ),
    ),
    "superman": DonorSpec(
        name="superman",
        repository="astrobleem/supermn-snes",
        default_posix_path="/home/chad/supermn-snes",
        default_windows_path=r"E:\gh\supermn-snes",
        required_ancestor=None,
        include=(
            "src/interp.pasm",
            "src/escbank*.pasm",
            "src/main.pasm",
            "tools/mame-trace/**/*.py",
            "tools/**/optest*",
            "docs/toolchain/**",
        ),
    ),
    "blacktiger": DonorSpec(
        name="blacktiger",
        repository="astrobleem/blktiger-snes",
        default_posix_path="/home/chad/blktiger-snes",
        default_windows_path=r"E:\gh\blktiger-snes",
        required_ancestor=None,
        include=(
            "src/**/*z80*",
            "src/interp*.pasm",
            "tools/**/*z80*",
            "tools/mame-trace/**/*.py",
            "docs/toolchain/**",
            "handoff.md",
            "theplan.md",
        ),
    ),
    "poppy": DonorSpec(
        name="poppy",
        repository="astrobleem/poppy",
        default_posix_path="/home/chad/poppy",
        default_windows_path=r"E:\gh\poppy-astrobleem",
        required_ancestor="ec005c196eedabf7d0c25ff6336398c427dd43ac",
        include=(),
    ),
}


def _git(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *arguments],
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise DonorError("git is not installed") from exc
    except subprocess.CalledProcessError as exc:
        raise DonorError(
            f"git -C {root} {' '.join(arguments)} failed: {exc.stderr.strip()}"
        ) from exc


def _normalized_remote(remote: str) -> str:
    return remote.lower().removesuffix(".git").replace(":", "/")


def identify(spec: DonorSpec, root: Path) -> dict[str, object]:
    root = root.expanduser().resolve()
    if not (root / ".git").exists():
        raise DonorError(f"{root} is not a Git checkout")
    remote = _git(root, "config", "--get", "remote.origin.url").stdout.strip()
    if spec.repository.lower() not in _normalized_remote(remote):
        raise DonorError(
            f"{root} origin is {remote!r}; expected repository {spec.repository}"
        )
    head = _git(root, "rev-parse", "HEAD").stdout.strip()
    if spec.required_ancestor:
        result = _git(
            root,
            "merge-base",
            "--is-ancestor",
            spec.required_ancestor,
            "HEAD",
            check=False,
        )
        if result.returncode != 0:
            raise DonorError(
                f"{spec.name} HEAD {head} does not contain required ancestor "
                f"{spec.required_ancestor}"
            )
    status = _git(root, "status", "--porcelain").stdout.splitlines()
    return {
        "name": spec.name,
        "repository": spec.repository,
        "path": str(root),
        "head": head,
        "dirty": bool(status),
        "dirty_paths": status,
        "required_ancestor": spec.required_ancestor,
    }


def _matches(root: Path, patterns: Iterable[str]) -> list[Path]:
    files: set[Path] = set()
    for pattern in patterns:
        for match in root.glob(pattern):
            if match.is_file() and ".git" not in match.parts:
                files.add(match)
    return sorted(files)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_reference(spec: DonorSpec, root: Path, destination: Path) -> dict[str, object]:
    identity = identify(spec, root)
    if not spec.include:
        return {**identity, "files": [], "note": "identity-only donor"}
    files = _matches(root.resolve(), spec.include)
    if not files:
        raise DonorError(f"{spec.name}: no files matched the configured donor patterns")
    donor_destination = destination / spec.name
    if donor_destination.exists():
        shutil.rmtree(donor_destination)
    records = []
    for source in files:
        relative = source.relative_to(root.resolve())
        target = donor_destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        records.append(
            {
                "path": relative.as_posix(),
                "bytes": source.stat().st_size,
                "sha256": sha256(source),
            }
        )
    result = {**identity, "files": records}
    donor_destination.mkdir(parents=True, exist_ok=True)
    (donor_destination / "SAME_DONOR_MANIFEST.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def donor_paths(overrides: dict[str, Path] | None = None) -> dict[str, Path]:
    overrides = overrides or {}
    return {
        name: overrides.get(name, spec.default_path())
        for name, spec in DONORS.items()
    }
