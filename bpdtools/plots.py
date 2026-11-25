"""Shared figure style and the hour and weekday plots of the analyses."""

import matplotlib.pyplot as plt

# Figure settings that every notebook shares, so that the figures match.
PLOT_STYLE = {
    "figure.figsize": (8, 4.5),
    "figure.dpi": 100,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
}


def set_plot_style():
    """Apply the shared matplotlib settings of the project.

    Returns
    -------
    None
        The settings in PLOT_STYLE are written to matplotlib.rcParams.
    """
    plt.rcParams.update(PLOT_STYLE)
