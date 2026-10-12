from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from latent_triz.cli import main
from tests.a0x_test_support import synthetic_a0_source


class A0R1CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.protocol = self.root / "results/a0r1/freeze/protocol-planned.json"

    def test_a0r1_corpus_and_preoutput_cli(self) -> None:
        with tempfile.TemporaryDirectory() as workdir:
            corpus = Path(workdir) / "corpus"
            audits = Path(workdir) / "audits"
            source_corpus = synthetic_a0_source(Path(workdir))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    0,
                    main(["a0r1-corpus", "--protocol", str(self.protocol), "--output-dir", str(corpus)]),
                )

            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(
                    [
                        "a0r1-preoutput",
                        "--protocol",
                        str(self.protocol),
                        "--candidate-corpus-dir",
                        str(corpus),
                        "--source-corpus-dir",
                        str(source_corpus),
                        "--output-dir",
                        str(audits),
                    ]
                )

            summary = json.loads(stdout.getvalue())
            self.assertEqual("", stderr.getvalue())
            self.assertEqual(0, code)
            self.assertEqual("pass", summary["status"])
            self.assertFalse(summary["model_output_accessed"])
            self.assertTrue((audits / "independence.json").is_file())
            self.assertTrue((audits / "shortcuts.json").is_file())
            self.assertTrue((audits / "preoutput-manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
