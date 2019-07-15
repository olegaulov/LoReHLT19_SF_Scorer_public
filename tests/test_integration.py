from unittest.mock import patch
import sys
import filecmp

import pytest

from LoReHLT_Frame_Scorer import main

test_input_data = [
    (
        "tests/SEC_test1/expected_SEC_output.txt",
        "tests/SEC_test1/setE/data/annotation/eng/situation_frame/",
        "tests/SEC_test1/perfect_submission.json",
        "tests/SEC_test1/diff_nil_edl.tab",
        "tests/SEC_test1/setE/data/annotation/eng/sec_test_eng_edl.tab",
    ),
    (
        "tests/SEC_test2/expected_SEC_output.txt",
        "tests/SEC_test2/setE/data/annotation/eng/situation_frame/",
        "tests/SEC_test2/perfect_submission.json",
        "tests/SEC_test2/diff_nil_edl.tab",
        "tests/SEC_test2/setE/data/annotation/eng/sec_test_eng_edl.tab",
    ),
]


@pytest.mark.parametrize("expected_file, ref, sub, EDL_ref, EDL_sub", test_input_data)
def test_this_test(expected_file, ref, sub, EDL_ref, EDL_sub, tmp_path):
    expected_file_dir = tmp_path / "tmp_output"
    expected_file_location = expected_file_dir / "PREFIX_diagnostic_SEC_scores.txt"
    test_args = [
        "test",
        "-g",
        ref,
        "-s",
        sub,
        "-o",
        expected_file_dir.as_posix(),
        "-m",
        "TEST_SYSTEM",
        "-p",
        "PREFIX",
        "-e",
        EDL_ref,
        "-r",
        EDL_sub,
    ]

    with patch.object(sys, "argv", test_args):
        main()
        assert filecmp.cmp(expected_file, expected_file_location.as_posix())
