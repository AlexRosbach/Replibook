import unittest

from replibook.scanner.docker_scanner import DockerScanner


class DockerScannerTests(unittest.TestCase):
    def test_secret_keys_are_redacted(self):
        scanner = DockerScanner(redact_secrets=True)
        attrs = {"Config": {"Env": ["APP_MODE=prod", "DB_PASSWORD=supersecret"]}}
        env = scanner._parse_env(attrs, "my-app")
        self.assertEqual(env["APP_MODE"], "prod")
        self.assertEqual(env["DB_PASSWORD"], "__REDACTED__")

    def test_vault_placeholders_are_generated(self):
        scanner = DockerScanner(redact_secrets=False, vault_env_prefix="vault")
        attrs = {"Config": {"Env": ["API_TOKEN=abc", "LOG_LEVEL=info"]}}
        env = scanner._parse_env(attrs, "My-App")
        vars_out = scanner._collect_vault_vars(attrs, "My-App")
        self.assertEqual(env["API_TOKEN"], "{{ vault_my_app_api_token }}")
        self.assertEqual(env["LOG_LEVEL"], "info")
        self.assertIn("vault_my_app_api_token", vars_out)


if __name__ == "__main__":
    unittest.main()
