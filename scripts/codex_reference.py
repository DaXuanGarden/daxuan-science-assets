#!/usr/bin/env python3
"""Optional Codex OAuth reference adapter. Dry-run by default; never vector output."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def helper_path(explicit=None):
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        return candidate if candidate.is_file() else None
    codex_dir = Path(os.environ.get("CODEX_HOME", str(Path.home()/".codex")))
    candidates = [codex_dir/"skills/codex-gpt-image/scripts/codex_gpt_image.py", Path.home()/".agents/skills/codex-gpt-image/scripts/codex_gpt_image.py"]
    return next((path for path in candidates if path.is_file()), None)


def doctor(helper=None):
    dependency = helper_path(helper)
    if not dependency:
        return {"ok":False,"dependency_found":False,"auth_ready":False,"native_image_tool":"determined by host, not this script","generation_executed":False,"missing_evidence":"Optional codex-gpt-image dependency is not installed; native SVG work remains available"}
    probe = subprocess.run([sys.executable,str(dependency),"auth-status"],capture_output=True,text=True,timeout=20)
    return {"ok":probe.returncode==0,"dependency_found":True,"auth_ready":probe.returncode==0,"native_image_tool":"determined by host, not this script","generation_executed":False,"missing_evidence":None if probe.returncode==0 else "Codex OAuth dependency is not ready; no login or generation attempted"}


def build_command(helper, prompt, output):
    # GPT Image 2 in this dependency does not expose transparent-background mode.
    # This is a white-background reference; native SVG reconstruction removes it.
    return [sys.executable,str(helper),"generate","--prompt-file",str(prompt),"--out",str(output),"--count","1","--model","gpt-image-2","--background","opaque","--output-format","png"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doctor",action="store_true",help="Check optional dependency readiness without login/generation")
    parser.add_argument("--helper",help="Path to a reviewed local codex-gpt-image helper")
    parser.add_argument("--prompt-file"); parser.add_argument("--out")
    parser.add_argument("--execute",action="store_true",help="Actually send the authorized reference-generation request")
    parser.add_argument("--timeout",type=int,default=240)
    args=parser.parse_args()
    try:
        if args.doctor:
            result=doctor(args.helper)
            print(json.dumps(result,ensure_ascii=False,indent=2))
            return 0 if result["ok"] else 1
        if not args.prompt_file or not args.out:
            parser.error("--prompt-file and --out are required unless --doctor is used")
        prompt=Path(args.prompt_file).resolve(); output=Path(args.out).resolve()
        if not prompt.is_file(): raise ValueError("Prompt file does not exist")
        if output.exists(): raise ValueError("Reference output already exists; use a new version")
        if output.suffix.lower()!=".png": raise ValueError("Reference output must use .png")
        helper=helper_path(args.helper)
        result={"ok":True,"mode":"execute" if args.execute else "dry_run","backend":"codex-oauth-dependency","model":"gpt-image-2","background":"opaque reference; final SVG remains transparent","generation_executed":False,"svg_generated":False,"dependency_found":helper is not None}
        if not args.execute:
            result["next_step"]="Use the native image tool when exposed, or rerun with --execute only for an authorized Codex reference request. Inspect the PNG and rebuild native SVG."
        else:
            readiness=doctor(args.helper)
            if not readiness["ok"]:
                print(json.dumps({**result,"ok":False,"missing_evidence":readiness["missing_evidence"]},ensure_ascii=False,indent=2)); return 1
            output.parent.mkdir(parents=True,exist_ok=True)
            completed=subprocess.run(build_command(helper,prompt,output),capture_output=True,timeout=args.timeout)
            signature=output.read_bytes()[:8] if output.exists() else b""
            result["generation_executed"]=True
            result["ok"]=completed.returncode==0 and signature==b"\x89PNG\r\n\x1a\n"
            result["reference_saved"]=result["ok"]
            if not result["ok"]: result["error"]="Codex reference generation failed; no retry, account change, or provider fallback performed"
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if result["ok"] else 1
    except (OSError,ValueError,subprocess.SubprocessError):
        print(json.dumps({"ok":False,"error":"Optional Codex adapter failed; check the local dependency and chosen files. No automatic retry or provider fallback."}));return 2


if __name__=="__main__":
    sys.exit(main())
