"""Put Calls for Service into call groups by their Call Type labels."""

import pandas as pd

from bpdtools.config import (
    BATTERY_CALL_TYPES,
    NOISE_CALL_TYPES,
    RECKLESS_CALL_TYPES,
)

# Call groups and their exact Call Type labels. The label tuples in
# bpdtools/config.py do not overlap, so each label is in one group at most.
CALL_GROUPS = {
    "noise": NOISE_CALL_TYPES,
    "battery": BATTERY_CALL_TYPES,
    "reckless": RECKLESS_CALL_TYPES,
}

# Group of every Call Type that is in none of CALL_GROUPS, blanks included.
OTHER_GROUP = "other"


def classify_call_type(call_types):
    """Put each Call Type label into one call group.

    Parameters
    ----------
    call_types : pandas.Series of str
        Call Type labels of Calls for Service, for example
        "CFS 415E - Noise Disturbance". Missing values are allowed.

    Returns
    -------
    pandas.Series of str
        "noise", "battery", "reckless", or "other" for each label, with the
        index of `call_types`. A missing label gives "other".
    """
    # Start with "other" and overwrite the labels of each group. Matching is
    # exact (isin), because a substring match would also catch other call
    # types such as "CFS 415 - Disturbance".
    groups = pd.Series(OTHER_GROUP, index=call_types.index, dtype="object")
    for group, labels in CALL_GROUPS.items():
        groups[call_types.isin(labels)] = group
    return groups
