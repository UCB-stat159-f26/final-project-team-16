"""Tests for bpdtools.plots."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure

from bpdtools.plots import (
    HEATMAP_CMAP,
    PALETTE,
    PLOT_STYLE,
    plot_hour_weekday_heatmap,
    plot_hourly_profiles,
    set_plot_style,
)


def new_axes():
    """Make one axes on a figure that is not shown on screen.

    Returns
    -------
    matplotlib.axes.Axes
        Axes of a new matplotlib Figure.
    """
    return Figure().subplots()


def test_set_plot_style_writes_the_shared_settings():
    """Check that the style sets the saved figure dpi of the project."""
    with plt.rc_context():
        set_plot_style()
        assert plt.rcParams["savefig.dpi"] == PLOT_STYLE["savefig.dpi"]


def test_set_plot_style_uses_the_project_palette_for_lines():
    """Check that new lines take the project colors in order, not the defaults."""
    with plt.rc_context():
        set_plot_style()
        ax = new_axes()
        first = ax.plot([0, 1])[0]
        second = ax.plot([1, 0])[0]
        assert first.get_color() == PALETTE[0]
        assert second.get_color() == PALETTE[1]


def test_plot_hour_weekday_heatmap_uses_the_project_ramp():
    """Check that the heatmap is drawn with the project blue ramp."""
    table = pd.DataFrame(np.ones((7, 24)), columns=range(24))
    ax = plot_hour_weekday_heatmap(table, "x", ax=new_axes())
    assert ax.images[0].get_cmap().name == HEATMAP_CMAP.name


def test_plot_hour_weekday_heatmap_draws_each_cell_and_labels():
    """Check the cell values, the weekday labels, and the axis titles."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    table = pd.DataFrame(
        np.arange(168).reshape(7, 24), index=[*days, "Sunday"], columns=range(24)
    )
    ax = plot_hour_weekday_heatmap(table, "Noise calls", ax=new_axes())
    # The image holds the table as it is: Monday 0 a.m. top left.
    assert np.array_equal(np.asarray(ax.images[0].get_array()), table.to_numpy())
    assert [label.get_text() for label in ax.get_yticklabels()][0] == "Monday"
    assert ax.get_title() == "Noise calls"
    assert ax.get_xlabel() == "Hour of day (local time)"


def test_plot_hour_weekday_heatmap_rejects_a_table_of_the_wrong_shape():
    """Check that a 24 by 7 table raises a ValueError."""
    with pytest.raises(ValueError, match="7 weekdays by 24 hours"):
        plot_hour_weekday_heatmap(pd.DataFrame(np.zeros((24, 7))), "x", new_axes())


def test_plot_hourly_profiles_draws_one_line_per_group_in_percent():
    """Check two lines, their percentages, and the legend."""
    shares = np.zeros(24)
    shares[[8, 20]] = 0.5
    profiles = pd.DataFrame({"noise": shares, "battery": np.full(24, 1 / 24)})
    ax = plot_hourly_profiles(profiles, "Calls by hour", ax=new_axes())
    assert len(ax.get_lines()) == 2
    assert ax.get_lines()[0].get_ydata()[8] == 50
    assert ax.get_legend() is not None


def test_plot_hourly_profiles_rejects_rows_that_are_not_the_hours():
    """Check that profiles without the rows 0 to 23 raise a ValueError."""
    profiles = pd.DataFrame({"noise": np.full(24, 1 / 24)}, index=range(1, 25))
    with pytest.raises(ValueError, match="hours 0 to 23"):
        plot_hourly_profiles(profiles, "x", new_axes())
