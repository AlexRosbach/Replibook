import unittest

from replibook.cli import _canonicalize


class CliDiffTests(unittest.TestCase):
    def test_canonicalize_nested_structures(self):
        value = {
            "packages": [{"name": "a"}, {"name": "b"}],
            "sysctl": {"net.ipv4.ip_forward": "1"},
        }
        out = _canonicalize(value)
        self.assertTrue(any(item.startswith("packages:") for item in out))
        self.assertIn("sysctl:net.ipv4.ip_forward=1", out)


if __name__ == "__main__":
    unittest.main()
