"""Tests for bpdtools.plots."""

import matplotlib.pyplot as plt

from bpdtools.plots import PLOT_STYLE, set_plot_style


def test_set_plot_style_writes_the_shared_settings():
    """Check that the style sets the saved figure dpi of the project."""
    with plt.rc_context():
        set_plot_style()
        assert plt.rcParams["savefig.dpi"] == PLOT_STYLE["savefig.dpi"]
