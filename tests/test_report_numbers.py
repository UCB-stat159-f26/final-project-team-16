"""Check the numbers quoted in the report text against the saved results.

The report quotes results in plain sentences. Each test here builds the
quoted piece of a sentence again from the saved result tables and looks for
it in the text, so a rerun that changes a result fails the test until the
sentence is updated.
"""

import json
import re

import pandas as pd
import pytest

from bpdtools.paths import repo_path

# Text that can never be in a document. A claim uses it when the saved
# results no longer support the wording, so that the test fails.
NOT_SUPPORTED = "<the saved results do not support this sentence>"


def plain_text(markdown):
    """Reduce Markdown to the words a reader sees, on one line.

    Parameters
    ----------
    markdown : str
        Markdown source of a cell or a page.

    Returns
    -------
    str
        The text without images, link targets, table rows, bold marks, and
        code marks, with every run of white space as one space.
    """
    # Images carry no sentence text, and a link keeps only its label
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", markdown)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # Table rows are shown by code cells or checked as tables, not as prose
    lines = [line for line in text.splitlines() if not line.startswith("|")]
    text = " ".join(lines).replace("**", "").replace("`", "")
    return re.sub(r"\s+", " ", text)


def report_text():
    """Read the prose of the main report.

    Returns
    -------
    str
        The plain text of every Markdown cell of main.ipynb except the
        reference list, which holds no results.
    """
    with open(repo_path("main.ipynb"), encoding="utf-8") as source:
        cells = json.load(source)["cells"]
    prose = [
        "".join(cell["source"])
        for cell in cells
        if cell["cell_type"] == "markdown" and cell["id"] != "report-references"
    ]
    return plain_text("\n".join(prose))


def result(name):
    """Read one saved result table.

    Parameters
    ----------
    name : str
        File name inside results/, without the .csv ending.

    Returns
    -------
    pandas.DataFrame
        The table as saved by an analysis notebook.
    """
    return pd.read_csv(repo_path("results", f"{name}.csv"))


def supported(condition, sentence):
    """Give a sentence when the results support it, and a marker otherwise.

    Parameters
    ----------
    condition : bool
        Whether the saved results agree with the wording of `sentence`.
    sentence : str
        Text that the document must contain.

    Returns
    -------
    str
        `sentence`, or NOT_SUPPORTED, which no document contains.
    """
    return sentence if condition else NOT_SUPPORTED


def data_claims():
    """Build the quoted pieces of the Data section.

    Returns
    -------
    list of str
        Pieces of sentences with their numbers filled in from the tables
        that notebooks/01_data_overview.ipynb saves.
    """
    summary = result("01_dataset_summary").set_index("dataset")
    sources = result("01_call_sources").set_index("source")
    checks = result("01_time_checks").set_index("dataset")
    exact = result("01_crime_exact_hours").set_index("hour")["cases_at_exact_hour"]
    minutes = result("01_collision_minutes").set_index("hours")

    # Shares come from the counts, because the saved shares are rounded
    crime = checks.loc["Crime cases"]
    at_midnight = crime["rows_at_00_00_00"] / crime["timed_rows"]
    at_noon = crime["rows_at_12_00_00"] / crime["timed_rows"]
    first_collision = pd.Timestamp(summary.loc["Collisions", "first_local_date"])
    first_stop = pd.Timestamp(summary.loc["Vehicle stops", "first_local_date"])
    officer_share = sources.loc["Officer Initiated", "share"]
    early = minutes.loc["01:00-05:59", "share_minutes_under_10"]
    later = minutes.loc["06:00-19:59", "share_minutes_under_10"]
    return [
        f"collisions reach back to {first_collision.year}",
        f"Vehicle stops begin in {first_stop:%B %Y}",
        f"About a quarter of all calls ({officer_share:.1%}) are officer-initiated",
        f"A total of {crime['rows_at_00_00_00']:,} crime cases ({at_midnight:.1%}) have"
        f" a time of exactly 00:00:00 and {crime['rows_at_12_00_00']:,} crime cases"
        f" ({at_noon:.1%}) have a time of exactly 12:00:00, about three times as many"
        f" as at 11:00 ({exact[11]:,}) or 13:00 ({exact[13]:,})",
        supported(
            minutes.loc["00:00-00:59", "collisions"] == 0,
            "Zero collisions are recorded between 00:00 and 00:59",
        ),
        f"and {early:.0%} of the records between 01:00 and 05:59 have minutes under"
        f" 10, compared with {later:.0%} between 06:00 and 19:59",
    ]


def context_claims():
    """Build the quoted pieces of the Context section.

    Returns
    -------
    list of str
        Pieces of sentences with their numbers filled in from the tables
        that notebooks/02_trends.ipynb saves.
    """
    summary = result("01_dataset_summary").set_index("dataset")
    yearly = result("02_a1_yearly_totals").set_index("source")
    monthly = result("02_a1_monthly_counts")
    correlation = result("02_a1_correlation").set_index("measure")

    def top_two(column):
        """Give the two highest months of a column, in calendar order."""
        top = monthly.nlargest(2, column).sort_values("month")
        months = pd.to_datetime(top["month"])
        names = f"{months.iloc[0]:%B} and {months.iloc[1]:%B} {months.iloc[1].year}"
        counts = f"{top[column].iloc[0]} and {top[column].iloc[1]}"
        return names, counts

    stop_months, stop_counts = top_two("vehicle_stops")
    collision_months, collision_counts = top_two("collisions")
    pearson = correlation.loc["Pearson, monthly counts"]
    ranks = correlation.loc["Spearman, monthly counts"]
    changes = correlation.loc["Pearson, month-to-month changes"]
    interval = f"{pearson['ci_low']:.2f} to {pearson['ci_high']:.2f}"
    months = int(pearson["n"])
    undated = summary.loc["Collisions", "rows_without_time"]
    # The table stores each change as a negative percentage
    collision_drop = -yearly.loc["collisions", "change_pct"]
    stop_drop = -yearly.loc["vehicle_stops", "change_pct"]
    return [
        f"the {undated} collisions without a date",
        f"Collisions fell by {collision_drop:.1f}%, about twice as much as vehicle"
        f" stops ({stop_drop:.1f}%)",
        f"Stops were highest in {stop_months} ({stop_counts}), whereas collisions were"
        f" highest in {collision_months} ({collision_counts})",
        f"Across the {months} months, the correlation between monthly stops and"
        f" monthly collisions is close to zero (Pearson r = {pearson['r']:.2f}, 95%"
        f" interval {interval})",
        f"the correlation of the ranks is {ranks['r']:.2f}",
        f"that both series could share, is {changes['r']:.2f}",
        f"give only {months} monthly pairs, so the 95% interval runs from {interval}",
        supported(
            monthly[["vehicle_stops", "collisions"]].min().min() > 0,
            "No month in 2024–2025 has a count of 0",
        ),
    ]


# One group of claims per section of the report, named for the test output.
REPORT_SECTIONS = {
    "data": data_claims,
    "context": context_claims,
}


@pytest.mark.parametrize("section", REPORT_SECTIONS)
def test_report_quotes_the_saved_results(section):
    """Check that each quoted piece of one report section is in main.ipynb."""
    text = report_text()
    missing = [claim for claim in REPORT_SECTIONS[section]() if claim not in text]
    assert not missing, (
        "The saved results give these pieces, but main.ipynb does not contain them."
        " Update the sentences of the report:\n" + "\n".join(missing)
    )
