import tempfile
import unittest
from pathlib import Path

from replibook.scanner.deployments import DeploymentScanner


class DeploymentScannerTests(unittest.TestCase):
    def test_finds_env_files_from_compose(self):
        scanner = DeploymentScanner()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            compose = root / "docker-compose.yml"
            env = root / ".env"
            service_env = root / "service.env"
            env.write_text("X=1\n", encoding="utf-8")
            service_env.write_text("Y=2\n", encoding="utf-8")
            compose.write_text(
                """
services:
  app:
    image: nginx
    env_file:
      - service.env
""".strip(),
                encoding="utf-8",
            )

            found = scanner._find_env_files(str(compose))
            self.assertIn(str(env), found)
            self.assertIn(str(service_env), found)


if __name__ == "__main__":
    unittest.main()
