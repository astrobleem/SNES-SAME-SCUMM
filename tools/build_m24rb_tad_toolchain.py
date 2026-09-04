#!/usr/bin/env python3
"""Build pinned TAD with accepted M24R-A plus M24R-B content marker."""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
COMMIT="822164b09cb3d4750bd4c1960a430dc35b6ae04a"
def sha(path: Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--donor",type=Path,default=Path("/home/chad/terrific-audio-driver")); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    donor,out=a.donor.resolve(),a.output.resolve()
    if subprocess.check_output(["git","rev-parse","HEAD"],cwd=donor,text=True).strip()!=COMMIT: raise RuntimeError("TAD donor commit differs")
    if out.exists(): shutil.rmtree(out)
    shutil.copytree(donor,out,ignore=shutil.ignore_patterns("target",".git"))
    patches=[ROOT/"audio/m24ra/terrific_audio_driver_m24ra.patch",ROOT/"audio/m24rb/terrific_audio_driver_m24rb_content.patch"]
    for patch in patches:
        with patch.open("rb") as stream: subprocess.run(["patch","-p1"],cwd=out,stdin=stream,check=True)
    subprocess.run(["cargo","build","--release","-p","tad-compiler"],cwd=out,check=True)
    compiler=out/"target/release/tad-compiler"
    report={"schema":"same_m24rb_tad_toolchain_v1","donor_commit":COMMIT,
            "patches":[{"path":str(x.relative_to(ROOT)),"sha256":sha(x)} for x in patches],
            "compiler_sha256":sha(compiler),"accepted_primitive":"M24R-A","new_async_features":0}
    (out/"same-m24rb-toolchain.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    return 0
if __name__=="__main__": raise SystemExit(main())
