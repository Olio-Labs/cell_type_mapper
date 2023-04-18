import pytest

import numpy as np

from hierarchical_mapping.binary_array.binary_array import (
    BinarizedBooleanArray)


@pytest.mark.parametrize(
        "n_rows, n_cols", [(9, 13), (64, 128), (57, 77)])
def test_binarized_array_roundtrip(
        n_rows,
        n_cols):
    rng = np.random.default_rng(66771223)
    arr = BinarizedBooleanArray(
        n_rows=n_rows,
        n_cols=n_cols)

    src = rng.integers(0, 2, (n_rows, n_cols)).astype(bool)
    for i_row in range(n_rows):
        arr.set_row(i_row, src[i_row, :])

    for i_row in range(n_rows):
        actual = arr.get_row(i_row)
        np.testing.assert_array_equal(actual, src[i_row, :])

    for i_col in range(n_cols):
        actual = arr.get_col(i_col)
        np.testing.assert_array_equal(actual, src[:, i_col])


def test_column_setting():
    rng = np.random.default_rng(55667712)
    n_rows = 34
    n_cols = 71
    src = rng.integers(0, 2, (n_rows, n_cols)).astype(bool)
    arr = BinarizedBooleanArray(n_rows=n_rows, n_cols=n_cols)
    for i_row in range(n_rows):
        arr.set_row(i_row, data = src[i_row, :])

    been_zeroed = []
    for test_col in (17, 55, 31):
        # make sure the column wasn't already all True or all False
        assert src[:, test_col].sum() < n_cols
        assert src[:, test_col].sum() > 0
        arr.set_col_false(test_col)
        np.testing.assert_array_equal(
            arr.get_col(test_col),
            np.zeros(n_rows, dtype=bool))
        been_zeroed.append(test_col)
        for i_row in range(n_rows):
            actual = arr.get_row(i_row)
            expected = np.copy(src[i_row, :])
            expected[been_zeroed] = False
            np.testing.assert_array_equal(actual, expected)

    been_truthed = []
    for test_col in (22, 15, 3):
        # make sure the column wasn't already all True or all False
        assert src[:, test_col].sum() < n_cols
        assert src[:, test_col].sum() > 0
        arr.set_col_true(test_col)
        np.testing.assert_array_equal(
            arr.get_col(test_col),
            np.ones(n_rows, dtype=bool))
        been_truthed.append(test_col)
        for i_row in range(n_rows):
            actual = arr.get_row(i_row)
            expected = np.copy(src[i_row, :])
            expected[been_zeroed] = False
            expected[been_truthed] = True
            np.testing.assert_array_equal(actual, expected)


def test_row_setting():
    rng = np.random.default_rng(442113)
    n_cols = 34
    n_rows = 71
    src = rng.integers(0, 2, (n_rows, n_cols)).astype(bool)
    arr = BinarizedBooleanArray(n_rows=n_rows, n_cols=n_cols)
    for i_row in range(n_rows):
        arr.set_row(i_row, data = src[i_row, :])

    been_zeroed = []
    for test_row in (17, 55, 31):
        # make sure the row wasn't already all True or all False
        assert src[test_row, :].sum() < n_rows
        assert src[test_row].sum() > 0
        arr.set_row_false(test_row)
        np.testing.assert_array_equal(
            arr.get_row(test_row),
            np.zeros(n_cols, dtype=bool))
        been_zeroed.append(test_row)
        for i_col in range(n_cols):
            actual = arr.get_col(i_col)
            expected = np.copy(src[:, i_col])
            expected[been_zeroed] = False
            np.testing.assert_array_equal(actual, expected)

    been_truthed = []
    for test_row in (22, 15, 3):
        # make sure the row wasn't already all True or all False
        assert src[test_row, :].sum() < n_rows
        assert src[test_row, :].sum() > 0
        arr.set_row_true(test_row)
        np.testing.assert_array_equal(
            arr.get_row(test_row),
            np.ones(n_cols, dtype=bool))
        been_truthed.append(test_row)
        for i_col in range(n_cols):
            actual = arr.get_col(i_col)
            expected = np.copy(src[:, i_col])
            expected[been_zeroed] = False
            expected[been_truthed] = True
            np.testing.assert_array_equal(actual, expected)
