"""Include the optional Observatory's stdlib tests in repository CI."""

from pathlib import Path
import unittest


def load_tests(loader: unittest.TestLoader, suite: unittest.TestSuite, pattern: str | None):
    observatory = Path(__file__).resolve().parents[1] / "scripts/research_observatory"
    suite.addTests(unittest.TestLoader().discover(str(observatory), pattern="test_observatory_*.py"))
    return suite
