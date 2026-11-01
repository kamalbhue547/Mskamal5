"""Bridge standard-library test discovery at the parent repository root."""

from pathlib import Path
import sys
import unittest


def load_tests(
    loader: unittest.TestLoader,
    _standard_tests: unittest.TestSuite,
    pattern: str | None,
) -> unittest.TestSuite:
    project = Path(__file__).resolve().parent / "ios-sweet-portability"
    tests = project / "tests"
    # Source-checkout discovery works even before an editable install. The
    # explicit top level keeps unittest from treating the hyphenated parent
    # directory as a Python package.
    if str(project) not in sys.path:
        sys.path.insert(0, str(project))
    return loader.discover(
        str(tests), pattern=pattern or "test*.py", top_level_dir=str(tests)
    )
