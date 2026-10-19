#!/usr/bin/env python3
"""Select the active Codex image source; diagnose or execute one image request."""
from __future__ import annotations

import argparse
import base64
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit
import uuid


class BackendError(ValueError):
    pass


def load_config(path):
    if not path.is_file():
        return {}
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except ImportError:
        raise BackendError("TOML parser missing: use Python 3.11+ or install tomli for this Python")
    except (OSError, ValueError):
        raise BackendError("Codex configuration could not be parsed; no provider was guessed")


def normalize_base(value):
    u = urlsplit(value)
    if u.scheme not in {"https", "http"} or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise BackendError("Image base URL must be an HTTP(S) API base without credentials or query parameters")
    if u.scheme == "http" and u.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise BackendError("Use HTTPS for remote image providers")
    path = u.path.rstrip("/") or "/v1"
    return urlunsplit((u.scheme, u.netloc, path, "", ""))


def origin(value):
    u = urlsplit(value)
    return u.scheme, u.hostname, u.port


def resolve_route(config, env, auth=None, route="auto", base_url=None, profile=None):
    """Resolve endpoint and matching credential in memory; never forward OAuth to a relay."""
    auth = auth or {}
    selected_profile = profile or config.get("profile")
    if selected_profile and selected_profile not in config.get("profiles", {}):
        raise BackendError("Selected Codex profile does not exist")
    overlay = config.get("profiles", {}).get(selected_profile, {}) if selected_profile else {}
    provider = overlay.get("model_provider", config.get("model_provider", "openai"))
    settings = config.get("model_providers", {}).get(provider, {})
    active_base = settings.get("base_url")
    if provider == "openai" and not active_base:
        active_base = env.get("OPENAI_BASE_URL")
    explicit_base = base_url or env.get("DAXUAN_SCIENCE_IMAGE_BASE_URL")
    selected_base = explicit_base or active_base
    is_relay = bool(selected_base and urlsplit(selected_base).hostname != "api.openai.com")
    inferred = "relay" if is_relay else "official"
    if provider != "openai" and not selected_base:
        raise BackendError("The active custom provider has no API base URL")
    if route != "auto" and route != inferred:
        raise BackendError("Requested route conflicts with the active source; configure the intended source explicitly")
    result = {"selected_route": inferred, "provider": provider, "profile": selected_profile,
              "base_url": normalize_base(selected_base) if selected_base else None,
              "credential_source": None, "credential_present": False, "_secret": None}
    if inferred == "official":
        result["transport"] = "host-native-or-codex-oauth"
        return result
    result["transport"] = "openai-compatible-images"
    key = env.get("DAXUAN_SCIENCE_IMAGE_API_KEY")
    source = "image-environment" if key else None
    # A different image host needs a deliberately paired image credential.
    matching_active = bool(active_base and origin(normalize_base(active_base)) == origin(result["base_url"]))
    if not key and not matching_active:
        raise BackendError("A different image host requires DAXUAN_SCIENCE_IMAGE_API_KEY; active credentials were not forwarded")
    if not key:
        env_name = settings.get("env_key")
        if env_name and env.get(env_name):
            key, source = env[env_name], "active-provider-environment"
        elif settings.get("experimental_bearer_token"):
            key, source = settings["experimental_bearer_token"], "active-provider-bearer"
        else:
            headers = {k.lower(): v for k, v in settings.get("http_headers", {}).items()}
            env_headers = {k.lower(): v for k, v in settings.get("env_http_headers", {}).items()}
            authorization = headers.get("authorization") or env.get(env_headers.get("authorization", ""))
            if isinstance(authorization, str) and authorization.lower().startswith("bearer "):
                key, source = authorization[7:].strip(), "active-provider-authorization-header"
            elif env.get("OPENAI_API_KEY"):
                key, source = env["OPENAI_API_KEY"], "active-provider-api-key-environment"
            elif auth.get("OPENAI_API_KEY"):
                key, source = auth["OPENAI_API_KEY"], "active-provider-api-key-auth-file"
    if key and (not isinstance(key, str) or "\n" in key or "\r" in key):
        raise BackendError("Invalid credential representation")
    result.update({"_secret": key, "credential_source": source, "credential_present": bool(key)})
    return result


def public_plan(plan):
    return {k: v for k, v in plan.items() if not k.startswith("_")}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_bytes(url, headers=None, body=None, timeout=30):
    request = urllib.request.Request(url, data=body, headers=headers or {})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=timeout) as response:
            return response.read(64 * 1024 * 1024), response.status
    except urllib.error.HTTPError as exc:
        raise BackendError("Image provider returned HTTP %d; no retry or provider fallback" % exc.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        raise BackendError("Image provider network request failed; no automatic retry")


def relay_headers(plan):
    if not plan["credential_present"]:
        raise BackendError("The selected relay has no matching API credential")
    return {"Authorization": "Bearer " + plan["_secret"], "Accept": "application/json"}


def probe_models(plan):
    if plan["selected_route"] != "relay":
        return {"status": "host-or-oauth-check-required", "generation_verified": False}
    raw, status = request_bytes(plan["base_url"] + "/models", relay_headers(plan), timeout=20)
    try:
        data = json.loads(raw)
        models = [item["id"] for item in data.get("data", [])
                  if isinstance(item, dict) and isinstance(item.get("id"), str) and "image" in item["id"].lower()]
    except (ValueError, AttributeError):
        raise BackendError("Models endpoint returned an unexpected response")
    return {"status": "models-reachable", "http_status": status, "image_models": models,
            "generation_verified": False, "scope": "A model listing is not an image-generation test"}


def find_official_helper(codex_dir):
    candidates = [codex_dir/"skills/codex-gpt-image/scripts/codex_gpt_image.py",
                  Path.home()/".agents/skills/codex-gpt-image/scripts/codex_gpt_image.py"]
    return next((p for p in candidates if p.is_file()), None)


def official_status(codex_dir, native_tool=False, auth_path=None):
    if native_tool:
        return {"configuration_ready": True, "transport": "host-native", "generation_verified": False,
                "action": "Invoke the exposed native image tool; the CLI does not replace it"}
    helper = find_official_helper(codex_dir)
    if not helper:
        return {"configuration_ready": False, "transport": "codex-oauth", "generation_verified": False,
                "reason": "No host image tool declared and optional OAuth helper missing"}
    child_env = dict(os.environ)
    if auth_path:
        child_env["CODEX_AUTH_FILE"] = str(auth_path)
    run = subprocess.run([sys.executable, str(helper), "auth-status"], capture_output=True, timeout=20, env=child_env)
    return {"configuration_ready": run.returncode == 0, "transport": "codex-oauth", "generation_verified": False,
            "reason": None if run.returncode == 0 else "Optional OAuth helper is not ready; this says nothing about relay availability"}


def png_facts(raw):
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise BackendError("Provider output is not a PNG image")
    try:
        from PIL import Image
        with Image.open(BytesIO(raw)) as image:
            image.load()
            alpha = image.getchannel("A") if "A" in image.getbands() else None
            zeros = alpha.histogram()[0] if alpha else 0
            return {"mode": image.mode, "size": list(image.size), "has_alpha": alpha is not None,
                    "transparent_pixels": zeros, "transparent_canvas": bool(alpha and zeros and alpha.getbbox()),
                    "alpha_extrema": list(alpha.getextrema()) if alpha else None}
    except ImportError:
        raise BackendError("Pillow is required to verify image output")
    except (OSError, ValueError):
        raise BackendError("PNG decoding failed")


def download_payload(data, plan):
    try:
        item = data["data"][0]
        if item.get("b64_json"):
            return base64.b64decode(item["b64_json"], validate=True)
        url = item["url"]
        u = urlsplit(url)
        if u.scheme != "https" or not u.hostname or u.username or u.password:
            raise BackendError("Provider download URL must use HTTPS without URL credentials")
        headers = relay_headers(plan) if origin(url) == origin(plan["base_url"]) else {}
        # Same-host protected downloads retain auth; CDN downloads never receive it.
        raw, _ = request_bytes(url, headers, timeout=120)
        return raw
    except (KeyError, IndexError, TypeError, ValueError):
        raise BackendError("Provider response contains no usable image payload")


def relay_generate(plan, prompt, model, background, images, size, quality, timeout):
    fields = {"model": model, "prompt": prompt, "n": 1, "background": background, "output_format": "png"}
    if size:
        fields["size"] = size
    if quality:
        fields["quality"] = quality
    headers = relay_headers(plan)
    endpoint = "/images/edits" if images else "/images/generations"
    if images:
        boundary = "science-asset-" + uuid.uuid4().hex
        parts = []
        for key, value in fields.items():
            parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, key, value)).encode())
        for i, path in enumerate(images):
            mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(path.suffix.lower())
            if not mime:
                raise BackendError("Reference images must be PNG, JPEG or WebP")
            head = '--%s\r\nContent-Disposition: form-data; name="image[]"; filename="reference-%d%s"\r\nContent-Type: %s\r\n\r\n' % (boundary, i, path.suffix, mime)
            parts.extend([head.encode(), path.read_bytes(), b"\r\n"])
        parts.append(("--%s--\r\n" % boundary).encode())
        body = b"".join(parts)
        headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
    else:
        body = json.dumps(fields).encode()
        headers["Content-Type"] = "application/json"
    raw, status = request_bytes(plan["base_url"] + endpoint, headers, body, timeout)
    try:
        data = json.loads(raw)
    except ValueError:
        raise BackendError("Image endpoint returned non-JSON data")
    return download_payload(data, plan), status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--auth-file", type=Path)
    parser.add_argument("--profile")
    parser.add_argument("--route", choices=("auto", "official", "relay"), default="auto")
    parser.add_argument("--base-url")
    parser.add_argument("--doctor", action="store_true")
    parser.add_argument("--probe", action="store_true", help="GET models only; no generation")
    parser.add_argument("--native-tool", action="store_true", help="Declare only an image tool actually exposed by the host")
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--image", type=Path, action="append", default=[])
    parser.add_argument("--model", default=os.environ.get("DAXUAN_SCIENCE_IMAGE_MODEL", "gpt-image-2"))
    parser.add_argument("--background", choices=("opaque", "transparent", "auto"), default="opaque")
    parser.add_argument("--size")
    parser.add_argument("--quality", choices=("auto", "low", "medium", "high"))
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--timeout", type=int, default=240)
    args = parser.parse_args()
    result = {"ok": False, "generation_request_sent": False, "image_saved": False}
    try:
        if args.report and args.report.exists():
            raise BackendError("Report already exists; choose a new report filename before making a request")
        codex_dir = Path(os.environ.get("CODEX_HOME", str(Path.home()/".codex")))
        config = load_config(args.config or codex_dir/"config.toml")
        auth_path = args.auth_file or Path(os.environ.get("CODEX_AUTH_FILE", str(codex_dir/"auth.json")))
        plan = resolve_route(config, os.environ, {}, args.route, args.base_url, args.profile)
        # Only read the selected auth JSON if relay API-key fallback is needed.
        # Official auth is handled by the host/helper; OAuth tokens never go to relays.
        if plan["selected_route"] == "relay" and not plan["credential_present"] and auth_path.is_file():
            auth = json.loads(auth_path.read_text())
            plan = resolve_route(config, os.environ, auth, args.route, args.base_url, args.profile)
        result.update(public_plan(plan))
        result["generation_verified"] = False
        if args.doctor:
            status = ({"configuration_ready": plan["credential_present"], "generation_verified": False}
                      if plan["selected_route"] == "relay" else official_status(codex_dir, args.native_tool, auth_path))
            result.update(status)
            if args.probe:
                result["probe"] = probe_models(plan)
            result["ok"] = status["configuration_ready"]
        else:
            if args.probe:
                raise BackendError("Use --probe with --doctor")
            if not args.prompt_file or not args.out:
                raise BackendError("--prompt-file and --out are required for an image plan")
            prompt = args.prompt_file.read_text(encoding="utf-8").strip()
            if not prompt or len(prompt) > 32000:
                raise BackendError("Prompt must contain 1–32000 characters")
            if args.out.suffix.lower() != ".png" or args.out.exists():
                raise BackendError("Choose a new PNG output filename; existing files are preserved")
            for image in args.image:
                if not image.is_file() or image.stat().st_size > 20_000_000:
                    raise BackendError("A reference image is missing or exceeds 20 MB")
            if args.timeout < 1 or args.timeout > 600:
                raise BackendError("Request timeout must be between 1 and 600 seconds")
            result.update({"ok": True, "mode": "execute" if args.execute else "dry_run", "model": args.model,
                           "background": args.background, "references": len(args.image), "output": args.out.name,
                           "requested_size": args.size, "requested_quality": args.quality})
            if args.execute:
                if plan["selected_route"] == "official":
                    status = official_status(codex_dir, args.native_tool, auth_path)
                    if args.native_tool or not status["configuration_ready"]:
                        raise BackendError("Use the exposed native image tool, or configure the optional OAuth helper")
                    if args.background == "transparent" and args.model == "gpt-image-2":
                        raise BackendError("This OAuth helper/model supports opaque references; reconstruct SVG for final transparency")
                    helper = find_official_helper(codex_dir)
                    command = [sys.executable, str(helper), "generate", "--prompt-file", str(args.prompt_file),
                               "--out", str(args.out), "--model", args.model, "--background", args.background,
                               "--count", "1", "--output-format", "png"]
                    for image in args.image:
                        command.extend(["--image", str(image)])
                    for key in ("size", "quality"):
                        if getattr(args, key):
                            command.extend(["--"+key.replace("_", "-"), getattr(args, key)])
                    result["generation_request_sent"] = True
                    child_env = dict(os.environ)
                    child_env["CODEX_AUTH_FILE"] = str(auth_path)
                    run = subprocess.run(command, capture_output=True, timeout=args.timeout, env=child_env)
                    if run.returncode or not args.out.is_file():
                        raise BackendError("Optional OAuth generation failed; no account or provider change")
                    raw = args.out.read_bytes()
                else:
                    relay_headers(plan)
                    result["generation_request_sent"] = True
                    raw, http_status = relay_generate(plan, prompt, args.model, args.background, args.image,
                                                     args.size, args.quality, args.timeout)
                    result["http_status"] = http_status
                facts = png_facts(raw)
                if args.background == "transparent" and not facts["transparent_canvas"]:
                    raise BackendError("Provider returned an opaque image for a transparency request; no retry")
                if plan["selected_route"] == "relay":
                    args.out.parent.mkdir(parents=True, exist_ok=True)
                    with args.out.open("xb") as stream:
                        stream.write(raw)
                result.update({"image_saved": True, "generation_verified": True, "png": facts,
                               "image_sha256": hashlib.sha256(raw).hexdigest()})
    except (BackendError, OSError, ValueError, subprocess.SubprocessError) as exc:
        result.update({"ok": False, "error": str(exc) if isinstance(exc, BackendError)
                       else "Local image adapter failed; account output was suppressed"})
    encoded = json.dumps(result, indent=2)+"\n"
    if args.report:
        try:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            with args.report.open("x", encoding="utf-8") as stream:
                stream.write(encoded)
        except OSError:
            print(json.dumps({"ok": False, "error": "Report already exists or cannot be written; inspect completed image separately"}))
            return 2
    print(encoded, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
