from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "processed" / "fire_data_sample.csv"
PROVINCES_PATH = ROOT / "web_app" / "data" / "canada_provinces.geojson"

alt.data_transformers.disable_max_rows()


@st.cache_data
def load_fire_data() -> pd.DataFrame:
    return pd.DataFrame(pd.read_csv(DATA_PATH))


@st.cache_data
def load_canada_geojson() -> dict:
    with PROVINCES_PATH.open() as response:
        provinces_data = json.load(response)

    canada_provinces = [
        f for f in provinces_data["features"] if f["properties"].get("admin") == "Canada"
    ]

    province_to_agency = {
        "British Columbia": "BC",
        "Alberta": "AB",
        "Saskatchewan": "SK",
        "Manitoba": "MB",
        "Ontario": "ON",
        "Quebec": "QC",
        "Qu\u00e9bec": "QC",
        "New Brunswick": "NB",
        "Nova Scotia": "NS",
        "Prince Edward Island": "PE",
        "Newfoundland and Labrador": "NL",
        "Yukon": "YT",
        "Northwest Territories": "NT",
        "Nunavut": "NU",
    }

    features = []
    for f in canada_provinces:
        name = f["properties"]["name"]
        feature = {
            "type": "Feature",
            "properties": {
                "name": name,
                "agency_code": province_to_agency.get(name, None),
            },
            "geometry": f["geometry"],
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


def build_dashboard_one(fire_data_sample: pd.DataFrame) -> alt.Chart:
    fire_data_sample = fire_data_sample.copy()

    fire_data_sample["CAUSE"] = fire_data_sample["CAUSE"].map(
        {
            "H": "Human",
            "H-PB": "Human Prescribed Burn",
            "N": "Natural",
            "RE": "Reignition",
            "U": "Unknown",
        }
    )

    fixed_cause_domain = [
        "Human",
        "Human Prescribed Burn",
        "Natural",
        "Reignition",
        "Unknown",
    ]

    freq_table = fire_data_sample.groupby("SRC_AGENCY").size().reset_index(name="total_fires")

    canada_provinces_data = alt.Data(
        values=load_canada_geojson()["features"],
    )

    province_click = alt.selection_point(
        fields=["SRC_AGENCY"],
        name="selProvince",
        clear=True,
    )

    year_slider = alt.param(
        name="selected_year",
        value=1990,
        bind=alt.binding_range(
            min=int(fire_data_sample["YEAR"].min()),
            max=int(fire_data_sample["YEAR"].max()),
            step=1,
            name="Select Year: ",
        ),
    )

    show_all = alt.param(
        name="showAllYears",
        bind=alt.binding_checkbox(name="Show All Years"),
        value=True,
    )

    filter_year = (alt.datum.YEAR == year_slider) | show_all

    cause_click = alt.selection_point(
        fields=["CAUSE"],
        toggle=False,
        empty=True,
    )

    map_provinces = (
        alt.Chart(canada_provinces_data)
        .mark_geoshape(stroke="black", strokeWidth=1)
        .encode(
            color=alt.condition(
                province_click,
                alt.value("#FFD54F"),
                alt.value("lightgray"),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("properties.name:N", title="Province"),
                alt.Tooltip("properties.agency_code:N", title="Agency Code"),
                alt.Tooltip("total_fires:Q", title="Total Fires"),
            ],
        )
        .transform_calculate(SRC_AGENCY="datum.properties.agency_code")
        .transform_lookup(
            lookup="SRC_AGENCY",
            from_=alt.LookupData(freq_table, "SRC_AGENCY", ["total_fires"]),
        )
        .add_params(province_click)
    )

    map_points = (
        alt.Chart(fire_data_sample)
        .mark_circle(size=10, opacity=0.45)
        .encode(
            longitude="LONGITUDE:Q",
            latitude="LATITUDE:Q",
            color=alt.Color(
                "CAUSE:N",
                legend=None,
                scale=alt.Scale(domain=fixed_cause_domain),
            ),
            opacity=alt.condition(
                cause_click & province_click,
                alt.value(0.8),
                alt.value(0),
            ),
            tooltip=[
                alt.Tooltip("YEAR:Q", title="Year:"),
                alt.Tooltip("MONTH:O", title="Month:"),
                alt.Tooltip("CAUSE:N", title="Cause:"),
                alt.Tooltip("SIZE_HA:Q", title="Size (Hectare):"),
                alt.Tooltip("SRC_AGENCY:N", title="Agency:"),
            ],
        )
        .transform_filter(year_slider, filter_year, cause_click)
        .add_params(province_click)
    )

    summary_bar = (
        alt.Chart(fire_data_sample)
        .mark_bar(size=30)
        .encode(
            x=alt.X("CAUSE:N", title="Fire Cause"),
            y=alt.Y("count():Q", title="Frequency"),
            color=alt.Color("CAUSE:N", scale=alt.Scale(domain=fixed_cause_domain)),
            tooltip=[
                alt.Tooltip("CAUSE:N", title="Fire Cause:"),
                alt.Tooltip("count(CAUSE):Q", title="Frequency:"),
                alt.Tooltip("mean(SIZE_HA):Q", title="Average Fire Size (Hectare):"),
            ],
        )
        .transform_filter(province_click)
        .transform_filter(filter_year)
        .properties(
            height=350,
            width=200,
            title="Fire Causes in Selected Province",
        )
        .add_params(cause_click)
    )

    fire_map = (
        alt.layer(map_provinces, map_points)
        .project(
            type="albers",
            parallels=[50, 70],
            rotate=[96, 0, 0],
            scale=800,
            translate=[300, 630],
        )
        .properties(
            width=700,
            height=600,
            title="Fire Events Across Canada",
        )
        .add_params(year_slider, show_all)
    )

    return (
        alt.hconcat(fire_map, summary_bar)
        .add_params(year_slider, show_all)
        .resolve_scale(color="independent")
        .properties(
            title=alt.Title(
                "Wildfire Event Frequency Over Time by Fire Cause",
                fontSize=16,
                anchor="middle",
            )
        )
    )


def build_dashboard_two(fire_data_sample: pd.DataFrame) -> alt.Chart:
    fire_data_sample = fire_data_sample.copy()

    fire_data_sample["CAUSE"] = fire_data_sample["CAUSE"].map(
        {
            "H": "Human",
            "H-PB": "Human Prescribed Burn",
            "N": "Natural",
            "RE": "Reignition",
            "U": "Unknown",
        }
    )

    fire_data_sample["SRC_AGENCY"] = fire_data_sample["SRC_AGENCY"].map(
        {
            "AB": "Alberta",
            "BC": "British Columbia",
            "MB": "Manitoba",
            "NL": "Newfoundland and Labrador",
            "NT": "Northwest Territories",
            "ON": "Ontario",
            "PC": "Parks Canada",
            "QC": "Quebec",
            "SK": "Saskatchewan",
            "YT": "Yukon",
        }
    )

    fire_data_sample["SEVERITY"] = np.where(
        fire_data_sample["SIZE_HA"] < 100,
        "Small (<100 Ha)",
        np.where(
            fire_data_sample["SIZE_HA"] < 1000,
            "Medium (100-1000 Ha)",
            np.where(
                fire_data_sample["SIZE_HA"] < 10000,
                "Large (1000-10000 Ha)",
                "Extreme (>10000 Ha)",
            ),
        ),
    )

    fixed_cause_domain = [
        "Human",
        "Human Prescribed Burn",
        "Natural",
        "Reignition",
        "Unknown",
    ]

    brush = alt.selection_interval(name="brush")

    cause_click = alt.selection_point(
        fields=["CAUSE"],
        toggle=False,
        empty=True,
    )

    province_click = alt.selection_point(
        fields=["SRC_AGENCY"],
        empty=True,
        toggle=False,
    )

    severity_param = alt.param(
        name="severity_param",
        bind=alt.binding_select(
            options=[
                "Overall",
                "Small (<100 Ha)",
                "Medium (100-1000 Ha)",
                "Large (1000-10000 Ha)",
                "Extreme (>10000 Ha)",
            ],
            name="Select Severity: ",
        ),
        value="Overall",
    )

    severity_filter = "datum.SEVERITY == severity_param || severity_param == 'Overall'"

    jittered_strip = (
        alt.Chart(fire_data_sample)
        .transform_calculate(jitter=f"(random() - 0.5) * {0.3}")
        .mark_circle(size=12, opacity=0.7)
        .encode(
            x=alt.X("SIZE_HA:Q", title="Fire Size (Hectare)"),
            y=alt.Y(
                "SRC_AGENCY:N",
                title="Province/Agency",
                axis=alt.Axis(labelAngle=0),
                scale=alt.Scale(type="log"),
            ),
            yOffset="jitter:Q",
            color=alt.Color(
                "CAUSE:N",
                title="Fire Cause",
                scale=alt.Scale(domain=fixed_cause_domain),
            ),
            tooltip=[
                alt.Tooltip("SRC_AGENCY:N", title="Province/Agency:"),
                alt.Tooltip("CAUSE:N", title="Fire Cause:"),
                alt.Tooltip("SIZE_HA:Q", title="Fire Size (Hectare):"),
            ],
            opacity=alt.condition(
                cause_click & province_click,
                alt.value(1),
                alt.value(0),
            ),
        )
        .add_params(brush)
        .properties(
            width=800,
            height=330,
            title="Jittered Strip Plot of Fire Size by Province",
        )
    )

    avg_size_bar = (
        alt.Chart(fire_data_sample)
        .mark_bar(size=20)
        .encode(
            y=alt.Y("SRC_AGENCY:N", title="Province/Agency", sort="-x"),
            x=alt.X("mean(SIZE_HA):Q", title="Average Fire Size (Hectare)"),
            tooltip=[
                alt.Tooltip("SRC_AGENCY:N", title="Province/Agency:"),
                alt.Tooltip("mean(SIZE_HA):Q", title="Average Fire Size (Hectare):"),
            ],
            color=alt.condition(
                province_click,
                alt.value("#4e79a7"),
                alt.value("#7f7f7f"),
            ),
        )
        .add_params(province_click)
        .properties(
            width=300,
            height=280,
            title="Average Fire Size by Province",
        )
        .transform_filter(brush)
    )

    cause_stats = (
        alt.Chart(fire_data_sample)
        .transform_filter(severity_filter)
        .transform_filter(brush)
        .transform_aggregate(mean_size="mean(SIZE_HA)", groupby=["CAUSE"])
    )

    line = cause_stats.mark_rule(strokeWidth=3, color="#cccccc").encode(
        y=alt.Y("CAUSE:N", sort="-x", title="Fire Cause"),
        x=alt.X("mean_size:Q", title="Average Fire Size (Hectare)"),
    )

    dot = (
        cause_stats.mark_circle(size=200)
        .encode(
            y=alt.Y("CAUSE:N", sort="-x"),
            x="mean_size:Q",
            color=alt.condition(
                cause_click,
                alt.Color("CAUSE:N", scale=alt.Scale(domain=fixed_cause_domain)),
                alt.value("#bdbdbd"),
            ),
            tooltip=[
                alt.Tooltip("CAUSE:N", title="Fire Cause"),
                alt.Tooltip("mean_size:Q", title="Average Fire Size (Hectare)"),
            ],
        )
        .add_params(cause_click)
    )

    cause_lollipop = (line + dot).properties(
        width=300,
        height=280,
        title="Average Fire Size by Cause",
    )

    jittered_strip_filtered = jittered_strip.transform_filter(severity_filter)
    avg_size_province_filtered = avg_size_bar.transform_filter(severity_filter)
    cause_lollipop_filtered = cause_lollipop.transform_filter(severity_filter)

    province_rules = (
        alt.Chart(fire_data_sample)
        .mark_rule(stroke="lightgray", strokeWidth=1)
        .encode(
            y=alt.Y("SRC_AGENCY:N"),
        )
    )

    jittered_strip_with_lines = alt.layer(
        province_rules,
        jittered_strip_filtered,
    ).resolve_scale(y="shared")

    return (
        (jittered_strip_with_lines & (avg_size_province_filtered | cause_lollipop_filtered))
        .add_params(severity_param)
        .properties(
            title=alt.Title(
                "Average Wildfire Size by Severity: Regional and Cause-Based Comparisons",
                fontSize=16,
                anchor="middle",
            )
        )
    )


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #172026;
            --muted: #61707a;
            --line: rgba(30, 42, 48, 0.12);
            --panel: rgba(255, 255, 255, 0.92);
            --ember: #c95f2e;
            --gold: #f2b84b;
            --green: #2f6f68;
        }

        html {
            scroll-behavior: smooth;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(242, 184, 75, 0.28), transparent 30rem),
                linear-gradient(135deg, #f8f4ea 0%, #eef3f1 44%, #f7f1e8 100%);
            color: var(--ink);
        }

        .block-container {
            max-width: 1320px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        div[data-testid="stToolbar"] {
            display: none;
        }

        .hero {
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 2rem;
            background:
                linear-gradient(120deg, rgba(255, 255, 255, 0.94), rgba(255, 255, 255, 0.76)),
                linear-gradient(90deg, rgba(201, 95, 46, 0.12), rgba(47, 111, 104, 0.12));
            box-shadow: 0 22px 70px rgba(31, 43, 47, 0.12);
        }

        .eyebrow {
            color: var(--ember);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }

        .hero h1 {
            font-size: 2.7rem;
            line-height: 1.06;
            margin: 0 0 0.85rem 0;
            letter-spacing: 0;
        }

        .hero p {
            max-width: 760px;
            color: var(--muted);
            font-size: 1.05rem;
            line-height: 1.65;
            margin: 0;
        }

        .metric-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 1rem;
            margin: 1.25rem 0 1.4rem;
        }

        .metric-card {
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 1rem 1.1rem;
            background: var(--panel);
            box-shadow: 0 12px 34px rgba(31, 43, 47, 0.08);
        }

        .metric-card span {
            display: block;
            color: var(--muted);
            font-size: 0.78rem;
            margin-bottom: 0.35rem;
        }

        .metric-card strong {
            display: block;
            color: var(--ink);
            font-size: 1.55rem;
            line-height: 1.1;
        }

        .section-card {
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 1.15rem 1.25rem;
            margin: 1.15rem 0;
            background: var(--panel);
            box-shadow: 0 16px 44px rgba(31, 43, 47, 0.1);
        }

        .section-card h2 {
            margin: 0 0 0.55rem 0;
            font-size: 1.35rem;
            letter-spacing: 0;
        }

        .dashboard-title {
            margin: 0 0 0.75rem 0;
            color: var(--green);
            font-size: 1.85rem;
            font-weight: 850;
            line-height: 1.15;
            letter-spacing: 0;
        }

        .section-card p {
            margin: 0;
            color: var(--muted);
            line-height: 1.6;
        }

        .instruction-list {
            margin: 0.85rem 0 0 0;
            padding-left: 1.15rem;
            color: var(--muted);
            line-height: 1.65;
        }

        .instruction-list li {
            margin: 0.28rem 0;
        }

        .section-stack {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            margin: 1.25rem 0;
        }

        .section-label {
            margin: 1.35rem 0 0.65rem;
            color: var(--ember);
            font-size: 0.8rem;
            font-weight: 800;
            letter-spacing: 0;
            text-transform: uppercase;
        }

        .report-section {
            border-left: 4px solid var(--green);
            border-radius: 14px;
            padding: 1.25rem 1.35rem;
            background:
                linear-gradient(90deg, rgba(47, 111, 104, 0.08), rgba(255, 255, 255, 0) 34%),
                rgba(255, 255, 255, 0.9);
            box-shadow: 0 14px 34px rgba(31, 43, 47, 0.08);
        }

        .report-kicker {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2rem;
            height: 2rem;
            margin-bottom: 0.7rem;
            border-radius: 999px;
            background: rgba(47, 111, 104, 0.12);
            color: var(--green);
            font-weight: 800;
            font-size: 0.85rem;
        }

        .report-section h3 {
            margin: 0 0 0.45rem 0;
            font-size: 1.14rem;
            letter-spacing: 0;
        }

        .report-section p {
            margin: 0;
            color: var(--muted);
            line-height: 1.62;
            font-size: 1rem;
            max-width: 980px;
        }

        .interpretation-grid {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            margin-top: 1rem;
        }

        .interpretation-card {
            border: 1px solid rgba(30, 42, 48, 0.1);
            border-radius: 12px;
            padding: 1rem 1.1rem;
            background: rgba(255, 255, 255, 0.82);
        }

        .interpretation-card h3 {
            margin: 0 0 0.5rem 0;
            font-size: 1rem;
            letter-spacing: 0;
        }

        .interpretation-card ul {
            margin: 0;
            padding-left: 1.1rem;
            color: var(--muted);
            line-height: 1.55;
        }

        .interpretation-card li {
            margin: 0.3rem 0;
        }

        .tip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 0.85rem;
        }

        .tip-pill {
            border: 1px solid rgba(47, 111, 104, 0.18);
            border-radius: 999px;
            padding: 0.38rem 0.72rem;
            color: #2f514d;
            background: rgba(47, 111, 104, 0.08);
            font-size: 0.84rem;
        }

        div[role="radiogroup"] {
            gap: 0.6rem;
        }

        div[role="radiogroup"] label {
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 0.85rem 1rem;
            background: rgba(255, 255, 255, 0.82);
            box-shadow: 0 8px 20px rgba(31, 43, 47, 0.06);
        }

        div[role="radiogroup"] label p {
            color: #203f3b;
            font-size: 1.08rem;
            font-weight: 800;
            line-height: 1.25;
        }

        div[data-testid="stVegaLiteChart"] {
            overflow: visible;
        }

        iframe {
            border: 0;
            border-radius: 12px;
            background: white;
        }

        @media (max-width: 760px) {
            .hero {
                padding: 1.35rem;
            }

            .hero h1 {
                font-size: 2rem;
            }

            .metric-row {
                grid-template-columns: 1fr;
            }

        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(fire_data_sample: pd.DataFrame) -> None:
    min_year = int(fire_data_sample["YEAR"].min())
    max_year = int(fire_data_sample["YEAR"].max())
    province_count = fire_data_sample["SRC_AGENCY"].nunique()

    st.markdown(
        f"""
        <div id="overview"></div>
        <div class="hero">
            <div class="eyebrow">Canadian National Fire Database sample</div>
            <h1>Understanding Fire Severity in Canada</h1>
            <p>
                An interactive web version of the original notebook dashboards.
                Explore where fires are reported, how causes vary by region and year,
                and how fire size changes across provinces, causes, and severity groups.
            </p>
        </div>
        <div class="metric-row">
            <div class="metric-card">
                <span>Sample size</span>
                <strong>{len(fire_data_sample):,}</strong>
            </div>
            <div class="metric-card">
                <span>Year range</span>
                <strong>{min_year}-{max_year}</strong>
            </div>
            <div class="metric-card">
                <span>Source agencies</span>
                <strong>{province_count}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    st.sidebar.title("Sections")
    st.sidebar.markdown(
        """
        - [Overview](#overview)
        - [Project Context](#project-context)
        - [Choose a Dashboard](#choose-dashboard)
        - [How to Use This View](#how-to-use-this-view)
        - [Dashboard](#dashboard)
        - [Interpretation](#interpretation)
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Use these links to move through the interactive report.")


def render_report_sections() -> None:
    st.markdown(
        """
        <div id="project-context"></div>
        <div class="section-label">Project Context</div>
        <div class="section-stack">
            <div class="report-section">
                <div class="report-kicker">01</div>
                <h3>Dataset Description</h3>
                <p>
                    The visualization uses a 20,000-row sample from the Canadian National
                    Fire Database, focusing on reported wildfire events, fire size, cause,
                    location, year, and source agency.
                </p>
            </div>
            <div class="report-section">
                <div class="report-kicker">02</div>
                <h3>Intended Audience</h3>
                <p>
                    The primary audience is the general Canadian public: people who want
                    to understand wildfire patterns by region, cause, severity, and time
                    without reading raw tabular data.
                </p>
            </div>
            <div class="report-section">
                <div class="report-kicker">03</div>
                <h3>General Takeaway</h3>
                <p>
                    The dashboards emphasize that fire activity is spatially uneven:
                    different provinces show different cause profiles, and severe events
                    can stand apart from ordinary fire-frequency patterns.
                </p>
            </div>
            <div class="report-section">
                <div class="report-kicker">04</div>
                <h3>How to Explore</h3>
                <p>
                    Treat each view as a coordinated dashboard. Click, brush, filter, and
                    hover to move between overview patterns and individual fire records.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard_selector() -> str:
    st.markdown('<div id="choose-dashboard"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            """
            <div class="eyebrow">Interactive Dashboards</div>
            <h2 class="dashboard-title">Choose a Dashboard</h2>
            <p>
                Select one dashboard to load below. The first view focuses on where
                fires occur and how causes change by region and year; the second view
                focuses on wildfire size, severity, and regional/cause-based comparisons.
            </p>
            """,
            unsafe_allow_html=True,
        )
        return st.radio(
            "Select one dashboard to explore",
            [
                "Wildfire Event Frequency Over Time by Fire Cause",
                "Average Wildfire Size by Severity: Regional and Cause-Based Comparisons",
            ],
            horizontal=True,
            label_visibility="collapsed",
        )


def render_dashboard_intro(dashboard: str) -> None:
    if dashboard == "Wildfire Event Frequency Over Time by Fire Cause":
        title = "Wildfire Event Frequency Over Time by Fire Cause"
        instructions = [
            "Start by clicking a province on the map. The selected province turns yellow, and the bar chart updates to summarize fire causes for that region.",
            "Use the Show All Years checkbox for the long-term overview. Uncheck it when you want the year slider to show one selected year at a time.",
            "Click one fire cause in the bar chart to reveal matching fire locations on the map.",
            "Hover over provinces, bars, or fire points to inspect the province, cause, year, month, agency, and fire size details.",
        ]
        tips = ["Click a province", "Adjust year", "Select a cause", "Hover for details"]
    else:
        title = "Average Wildfire Size by Severity"
        instructions = [
            "Choose a severity category from the dropdown to focus on small, medium, large, or extreme fires.",
            "Drag across the strip plot to brush a fire-size range. The province and cause summaries update to that selected range.",
            "Click a province bar to highlight fires from that province in the strip plot.",
            "Click a cause in the lollipop chart to isolate that cause and compare its fire-size pattern against the others.",
        ]
        tips = ["Choose severity", "Brush a size range", "Click province bars", "Compare causes"]

    tip_html = "".join(f'<span class="tip-pill">{tip}</span>' for tip in tips)
    instruction_html = "".join(f"<li>{instruction}</li>" for instruction in instructions)
    st.markdown(
        f"""
        <div id="how-to-use-this-view"></div>
        <div class="section-card">
            <h2 class="dashboard-title">{title}</h2>
            <p>Use this dashboard as an interactive exploration tool:</p>
            <ol class="instruction-list">{instruction_html}</ol>
            <div class="tip-row">{tip_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard_one_chart(chart: alt.Chart) -> None:
    html = chart.to_html()
    fit_styles = """
    <style>
      body {
        margin: 0;
        background: white;
      }

      #vis {
        transform: scale(0.9);
        transform-origin: top left;
        width: 112%;
      }

      .vega-embed,
      .vega-embed > div,
      .vega-embed svg {
        overflow: visible;
      }
    </style>
    """
    html = html.replace(
        "</head>",
        f"{fit_styles}</head>",
        1,
    )
    components.html(
        html,
        height=780,
        scrolling=False,
    )


def render_dashboard_chart(dashboard: str, fire_data_sample: pd.DataFrame) -> None:
    st.markdown('<div id="dashboard"></div>', unsafe_allow_html=True)
    if dashboard == "Wildfire Event Frequency Over Time by Fire Cause":
        render_dashboard_one_chart(build_dashboard_one(fire_data_sample))
    else:
        st.altair_chart(build_dashboard_two(fire_data_sample))


def render_dashboard_interpretation(dashboard: str) -> None:
    if dashboard == "Wildfire Event Frequency Over Time by Fire Cause":
        question = (
            "How do wildfire frequencies vary across regions and causes, and how do "
            "these patterns change over time?"
        )
        view_items = [
            "The left map combines province polygons with point marks for individual fire events.",
            "The right bar chart summarizes fire-cause frequency for the selected province and year setting.",
            "Color links fire causes across views, while province highlighting shows the current spatial focus.",
        ]
        reading_items = [
            "Use the map first for spatial patterns, then use the bar chart to interpret cause composition.",
            "Compare all-years patterns with year-specific patterns by toggling Show All Years.",
            "Look for provinces where one cause dominates, or where fire points cluster strongly in certain areas.",
        ]
        strength_items = [
            "The geographic map makes regional fire patterns immediately visible.",
            "Linked selections reduce manual cross-referencing between province, cause, and location.",
            "Tooltips preserve detailed record-level information without cluttering the main view.",
        ]
        limitation_items = [
            "Dense regions such as BC or Alberta may have overlapping points that are harder to inspect individually.",
            "Only one selected year can be compared at a time, so multi-year comparison requires memory.",
            "The view uses a 20,000-record sample, so it should be interpreted as exploratory rather than complete.",
        ]
    else:
        question = (
            "How does fire severity change across provinces and fire causes, and which "
            "events appear unusually severe compared with typical patterns?"
        )
        view_items = [
            "The top jittered strip plot shows individual fire sizes by province or agency.",
            "The lower-left bar chart compares average fire size by province.",
            "The lower-right lollipop chart compares average fire size by fire cause.",
        ]
        reading_items = [
            "Start with the severity dropdown to choose an overall view or a specific severity class.",
            "Brush the strip plot to focus on a fire-size range and watch the summaries update.",
            "Use province and cause selections to connect individual event distributions to aggregate averages.",
        ]
        strength_items = [
            "The strip plot preserves individual events, making outliers easier to notice.",
            "The linked summaries support both regional and cause-based comparison.",
            "The severity filter improves readability by separating small, medium, large, and extreme events.",
        ]
        limitation_items = [
            "Severity classes cannot be viewed side by side, so direct category comparison requires switching.",
            "The full overall distribution can still be crowded before filtering.",
            "Single-selection behavior limits comparison of multiple provinces or causes at once.",
        ]

    def list_html(items: list[str]) -> str:
        return "".join(f"<li>{item}</li>" for item in items)

    st.markdown(
        f"""
        <div id="interpretation"></div>
        <div class="section-card">
            <div class="eyebrow">Dashboard Interpretation</div>
            <h2>How to Read This View</h2>
            <p><strong>Analytic question:</strong> {question}</p>
            <div class="interpretation-grid">
                <div class="interpretation-card">
                    <h3>What the View Shows</h3>
                    <ul>{list_html(view_items)}</ul>
                </div>
                <div class="interpretation-card">
                    <h3>Reading Strategy</h3>
                    <ul>{list_html(reading_items)}</ul>
                </div>
                <div class="interpretation-card">
                    <h3>Strengths</h3>
                    <ul>{list_html(strength_items)}</ul>
                </div>
                <div class="interpretation-card">
                    <h3>Limitations</h3>
                    <ul>{list_html(limitation_items)}</ul>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="Canadian Fire Visualization",
        layout="wide",
    )

    inject_styles()
    render_sidebar()

    fire_data_sample = load_fire_data()
    render_hero(fire_data_sample)
    render_report_sections()
    dashboard = render_dashboard_selector()

    render_dashboard_intro(dashboard)
    render_dashboard_chart(dashboard, fire_data_sample)
    render_dashboard_interpretation(dashboard)


if __name__ == "__main__":
    main()
