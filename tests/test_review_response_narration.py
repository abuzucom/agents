#!/usr/bin/env python3
"""Cover the narration rule of the vendored PR review response validator.

The validator comes from `abuzucom/foucault`. Its 3.7.7 revision rejects a
report line that opens with a first-person pronoun. A model that narrates
its own process produces no usable verdict, so the contract forbids it.
"""
import unittest

from scripts.check_pr_review_response import (
    ResponseError,
    process_narration_lines,
    validate_response,
)

VALID_JSON = '{"mode": "PR", "verdict": "APPROVE", "findings": []}'
VERDICT_LINES = f"VERDICT: APPROVE - no findings\nVERDICT_JSON: {VALID_JSON}\n"
NARRATION_LINE_NUMBER = 2


class NarrationRuleTest(unittest.TestCase):
    """A report line that opens in the first person fails validation."""

    def test_a_first_person_report_line_is_rejected(self):
        response = "Scope: one file.\nI need to review the diff first.\n" + VERDICT_LINES
        with self.assertRaises(ResponseError) as raised:
            validate_response(response)
        self.assertIn("process narration", str(raised.exception))
        self.assertIn(str(NARRATION_LINE_NUMBER), str(raised.exception))

    def test_a_first_person_list_item_is_rejected(self):
        response = "Scope: one file.\n- We checked the workflow.\n" + VERDICT_LINES
        self.assertEqual(
            process_narration_lines(response), [NARRATION_LINE_NUMBER])

    def test_an_impersonal_report_passes(self):
        response = "Scope: one file.\nThe diff adds one test.\n" + VERDICT_LINES
        verdict, payload = validate_response(response)
        self.assertEqual(verdict, "APPROVE")
        self.assertEqual(payload["findings"], [])

    def test_a_word_that_only_starts_with_i_passes(self):
        response = "Scope: one file.\nInputs stay unchanged.\n" + VERDICT_LINES
        self.assertEqual(process_narration_lines(response), [])

    def test_a_fenced_first_person_line_passes(self):
        response = (
            "Scope: one file.\n```\nI am quoted evidence.\n```\n" + VERDICT_LINES)
        self.assertEqual(process_narration_lines(response), [])


if __name__ == "__main__":
    unittest.main()
