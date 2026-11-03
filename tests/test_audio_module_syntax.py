"""Regression test: core audio module must remain valid Python source."""

import unittest
from pathlib import Path


class AudioModuleSyntaxTests(unittest.TestCase):
    def test_audio_module_compiles(self):
        audio_path = Path(__file__).resolve().parents[1] / "systems" / "audio.py"
        source = audio_path.read_text(encoding="utf-8")
        compile(source, str(audio_path), "exec")


if __name__ == "__main__":
    unittest.main()
