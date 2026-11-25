"""Shared figure style and the hour and weekday plots of the analyses."""

import matplotlib.pyplot as plt
from cycler import cycler
from matplotlib.colors import LinearSegmentedColormap

# Line colors of the project, in the order that groups get them: teal,
# terracotta, navy, ochre, plum, and warm gray. They follow the chart
# colors of a light report theme and replace the matplotlib defaults.
PALETTE = ("#3b9d82", "#d97757", "#213f7c", "#cca45e", "#7e4c8d", "#766d66")

# Page and line colors: warm paper background, near-black text, warm gray
# axes and ticks, and a faint grid.
PAPER = "#faf9f5"
INK = "#141413"
MUTED = "#5e5d59"
AXIS = "#b0aea5"
GRID = "#e8e6dc"

# Warm one-hue ramp for heatmaps, from paper (few events) through
# terracotta to deep brown (many events).
HEATMAP_COLORS = ("#faf9f5", "#efc7a6", "#d97757", "#8a3b22")
HEATMAP_CMAP = LinearSegmentedColormap.from_list("bpd_warm", HEATMAP_COLORS)

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
    "axes.prop_cycle": cycler(color=PALETTE),
    "figure.facecolor": PAPER,
    "axes.facecolor": PAPER,
    "savefig.facecolor": PAPER,
    "text.color": INK,
    "axes.labelcolor": INK,
    "axes.titlecolor": INK,
    "axes.edgecolor": AXIS,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    # Faint horizontal grid lines behind the data
    "axes.grid": True,
    "axes.grid.axis": "y",
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    # Thinner lines and smaller markers than the defaults
    "lines.linewidth": 1.8,
    "lines.markersize": 4,
}

# Shape of an hour and weekday table: 7 weekdays by 24 hours.
TABLE_SHAPE = (7, 24)

# Hours that get a tick label on the hour axis.
HOUR_TICKS = range(0, 24, 3)


def set_plot_style():
    """Apply the shared matplotlib settings of the project.

    Returns
    -------
    None
        The settings in PLOT_STYLE are written to matplotlib.rcParams.
    """
    plt.rcParams.update(PLOT_STYLE)


def plot_hour_weekday_heatmap(table, title, ax=None, count_label="Events"):
    """Draw a 7 by 24 hour and weekday table as a heatmap.

    Parameters
    ----------
    table : pandas.DataFrame
        7 rows (weekdays, Monday first) and 24 columns (hours 0 to 23), such
        as the result of `bpdtools.clock.hour_weekday_table`.
    title : str
        Title of the plot.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on. A new figure is made when it is not given.
    count_label : str, default "Events"
        Label of the color bar, for example "Noise calls".

    Returns
    -------
    matplotlib.axes.Axes
        The axes with the heatmap and its color bar.

    Raises
    ------
    ValueError
        If `table` is not 7 by 24.
    """
    # Stop early when the table does not have one row per weekday and one
    # column per hour, because the tick labels would not match the cells.
    if table.shape != TABLE_SHAPE:
        raise ValueError(
            f"table has shape {table.shape}; it needs 7 weekdays by 24 hours. "
            "Use bpdtools.clock.hour_weekday_table to build it."
        )
    if ax is None:
        _, ax = plt.subplots()

    # Draw the counts with weekdays as rows and hours as columns, on the
    # project warm ramp (light means few events), without grid lines.
    image = ax.imshow(table.to_numpy(), aspect="auto", cmap=HEATMAP_CMAP)
    ax.grid(False)
    ax.figure.colorbar(image, ax=ax, label=count_label)

    # Label every weekday and every third hour.
    ax.set_yticks(range(len(table.index)), labels=table.index)
    ax.set_xticks(HOUR_TICKS, labels=HOUR_TICKS)
    ax.set_xlabel("Hour of day (local time)")
    ax.set_ylabel("Day of week")
    ax.set_title(title)
    return ax


def plot_hourly_profiles(profiles, title, ax=None):
    """Draw the share of events in each hour, one line per group.

    Parameters
    ----------
    profiles : pandas.DataFrame
        24 rows (hours 0 to 23) and one column of shares per group, such as
        the result of `bpdtools.clock.hourly_profile`.
    title : str
        Title of the plot.
    ax : matplotlib.axes.Axes, optional
        Axes to draw on. A new figure is made when it is not given.

    Returns
    -------
    matplotlib.axes.Axes
        The axes with one line per group and a legend when there is more
        than one group.

    Raises
    ------
    ValueError
        If `profiles` does not have the 24 hours 0 to 23 as its rows.
    """
    # Check the rows, so that each line is drawn at the right hours.
    if list(profiles.index) != list(range(24)):
        raise ValueError(
            "profiles needs the hours 0 to 23 as its rows, in order. "
            "Use bpdtools.clock.hourly_profile to build it."
        )
    if ax is None:
        _, ax = plt.subplots()

    # Draw each group as a percentage of its own events.
    for group in profiles.columns:
        ax.plot(profiles.index, 100 * profiles[group], marker="o", label=group)

    # Start the share axis at zero, so that line heights compare fairly.
    ax.set_ylim(bottom=0)
    ax.set_xticks(HOUR_TICKS, labels=HOUR_TICKS)
    ax.set_xlabel("Hour of day (local time)")
    ax.set_ylabel("Share of events (%)")
    ax.set_title(title)
    if len(profiles.columns) > 1:
        ax.legend()
    return ax
