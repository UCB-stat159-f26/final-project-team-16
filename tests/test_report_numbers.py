"""Check the numbers quoted in the report text against the saved results.

The report and the home page quote results in plain sentences. Each test
here builds the quoted piece of a sentence again from the saved result
tables and looks for it in the text, so a rerun that changes a result fails
the test until the sentence is updated.
"""

import json
import re

import pandas as pd
import pytest

from bpdtools.clock import DEFAULT_PERMUTATIONS
from bpdtools.config import HEADQUARTERS_ADDRESS
from bpdtools.hotspots import block_counts
from bpdtools.load import load_calls
from bpdtools.paths import repo_path

# Text that can never be in a document. A claim uses it when the saved
# results no longer support the wording, so that the test fails.
NOT_SUPPORTED = "<the saved results do not support this sentence>"


# Number words that the report spells out.
NUMBER_WORDS = {5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}


# A number in running text: a clock time, or digits with optional thousands
# commas, decimals, a minus sign, and a percent sign.
NUMBER_PATTERN = re.compile(
    r"\d{1,2}:\d{2}(?::\d{2})?|(?<![\w.])-?\d[\d,]*(?:\.\d+)?%?"
)


# Numbers in the report that are settings or names, not results, with the
# reason for each group. Every other number must be part of a checked claim.
NOT_RESULTS = {
    # Years and the analysis window
    "2007", "2021", "2022", "2024", "2025",
    # Clock limits of the checks and the placeholder times
    "00:00", "00:59", "01:59", "05:59", "06:00", "23:59", "00:00:00", "12:00:00",
    # The emergency phone number
    "911",
    # Hours in a day, and the two ends of the overlap scale
    "24", "1", "0",
    # Confidence level of the interval
    "95%",
    # Street number of a block that the text names
    "2700",
    # Police beat numbers and sizes of the top lists
    "6", "7", "4", "20", "10", "50",
}  # fmt: skip


# Numbers of the home page that are names: the course, the team, and the term.
HOME_NOT_RESULTS = {"159", "16", "2026"}


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


def home_text():
    """Read the prose of the website home page.

    Returns
    -------
    str
        The plain text of index.md without its front matter and without
        the lines that open, close, or set options of a MyST directive.
    """
    with open(repo_path("index.md"), encoding="utf-8") as source:
        lines = source.read().splitlines()
    # The front matter sits between the first two lines of three dashes
    body = lines[lines.index("---", 1) + 1 :]
    # Directive fences and their options start with a colon
    return plain_text("\n".join(line for line in body if not line.startswith(":")))


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


def processed(name):
    """Read one small analysis table from data/processed/.

    Parameters
    ----------
    name : str
        File name inside data/processed/, without the .csv ending.

    Returns
    -------
    pandas.DataFrame
        The table as saved by an analysis notebook.
    """
    return pd.read_csv(repo_path("data", "processed", f"{name}.csv"))


def clock(hour):
    """Write an hour of the day the way the report does, for example 17:00.

    Parameters
    ----------
    hour : int
        Hour of the day, 0 to 23.

    Returns
    -------
    str
        The hour as HH:00.
    """
    return f"{int(hour):02d}:00"


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


def time_claims():
    """Build the quoted pieces of the Time section.

    Returns
    -------
    list of str
        Pieces of sentences with their numbers filled in from the tables
        that notebooks/03_clock.ipynb saves.
    """
    peaks = result("03_a2_peaks").set_index("events")
    counts = result("03_a2_hour_weekday_counts")
    a2_profiles = result("03_a2_hourly_profiles").set_index("hour")
    a6_overlap = result("03_a6_overlap").set_index(["first", "second"])["overlap"]
    a6_tests = result("03_a6_overlap")["p_value"].dropna()
    a6_profiles = result("03_a6_hourly_profiles").set_index("hour")
    a7_overlap = result("03_a7_overlap").set_index(["days", "hours"])["overlap"]
    a7_profiles = result("03_a7_hourly_profiles").set_index("hour")

    # A2: noise at night, and the peak of each event type
    noise = counts[counts["events"].eq("Noise calls")]
    night = noise.loc[noise["hour"].isin([22, 23, 0, 1]), "count"].sum()
    busiest_day, busiest_time = peaks.loc["Noise calls", "busiest_cell"].split()
    claims = [
        f"of the {peaks.loc['Noise calls', 'n']:,} noise calls in 2021–2025,"
        f" {night / noise['count'].sum():.0%} came between 22:00 and 01:59, and the"
        f" busiest hour of the week was {busiest_day} at {busiest_time}",
        f"Collisions peak at {clock(peaks.loc['Collisions', 'peak_hour'])}, whereas"
        " assault cases",
    ]

    # A2 checks: assaults without the placeholder times, collisions by day
    assaults = peaks.loc["Assault cases"]
    no_midnight = peaks.loc["Assault cases without 00:00:00"]
    no_placeholder = peaks.loc["Assault cases without 00:00:00 or 12:00:00"]
    daytime = peaks.loc["Collisions 06:00-23:59"]
    at_midnight = assaults["n"] - no_midnight["n"]
    at_noon = no_midnight["n"] - no_placeholder["n"]
    in_noon_hour = counts.loc[
        counts["events"].eq("Assault cases") & counts["hour"].eq(12), "count"
    ].sum()
    afternoon = a2_profiles.loc[13:17, "Assault cases without 00:00:00 or 12:00:00"]
    claims += [
        f"assault cases appear to peak at {clock(assaults['peak_hour'])}, but {at_noon}"
        f" of the {in_noon_hour} assault cases in that hour have a time of exactly"
        " 12:00:00",
        f"Removing the {at_midnight} assault cases at exactly 00:00:00 alone leaves the"
        f" peak at {clock(no_midnight['peak_hour'])}"
        f" ({no_midnight['peak_hour_share']:.1%}"
        f" of {no_midnight['n']:,} assault cases)",
        f"Removing both the {at_midnight} assault cases at 00:00:00 and the {at_noon}"
        f" assault cases at 12:00:00 leaves {no_placeholder['n']:,} assault cases"
        " without a clear peak: every hour from 13:00 to 17:00 holds between"
        f" {afternoon.min():.1%} and {afternoon.max():.1%} of them, and"
        f" {clock(no_placeholder['peak_hour'])} is the highest at"
        f" {no_placeholder['peak_hour_share']:.1%}",
        f"leaves their peak at {clock(daytime['peak_hour'])}"
        f" ({daytime['peak_hour_share']:.1%} of {daytime['n']:,} collisions)",
    ]

    # A6: residents' calls against officer-initiated stops
    traffic, pedestrian = "Traffic stops", "Pedestrian stops"
    midday = a6_profiles.loc[11:16, pedestrian].sum()
    battery_pedestrian = a6_overlap["Battery calls", pedestrian]
    noise_pedestrian = a6_overlap["Noise calls", pedestrian]
    stop_sources = ("CFS traffic stops 2024-2025", "Stop Data vehicle stops 2024-2025")
    claims += [
        f"with their highest hour at {clock(a6_profiles[traffic].idxmax())}",
        f"They share the least timing with noise calls"
        f" ({a6_overlap['Noise calls', traffic]:.2f})",
        f"with {midday:.0%} happening between 11:00 and 16:59; their hourly profile is"
        f" close to that of battery calls ({battery_pedestrian:.2f}) and far from"
        f" that of noise calls ({noise_pedestrian:.2f})",
        f"have almost the same hourly profile (overlap {a6_overlap[stop_sources]:.2f})",
        f"shuffled the group labels {DEFAULT_PERMUTATIONS:,} times",
        supported(
            a6_tests.nunique() == 1,
            f"Every test gave p = {a6_tests.iloc[0]}, the smallest value that"
            f" {DEFAULT_PERMUTATIONS:,} shuffles allow",
        ),
        f"For each of the {NUMBER_WORDS[len(a6_tests)]} pairs, none of the"
        f" {DEFAULT_PERMUTATIONS:,} shuffles",
    ]

    # A7: vehicle stops against collisions on weekdays and weekends
    weekday_stops = a7_profiles["Weekdays, Vehicle stops"]
    weekday_collisions = a7_profiles["Weekdays, Collisions"]
    weekend_stops = a7_profiles["Weekends, Vehicle stops"]
    late = weekend_stops.loc[19:23].sum() + weekend_stops.loc[0]
    all_hours, daytime_hours = "00:00-23:59", "06:00-23:59"
    claims += [
        f"vehicle stops peak at {clock(weekday_stops.idxmax())}"
        f" ({weekday_stops.max():.1%} of weekday stops), while collisions peak at"
        f" {clock(weekday_collisions.idxmax())} ({weekday_collisions.max():.1%} of"
        " weekday collisions), yet the two hourly profiles still share most of their"
        f" timing (overlap {a7_overlap['Weekdays', all_hours]:.2f})",
        f"On weekends the overlap falls to {a7_overlap['Weekends', all_hours]:.2f}:"
        f" {late:.0%} of weekend stops happen between 19:00 and 00:59, whereas weekend"
        f" collisions peak at {clock(a7_profiles['Weekends, Collisions'].idxmax())}",
        f"the gap between weekdays ({a7_overlap['Weekdays', daytime_hours]:.2f}) and"
        f" weekends ({a7_overlap['Weekends', daytime_hours]:.2f})",
    ]
    return claims


def calendar_claims():
    """Build the quoted pieces of the Academic calendar section.

    Returns
    -------
    list of str
        Pieces of sentences with their numbers filled in from the tables
        that notebooks/04_calendar.ipynb saves in data/processed/.
    """
    rates = processed("a3_period_rates").set_index(
        ["outcome", "definition", "area", "period"]
    )
    no_beat = processed("a3_unassigned").set_index(["outcome", "period"])["unassigned"]
    matches = processed("a4_noise_matches")

    def ratio(outcome, definition, area):
        """Give the semester to break rate ratio of one group, two decimals."""
        row = rates.loc[(outcome, definition, area, "semester")]
        return f"{row['semester_to_break_ratio']:.2f}"

    semester = rates.loc[("noise", "southside", "near", "semester")]
    winter = rates.loc[("noise", "southside", "near", "winter_break")]
    # Event dates that found no ordinary date to compare with
    unmatched = pd.to_datetime(matches.loc[matches["n_controls"].eq(0), "event_date"])
    unmatched_days = " and ".join(f"{day:%B} {day.day}" for day in sorted(unmatched))
    return [
        f"noise calls in Southside averaged {semester['daily_rate']:.2f} per day during"
        f" the semester and {winter['daily_rate']:.2f} during winter break",
        f"The semester rate was {ratio('noise', 'southside', 'near')} times the break"
        f" rate there and {ratio('noise', 'southside', 'other')} times the break rate"
        " in the other",
        f"The comparison uses {int(semester['covered_days'])} semester days and"
        f" {int(winter['covered_days'])} break days",
        "the larger semester increase in noise calls"
        f" ({ratio('noise', 'adjacent', 'near')}"
        f" versus {ratio('noise', 'adjacent', 'other')} elsewhere)",
        f"reversed the ordering ({ratio('assault', 'adjacent', 'near')} versus"
        f" {ratio('assault', 'adjacent', 'other')})",
        f"excluded {no_beat['noise', 'semester']} noise calls and"
        f" {no_beat['assault', 'semester']} assault cases with no beat during the"
        " semester",
        f"{unmatched_days} had no eligible comparison",
    ]


def location_claims():
    """Build the quoted pieces of the Location section.

    Returns
    -------
    list of str
        Pieces of sentences with their numbers filled in from the tables
        that notebooks 05 and 06 save, and from the calls table for the two
        counts that no result table holds.
    """
    beats = processed("a5_driving_by_beat").set_index("beat")
    blocks = result("05_a8_block_counts")
    concentration = result("05_a8_concentration")
    checks = result("05_a8_checks").set_index("version")
    stability = result("05_a8_top_overlap")
    calls = load_calls()

    # A5: rank correlation of reckless-driving calls with the other counts
    with_calls = beats.corr(method="spearman")["reckless_calls"]
    reckless = calls[calls["call_group"].eq("reckless")]
    eligible = reckless["local_time"].dt.year.isin([2024, 2025]).sum()

    # A5: counts of the boundary check, the third one spelled as a word
    boundary = result("06_boundary_summary").iloc[0]
    changed = boundary["beats_with_changed_rank"]
    changed_ranks = NUMBER_WORDS.get(changed, str(changed))
    claims = [
        f"Among Berkeley’s {len(beats)} police beats in 2024–2025",
        f"more recorded collisions (Spearman ρ = {with_calls['collisions']:.3f})",
        f"vehicle-stop counts was weaker ({with_calls['vehicle_stops']:.3f})",
        f"Of {eligible:,} eligible calls, {beats['reckless_calls'].sum():,} could be"
        " assigned to a beat",
        "the calls–collisions correlation was still"
        f" {with_calls['alternate_collisions']:.3f}",
        f"Of {boundary['collisions_near_two_boundaries']} collisions within one"
        f" centimetre of two beat boundaries, {boundary['reassigned_collisions']} could"
        " be reassigned to the other beat",
        f"{changed_ranks.capitalize()} beats changed collision rank",
    ]

    # A8: how concentrated noise calls are
    top = [
        f"the busiest {row.fraction:.0%} ({row.n_blocks}) hold {row.share:.1%}"
        for row in concentration.itertuples()
    ]
    without = checks.drop(index="all blocks")["top 5% share"]
    intersections = blocks["block"].str.contains("&").sum()
    noise_calls = checks.loc["all blocks", "noise calls"]
    claims += [
        f"The {noise_calls:,} noise calls of 2021–2025 fall on {len(blocks):,} block"
        " addresses and intersections",
        f"The busiest {concentration['fraction'][0]:.0%} of blocks"
        f" ({concentration['n_blocks'][0]}) hold {concentration['share'][0]:.1%} of the"
        f" noise calls, {top[1]}, and {top[2]}",
        supported(
            blocks["block"][0] == "2700 CHANNING WAY",
            "The busiest block, the 2700 block of Channing Way, had"
            f" {blocks['count'][0]} noise calls",
        ),
        supported(
            blocks["block"][4] == HEADQUARTERS_ADDRESS,
            "The fifth-busiest block, 2100 Martin Luther King Jr Way, is the police"
            f" headquarters, and its {blocks['count'][4]} calls",
        ),
        f"without the {intersections} intersections, or without both, the busiest 5% of"
        f" blocks still hold between {without.min():.1%} and {without.max():.1%} of the"
        " noise calls",
    ]

    # A8: how many top blocks stay in the top list of the next year
    def shared(cutoff):
        """Give the lowest and highest yearly share of a top list that stays."""
        shares = stability.loc[stability["cutoff"].eq(cutoff), "share_shared"]
        return f"{shares.min():.0%}", f"{shares.max():.0%}"

    every_year = checks["top 20 every year"]
    noise = calls[calls["call_group"].eq("noise")]
    shattuck = {
        year: block_counts(noise[noise["local_time"].dt.year.eq(year)]).get(
            "2000 SHATTUCK AVE", 0
        )
        for year in (2021, 2022, 2025)
    }
    claims += [
        f"between {shared(20)[0]} and {shared(20)[1]} of a year's top 20 blocks",
        f"With a top 10 instead, the overlap was {shared(10)[0]} to {shared(10)[1]},"
        f" and with a top 50 it was {shared(50)[0]} to {shared(50)[1]}",
        f"{NUMBER_WORDS[every_year['all blocks']].capitalize()} blocks were in the top"
        " 20 in all five years",
        supported(
            every_year.drop(index="all blocks").nunique() == 1,
            f"{NUMBER_WORDS[every_year['without both']]} blocks still stayed in the top"
            " 20 every year",
        ),
        f"the 2000 block of Shattuck Avenue had {shattuck[2022]} noise calls in 2022"
        f" but {shattuck[2021]} in 2021 and {shattuck[2025]} in 2025",
    ]
    return claims


def conclusion_claims():
    """Build the quoted pieces of the Conclusion.

    Returns
    -------
    list of str
        Pieces of sentences that repeat results of the earlier sections,
        with their numbers filled in from the same saved tables.
    """
    peaks = result("03_a2_peaks").set_index("events")
    counts = result("03_a2_hour_weekday_counts")
    a6_overlap = result("03_a6_overlap").set_index(["first", "second"])["overlap"]
    a7_overlap = result("03_a7_overlap").set_index(["days", "hours"])["overlap"]
    weekend_stops = result("03_a7_hourly_profiles").set_index("hour")[
        "Weekends, Vehicle stops"
    ]
    rates = processed("a3_period_rates").set_index(
        ["outcome", "definition", "area", "period"]
    )
    beats = processed("a5_driving_by_beat").set_index("beat")

    noise = counts[counts["events"].eq("Noise calls")]
    night = noise.loc[noise["hour"].isin([22, 23, 0, 1]), "count"].sum()
    night_share = night / noise["count"].sum()
    busiest_day, busiest_time = peaks.loc["Noise calls", "busiest_cell"].split()
    semester = rates.loc[("noise", "southside", "near", "semester")]
    winter = rates.loc[("noise", "southside", "near", "winter_break")]
    other = rates.loc[("noise", "southside", "other", "semester")]
    late = weekend_stops.loc[19:23].sum() + weekend_stops.loc[0]
    with_calls = beats.corr(method="spearman")["reckless_calls"]
    traffic, all_hours = "Traffic stops", "00:00-23:59"
    return [
        f"{night_share:.0%} in 2021–2025 came between 22:00 and 01:59,"
        f" peaking {busiest_day} at {busiest_time}",
        f"noise calls averaged {semester['daily_rate']:.2f} per day in the Fall 2024"
        f" semester and {winter['daily_rate']:.2f} in winter break, a semester rate"
        f" {semester['semester_to_break_ratio']:.2f} times the break rate, compared"
        f" with {other['semester_to_break_ratio']:.2f} times in the other beats",
        f"collisions peak at {clock(peaks.loc['Collisions', 'peak_hour'])}, and assault"
        " cases spread",
        "traffic stops share the least timing with noise calls (overlap"
        f" {a6_overlap['Noise calls', traffic]:.2f}) and more with battery"
        f" ({a6_overlap['Battery calls', traffic]:.2f}) and reckless-driving calls"
        f" ({a6_overlap['Reckless-driving calls', traffic]:.2f})",
        f"on weekdays ({a7_overlap['Weekdays', all_hours]:.2f}) than on weekends"
        f" ({a7_overlap['Weekends', all_hours]:.2f}), when {late:.0%} of stops happen"
        " between 19:00 and 00:59",
        f"Across Berkeley's {len(beats)} police beats in 2024–2025",
        f"tended to have more collisions (Spearman ρ = {with_calls['collisions']:.3f})",
        f"vehicle stops was weak ({with_calls['vehicle_stops']:.3f})",
    ]


def home_claims():
    """Build the quoted pieces of the website home page.

    Returns
    -------
    list of str
        The four record counts with their date ranges, and the sentences
        about the hour of day, filled in from the saved tables.
    """
    summary = result("01_dataset_summary").set_index("dataset")
    peaks = result("03_a2_peaks").set_index("events")
    counts = result("03_a2_hour_weekday_counts")

    def tile(dataset, label, date_format):
        """Write one count with its first and last date, as the page shows it."""
        row = summary.loc[dataset]
        first = pd.Timestamp(row["first_local_date"])
        last = pd.Timestamp(row["last_local_date"])
        return f"{row['rows']:,} {label}, {first:{date_format}} to {last:{date_format}}"

    no_midnight = peaks.loc["Assault cases without 00:00:00"]
    no_placeholder = peaks.loc["Assault cases without 00:00:00 or 12:00:00"]
    in_noon_hour = counts.loc[
        counts["events"].eq("Assault cases") & counts["hour"].eq(12), "count"
    ].sum()
    return [
        tile("Calls for Service", "calls for service", "%Y"),
        tile("Crime cases", "crime cases", "%Y"),
        tile("Collisions", "collisions", "%b %Y"),
        tile("Vehicle stops", "vehicle stops", "%b %Y"),
        f"Noise calls peak at {clock(peaks.loc['Noise calls', 'peak_hour'])}, when"
        f" {peaks.loc['Noise calls', 'peak_hour_share']:.1%} of them come in, and"
        f" collisions peak at {clock(peaks.loc['Collisions', 'peak_hour'])}",
        f"but {no_midnight['n'] - no_placeholder['n']} of the {in_noon_hour} cases in"
        " that hour were logged at exactly 12:00:00",
        f"and {clock(no_placeholder['peak_hour'])} is the highest hour at"
        f" {no_placeholder['peak_hour_share']:.1%}",
    ]


# One group of claims per section of the report, named for the test output.
REPORT_SECTIONS = {
    "data": data_claims,
    "context": context_claims,
    "time": time_claims,
    "calendar": calendar_claims,
    "location": location_claims,
    "conclusion": conclusion_claims,
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


def test_report_has_no_number_without_a_source():
    """Check that every number in the report prose is part of a checked claim."""
    text = report_text()
    # Take the checked pieces out, longest first, so that only numbers that
    # no claim covers are left
    claims = [claim for build in REPORT_SECTIONS.values() for claim in build()]
    for claim in sorted(claims, key=len, reverse=True):
        text = text.replace(claim, " ")
    left_over = {number.rstrip(",") for number in NUMBER_PATTERN.findall(text)}
    unknown = sorted(left_over - NOT_RESULTS)
    assert not unknown, (
        "These numbers in main.ipynb are not built from a saved result. Add a claim"
        f" for each, or list it in NOT_RESULTS with the reason: {unknown}"
    )


def test_home_page_quotes_the_saved_results():
    """Check that each quoted piece of the home page is in index.md."""
    text = home_text()
    missing = [claim for claim in home_claims() if claim not in text]
    assert not missing, (
        "The saved results give these pieces, but index.md does not contain them."
        " Update the home page:\n" + "\n".join(missing)
    )


def test_home_page_has_no_number_without_a_source():
    """Check that every number on the home page is part of a checked claim."""
    text = home_text()
    for claim in sorted(home_claims(), key=len, reverse=True):
        text = text.replace(claim, " ")
    left_over = {number.rstrip(",") for number in NUMBER_PATTERN.findall(text)}
    unknown = sorted(left_over - NOT_RESULTS - HOME_NOT_RESULTS)
    assert not unknown, (
        "These numbers in index.md are not built from a saved result. Add a claim"
        f" for each, or list it in HOME_NOT_RESULTS with the reason: {unknown}"
    )
