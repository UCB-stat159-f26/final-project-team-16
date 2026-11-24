"""Tests for bpdtools.load."""

import pandas as pd

from bpdtools.load import classify_call_type


def test_classify_call_type_puts_each_label_in_its_group():
    """Check one label of each group, an other label, and a missing label."""
    labels = pd.Series(
        [
            "CFS 415E - Noise Disturbance",
            "CFS 242 - Battery",
            "CFS 23103 - Reckless Vehicle",
            "CFS BMCVIO - BMC Violation",
            None,
        ]
    )
    groups = classify_call_type(labels)
    assert groups.tolist() == ["noise", "battery", "reckless", "other", "other"]


def test_classify_call_type_does_not_match_part_of_a_label():
    """Check that a label that only contains a group label stays other."""
    # "CFS 415 - Disturbance" shares "415" with the noise label but is a
    # different call type.
    labels = pd.Series(["CFS 415 - Disturbance", "cfs 415e - noise disturbance"])
    assert classify_call_type(labels).tolist() == ["other", "other"]
