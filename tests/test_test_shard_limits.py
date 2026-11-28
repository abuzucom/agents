#!/usr/bin/env python3
"""Environment variables tune the test shard worker count and timeout (#191)."""
import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from scripts import check_hook_coverage as coverage
from scripts import run_tests

WORKERS = "AGENTS_TEST_WORKERS"
TIMEOUT = "AGENTS_TEST_SHARD_TIMEOUT_SECONDS"
USAGE_EXIT_CODE = 2
CUSTOM_WORKERS = 2
CUSTOM_TIMEOUT = 90
# Values that are not whole ASCII numbers inside the documented range. The
# Arabic-Indic digit two passes int() but is not ASCII.
INVALID_VALUES = ("", "0", "33", "abc", " 2", "2 ", "1.5", "-1", "٢", "99999")
INVALID_TIMEOUTS = ("0", "601", "ten")


class ReadLimitsTest(unittest.TestCase):
    """read_test_limits returns defaults, overrides, or a usage error."""

    def test_unset_values_keep_defaults(self) -> None:
        self.assertEqual(coverage.read_test_limits({}),
                         (coverage.DEFAULT_WORKERS, coverage.TEST_SHARD_TIMEOUT_SECONDS))

    def test_valid_overrides_apply(self) -> None:
        limits = coverage.read_test_limits(
            {WORKERS: str(CUSTOM_WORKERS), TIMEOUT: str(CUSTOM_TIMEOUT)})
        self.assertEqual(limits, (CUSTOM_WORKERS, CUSTOM_TIMEOUT))

    def test_range_edges_accepted(self) -> None:
        self.assertEqual(coverage.read_test_limits({WORKERS: "1", TIMEOUT: "600"}), (1, 600))
        self.assertEqual(coverage.read_test_limits({WORKERS: "32", TIMEOUT: "1"}), (32, 1))

    def test_invalid_workers_rejected(self) -> None:
        for value in INVALID_VALUES:
            with self.subTest(value=value):
                with self.assertRaises(coverage.ShardLimitError) as caught:
                    coverage.read_test_limits({WORKERS: value})
                self.assertIn(WORKERS, str(caught.exception))
                self.assertNotIn(repr(value), str(caught.exception))

    def test_invalid_timeout_rejected(self) -> None:
        for value in INVALID_TIMEOUTS:
            with self.subTest(value=value):
                with self.assertRaises(coverage.ShardLimitError) as caught:
                    coverage.read_test_limits({TIMEOUT: value})
                self.assertIn(TIMEOUT, str(caught.exception))


class EntryPointTest(unittest.TestCase):
    """Both entry points pass the limits on and exit 2 on a bad value."""

    def test_run_tests_passes_limits(self) -> None:
        environment = {WORKERS: str(CUSTOM_WORKERS), TIMEOUT: str(CUSTOM_TIMEOUT)}
        with patch.dict("os.environ", environment), \
                patch.object(run_tests, "run_suite", return_value=0) as run_suite, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_tests.main([]), 0)
        self.assertEqual(run_suite.call_args.kwargs,
                         {"workers": CUSTOM_WORKERS, "timeout": CUSTOM_TIMEOUT})

    def test_run_tests_rejects_bad_value(self) -> None:
        stderr = io.StringIO()
        with patch.dict("os.environ", {WORKERS: "0", TIMEOUT: str(CUSTOM_TIMEOUT)}), \
                patch.object(run_tests, "run_suite") as run_suite, \
                contextlib.redirect_stderr(stderr):
            self.assertEqual(run_tests.main([]), USAGE_EXIT_CODE)
        run_suite.assert_not_called()
        self.assertIn(WORKERS, stderr.getvalue())

    def test_coverage_passes_limits(self) -> None:
        environment = {WORKERS: str(CUSTOM_WORKERS), TIMEOUT: str(CUSTOM_TIMEOUT)}
        with patch.dict("os.environ", environment), \
                patch.object(coverage, "run_test_shards", return_value=[]) as run_shards, \
                patch.object(coverage, "unreached_counts", return_value={}):
            self.assertEqual(coverage.measure(str(ROOT)), {})
        self.assertEqual(run_shards.call_args.kwargs,
                         {"workers": CUSTOM_WORKERS, "timeout": CUSTOM_TIMEOUT})

    def test_coverage_rejects_bad_value(self) -> None:
        stderr = io.StringIO()
        with patch.dict("os.environ", {WORKERS: str(CUSTOM_WORKERS), TIMEOUT: "601"}), \
                patch.object(coverage, "measure") as measure, \
                contextlib.redirect_stderr(stderr):
            self.assertEqual(coverage.main([]), USAGE_EXIT_CODE)
        measure.assert_not_called()
        self.assertIn(TIMEOUT, stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
