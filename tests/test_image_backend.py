import base64
from io import BytesIO
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("image_backend", ROOT/"scripts/image_backend.py")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


def config(base="https://relay.example", **settings):
    return {"model_provider": "relay", "model_providers": {
        "relay": {"base_url": base, **settings}}}


class ImageBackendTests(unittest.TestCase):
    def test_active_bearer_provider_works_without_auth_json(self):
        plan = backend.resolve_route(config(experimental_bearer_token="fixture-secret"), {})
        self.assertEqual(plan["selected_route"], "relay")
        self.assertEqual(plan["base_url"], "https://relay.example/v1")
        self.assertTrue(plan["credential_present"])
        self.assertNotIn("fixture-secret", json.dumps(backend.public_plan(plan)))

    def test_active_provider_environment_key(self):
        plan = backend.resolve_route(config(env_key="FIXTURE_IMAGE_KEY"), {"FIXTURE_IMAGE_KEY": "fixture-secret"})
        self.assertEqual(plan["credential_source"], "active-provider-environment")

    def test_oauth_is_never_used_as_relay_credential(self):
        plan = backend.resolve_route(config(), {}, {"tokens": {"access_token": "private-oauth"}})
        self.assertFalse(plan["credential_present"])
        with self.assertRaises(backend.BackendError):
            backend.relay_headers(plan)

    def test_official_does_not_pick_a_random_relay(self):
        plan = backend.resolve_route({}, {"DAXUAN_IMAGE_RELAY_API_KEY": "unrelated-key"})
        self.assertEqual(plan["selected_route"], "official")
        self.assertIsNone(plan["base_url"])

    def test_profile_selects_its_provider(self):
        c = config(experimental_bearer_token="fixture-secret")
        c["model_provider"] = "openai"
        c["profiles"] = {"work": {"model_provider": "relay"}}
        plan = backend.resolve_route(c, {}, profile="work")
        self.assertEqual(plan["provider"], "relay")

    def test_unknown_profile_is_not_silently_ignored(self):
        with self.assertRaises(backend.BackendError):
            backend.resolve_route(config(), {}, profile="absent")

    def test_other_host_cannot_receive_active_credential(self):
        with self.assertRaises(backend.BackendError):
            backend.resolve_route(config(experimental_bearer_token="active-private"), {}, base_url="https://other.example/v1")

    def test_explicit_image_endpoint_has_paired_key(self):
        plan = backend.resolve_route(config(experimental_bearer_token="active-private"),
                                     {"DAXUAN_SCIENCE_IMAGE_API_KEY": "image-private"},
                                     base_url="https://other.example/v1")
        self.assertEqual(plan["_secret"], "image-private")
        self.assertNotIn("private", json.dumps(backend.public_plan(plan)))

    def test_origin_port_is_part_of_credential_binding(self):
        with self.assertRaises(backend.BackendError):
            backend.resolve_route(config(experimental_bearer_token="private"), {}, base_url="https://relay.example:8443/v1")

    def test_existing_deeper_api_path_is_preserved(self):
        self.assertEqual(backend.normalize_base("https://relay.example/custom/v1/"), "https://relay.example/custom/v1")

    def test_remote_http_and_url_credentials_are_rejected(self):
        for url in ("http://relay.example", "https://user:secret@relay.example", "https://relay.example?key=secret"):
            with self.assertRaises(backend.BackendError):
                backend.normalize_base(url)

    def test_local_relay_http_is_supported(self):
        self.assertEqual(backend.normalize_base("http://127.0.0.1:4311"), "http://127.0.0.1:4311/v1")

    def test_conflicting_route_does_not_switch_billing(self):
        with self.assertRaises(backend.BackendError):
            backend.resolve_route(config(experimental_bearer_token="private"), {}, route="official")

    def test_malformed_config_is_not_reported_as_official(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"config.toml"
            path.write_text("[invalid")
            with self.assertRaises(backend.BackendError):
                backend.load_config(path)

    def test_provider_header_can_supply_the_active_key(self):
        plan = backend.resolve_route(config(http_headers={"Authorization": "Bearer fixture-key"}), {})
        self.assertEqual(backend.relay_headers(plan)["Authorization"], "Bearer fixture-key")

    def test_cdn_does_not_receive_authorization(self):
        plan = backend.resolve_route(config(experimental_bearer_token="private"), {})
        with mock.patch.object(backend, "request_bytes", return_value=(b"image", 200)) as request:
            self.assertEqual(backend.download_payload({"data": [{"url": "https://cdn.example/image.png"}]}, plan), b"image")
            self.assertEqual(request.call_args.args[1], {})

    def test_same_host_protected_download_retains_authorization(self):
        plan = backend.resolve_route(config(experimental_bearer_token="private"), {})
        with mock.patch.object(backend, "request_bytes", return_value=(b"image", 200)) as request:
            backend.download_payload({"data": [{"url": "https://relay.example/image.png"}]}, plan)
            self.assertEqual(request.call_args.args[1]["Authorization"], "Bearer private")

    def test_base64_payload_requires_no_download(self):
        with mock.patch.object(backend, "request_bytes") as request:
            raw = backend.download_payload({"data": [{"b64_json": base64.b64encode(b"PNG-fixture").decode()}]}, {})
            self.assertEqual(raw, b"PNG-fixture")
            request.assert_not_called()

    def test_provider_error_is_not_retried(self):
        plan = backend.resolve_route(config(experimental_bearer_token="private"), {})
        with mock.patch.object(backend, "request_bytes", side_effect=backend.BackendError("HTTP 401")) as request:
            with self.assertRaises(backend.BackendError):
                backend.relay_generate(plan, "chromosome", "gpt-image-2", "opaque", [], None, None, 30)
            self.assertEqual(request.call_count, 1)

    def test_http_error_body_is_not_exposed(self):
        error = urllib.error.HTTPError("https://relay.example", 401, "private-provider-message", {}, BytesIO(b"private-token"))
        opener = mock.MagicMock()
        opener.open.side_effect = error
        with mock.patch.object(backend.urllib.request, "build_opener", return_value=opener):
            with self.assertRaises(backend.BackendError) as caught:
                backend.request_bytes("https://relay.example/v1/models")
            self.assertNotIn("private", str(caught.exception))
            self.assertIn("401", str(caught.exception))

    def test_rgba_with_no_transparent_pixels_is_opaque(self):
        from PIL import Image
        raw = BytesIO()
        Image.new("RGBA", (12, 12), "white").save(raw, format="PNG")
        facts = backend.png_facts(raw.getvalue())
        self.assertTrue(facts["has_alpha"])
        self.assertFalse(facts["transparent_canvas"])

    def test_true_alpha_is_distinguished_from_empty_image(self):
        from PIL import Image
        for empty in (False, True):
            image = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
            if not empty:
                image.putpixel((6, 6), (145, 178, 200, 255))
            raw = BytesIO()
            image.save(raw, format="PNG")
            self.assertEqual(backend.png_facts(raw.getvalue())["transparent_canvas"], not empty)

    def test_cli_dry_run_does_not_generate_or_expose_credentials(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            (p/"config.toml").write_text('model_provider = "relay"\n[model_providers.relay]\nbase_url = "https://relay.example"\nexperimental_bearer_token = "fixture-private-key"\n')
            (p/"prompt.txt").write_text("One chromosome; fixture prompt not to be printed")
            env = {k: v for k, v in os.environ.items() if not k.startswith("DAXUAN_SCIENCE_IMAGE_")}
            run = subprocess.run([sys.executable, str(ROOT/"scripts/image_backend.py"), "--config", str(p/"config.toml"),
                                  "--auth-file", str(p/"absent.json"), "--prompt-file", str(p/"prompt.txt"),
                                  "--out", str(p/"asset.png")], capture_output=True, text=True, env=env)
            self.assertEqual(run.returncode, 0, run.stdout)
            data = json.loads(run.stdout)
            self.assertEqual(data["selected_route"], "relay")
            self.assertFalse(data["generation_request_sent"])
            self.assertFalse((p/"asset.png").exists())
            self.assertNotIn("fixture-private-key", run.stdout+run.stderr)
            self.assertNotIn("fixture prompt", run.stdout+run.stderr)

    def test_generation_payload_and_saved_bytes_are_real(self):
        from PIL import Image
        raw = BytesIO()
        Image.new("RGB", (24, 24), "white").save(raw, format="PNG")
        plan = backend.resolve_route(config(experimental_bearer_token="private"), {})
        response = json.dumps({"data": [{"b64_json": base64.b64encode(raw.getvalue()).decode()}]}).encode()
        with mock.patch.object(backend, "request_bytes", return_value=(response, 200)) as request:
            output, status = backend.relay_generate(plan, "one chromosome", "fixture-model", "opaque", [], "1024x1024", "high", 30)
            self.assertEqual(output, raw.getvalue())
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(request.call_args.args[2])["n"], 1)
            self.assertEqual(request.call_count, 1)

    def test_edit_request_uses_only_selected_image(self):
        plan = backend.resolve_route(config(experimental_bearer_token="private"), {})
        response = json.dumps({"data": [{"b64_json": base64.b64encode(b"fixture").decode()}]}).encode()
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder)/"selected.png"
            image.write_bytes(b"selected-image-bytes")
            with mock.patch.object(backend, "request_bytes", return_value=(response, 200)) as request:
                backend.relay_generate(plan, "one chromosome", "fixture-model", "opaque", [image], None, None, 30)
                self.assertTrue(request.call_args.args[0].endswith("/images/edits"))
                self.assertIn(b"selected-image-bytes", request.call_args.args[2])
                self.assertNotIn(str(image).encode(), request.call_args.args[2])

    def test_declared_native_tool_is_separate_from_generation_evidence(self):
        data = backend.official_status(Path("not-installed"), native_tool=True)
        self.assertTrue(data["configuration_ready"])
        self.assertFalse(data["generation_verified"])

    def test_newline_in_key_is_rejected(self):
        with self.assertRaises(backend.BackendError):
            backend.resolve_route(config(experimental_bearer_token="fixture\nheader"), {})


if __name__ == "__main__":
    unittest.main()
