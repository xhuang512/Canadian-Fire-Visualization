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
            --muted: #52616a;
            --line: rgba(30, 42, 48, 0.12);
            --panel: rgba(255, 255, 255, 0.92);
            --ember: #c95f2e;
            --gold: #f2b84b;
            --green: #2f6f68;
            --radius: 14px;
            --surface-shadow: 0 12px 34px rgba(31, 43, 47, 0.08);
        }

        html {
            scroll-behavior: smooth;
        }

        /* Page shell and Streamlit chrome */
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(242, 184, 75, 0.28), transparent 30rem),
                linear-gradient(135deg, #f8f4ea 0%, #eef3f1 44%, #f7f1e8 100%);
            color: var(--ink);
        }

        header[data-testid="stHeader"] {
            background: transparent;
        }

        .block-container {
            max-width: 1320px;
            padding-top: 1.35rem;
            padding-bottom: 3rem;
        }

        div[data-testid="stToolbar"] {
            display: none;
        }

        /* Portfolio hero and project metadata */
        .hero {
            border: 1px solid var(--line);
            border-radius: var(--radius);
            padding: 1.8rem 2rem;
            background:
                linear-gradient(120deg, rgba(255, 255, 255, 0.94), rgba(255, 255, 255, 0.76)),
                linear-gradient(90deg, rgba(201, 95, 46, 0.12), rgba(47, 111, 104, 0.12));
            box-shadow: var(--surface-shadow);
        }

        .section-eyebrow {
            color: var(--ember);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            line-height: 1.2;
            margin: 0 0 0.5rem;
        }

        .hero h1 {
            font-size: 2.7rem;
            line-height: 1.06;
            margin: 0 0 0.85rem 0;
            letter-spacing: 0;
        }

        .hero p {
            max-width: 900px;
            color: var(--muted);
            font-size: 1.05rem;
            line-height: 1.58;
            margin: 0;
        }

        .tech-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 1rem;
        }

        .tech-chip {
            border: 1px solid rgba(47, 111, 104, 0.16);
            border-radius: 999px;
            padding: 0.28rem 0.62rem;
            color: #3f5b57;
            background: rgba(255, 255, 255, 0.55);
            font-size: 0.75rem;
            font-weight: 650;
        }

        .metric-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.8rem;
            margin: 0.9rem 0 1.6rem;
        }

        .metric-card {
            border: 1px solid var(--line);
            border-radius: var(--radius);
            padding: 0.8rem 1rem;
            background: var(--panel);
            box-shadow: 0 8px 24px rgba(31, 43, 47, 0.07);
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

        /* Shared content surfaces */
        .section-card {
            border: 1px solid var(--line);
            border-radius: var(--radius);
            padding: 1.1rem 1.2rem;
            margin: 1rem 0;
            background: var(--panel);
            box-shadow: var(--surface-shadow);
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

        .project-section {
            margin-top: 1.6rem;
        }

        /* Compact project overview */
        .project-glance {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            margin-top: 0.75rem;
            border-top: 1px solid var(--line);
        }

        .glance-item {
            padding: 1rem 1.15rem;
            border-bottom: 1px solid var(--line);
        }

        .glance-item:nth-child(odd) {
            border-right: 1px solid var(--line);
        }

        .glance-item:nth-last-child(-n + 2) {
            border-bottom: 0;
        }

        .glance-item h3 {
            margin: 0 0 0.32rem;
            color: var(--green);
            font-size: 0.95rem;
            letter-spacing: 0;
        }

        .glance-item p {
            margin: 0;
            color: var(--muted);
            line-height: 1.52;
            font-size: 0.92rem;
        }

        /* Insight summary */
        .interpretation-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.8rem;
            margin-top: 0.8rem;
        }

        .interpretation-card {
            border: 1px solid rgba(30, 42, 48, 0.1);
            border-radius: var(--radius);
            padding: 0.9rem 1rem;
            background: rgba(255, 255, 255, 0.72);
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
            margin: 0.24rem 0;
        }

        .notice-panel {
            border-left: 4px solid var(--ember);
            border-radius: var(--radius);
            padding: 0.9rem 1rem;
            margin-top: 0.8rem;
            background: rgba(201, 95, 46, 0.07);
        }

        .notice-panel h3 {
            margin: 0 0 0.35rem;
            font-size: 1rem;
        }

        .notice-panel p {
            margin: 0;
            color: #44535c;
            line-height: 1.55;
        }

        /* Dashboard selector and interaction guide */
        .interaction-strip {
            margin: 0.8rem 0 0.55rem;
        }

        .interaction-list {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.6rem 1.5rem;
            margin: 0.75rem 0 0;
            padding: 0;
            list-style: none;
            counter-reset: interaction-step;
        }

        .interaction-list li {
            position: relative;
            padding-left: 1.75rem;
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.5;
            counter-increment: interaction-step;
        }

        .interaction-list li::before {
            content: counter(interaction-step);
            position: absolute;
            top: 0.05rem;
            left: 0;
            display: grid;
            place-items: center;
            width: 1.25rem;
            height: 1.25rem;
            border-radius: 50%;
            color: var(--green);
            background: rgba(47, 111, 104, 0.11);
            font-size: 0.7rem;
            font-weight: 800;
        }

        .interaction-note {
            margin-top: 0.8rem !important;
            padding: 0.55rem 0.7rem;
            border-left: 3px solid rgba(47, 111, 104, 0.45);
            background: rgba(47, 111, 104, 0.05);
            font-size: 0.85rem;
        }

        div[role="radiogroup"] {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.75rem;
            margin-top: 0.9rem;
        }

        div[role="radiogroup"] label {
            border: 1px solid var(--line);
            border-radius: var(--radius);
            padding: 0.85rem 1rem;
            background: rgba(255, 255, 255, 0.82);
            box-shadow: 0 6px 18px rgba(31, 43, 47, 0.05);
            transition: border-color 160ms ease, background 160ms ease, box-shadow 160ms ease;
        }

        div[role="radiogroup"] label:has(input:checked) {
            border-color: rgba(47, 111, 104, 0.7);
            background: rgba(47, 111, 104, 0.08);
            box-shadow: 0 9px 24px rgba(31, 43, 47, 0.1);
        }

        div[role="radiogroup"] label p {
            color: #203f3b;
            font-size: 1rem;
            font-weight: 800;
            line-height: 1.3;
        }

        div[role="radiogroup"] label p::before {
            display: block;
            margin-bottom: 0.25rem;
            color: var(--ember);
            font-size: 0.7rem;
            font-weight: 750;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }

        div[role="radiogroup"] label p::after {
            display: block;
            margin-top: 0.35rem;
            color: var(--muted);
            font-size: 0.82rem;
            font-weight: 450;
            line-height: 1.45;
        }

        div[role="radiogroup"] label:nth-child(1) p::before {
            content: "Dashboard 1";
        }

        div[role="radiogroup"] label:nth-child(1) p::after {
            content: "Explore where fires occur and how reported causes vary by province and year.";
        }

        div[role="radiogroup"] label:nth-child(2) p::before {
            content: "Dashboard 2";
        }

        div[role="radiogroup"] label:nth-child(2) p::after {
            content: "Compare fire-size distributions, severity groups, provinces, and reported causes.";
        }

        div[data-testid="stVegaLiteChart"] {
            overflow: visible;
        }

        iframe {
            border: 0;
            border-radius: 12px;
            background: white;
        }

        /* Responsive stacking for narrow screens */
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

            .project-glance,
            .interpretation-grid,
            .interaction-list,
            div[role="radiogroup"] {
                grid-template-columns: 1fr;
            }

            .glance-item,
            .glance-item:nth-child(odd),
            .glance-item:nth-last-child(-n + 2) {
                border-right: 0;
                border-bottom: 1px solid var(--line);
            }

            .glance-item:last-child {
                border-bottom: 0;
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
            <div class="section-eyebrow">Interactive data visualization case study</div>
            <h1>Understanding Fire Severity in Canada</h1>
            <p>
                An interactive analysis of 20,000 records from the Canadian National Fire
                Database. The coordinated dashboards reveal how wildfire frequency, causes,
                location, and severity vary across Canada and over time.
            </p>
            <div class="tech-row">
                <span class="tech-chip">Python</span>
                <span class="tech-chip">pandas</span>
                <span class="tech-chip">Altair</span>
                <span class="tech-chip">Streamlit</span>
                <span class="tech-chip">Interactive visualization</span>
            </div>
        </div>
        <div class="metric-row">
            <div class="metric-card">
                <span>Data sample</span>
                <strong>{len(fire_data_sample):,} records</strong>
            </div>
            <div class="metric-card">
                <span>Historical coverage</span>
                <strong>{min_year}-{max_year}</strong>
            </div>
            <div class="metric-card">
                <span>Reporting coverage</span>
                <strong>{province_count} source agencies</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    st.sidebar.title("Project Guide")
    st.sidebar.markdown(
        """
        - [Overview](#overview)
        - [Project](#project)
        - [Dashboards](#dashboards)
        - [How to Interact](#how-to-interact)
        - [Insights](#insights)
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.caption(
        "Explore the project, interact with either dashboard, and review the main findings."
    )


def render_report_sections() -> None:
    st.markdown(
        """
        <div id="project"></div>
        <div class="section-card project-section">
            <div class="section-eyebrow">Project at a Glance</div>
            <h2>Project Overview</h2>
            <div class="project-glance">
            <div class="glance-item">
                <h3>Project Goal</h3>
                <p>
                    Make a large national wildfire dataset easier to explore through
                    coordinated geographic and statistical views.
                </p>
            </div>
            <div class="glance-item">
                <h3>My Contribution</h3>
                <p>
                    Cleaned and standardized historical records, designed two linked
                    Altair dashboards, implemented filtering and tooltips, and converted
                    the notebook work into a public Streamlit application.
                </p>
            </div>
            <div class="glance-item">
                <h3>Data Scope</h3>
                <p>
                    20,000 sampled wildfire records covering location, year, cause,
                    agency, fire size, and severity.
                </p>
            </div>
            <div class="glance-item">
                <h3>Key Idea</h3>
                <p>
                    Regional fire frequency and severe-fire patterns do not always tell
                    the same story, so the project separates event frequency from
                    fire-size and severity analysis.
                </p>
            </div>
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard_selector():
    st.markdown('<div id="dashboards"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            """
            <div class="section-eyebrow">Interactive Dashboards</div>
            <h2 class="dashboard-title">Choose a Dashboard</h2>
            <p>
                Select a view to explore a different dimension of the same wildfire sample.
            </p>
            """,
            unsafe_allow_html=True,
        )
        dashboard = st.radio(
            "Select one dashboard to explore",
            [
                "Wildfire Event Frequency Over Time by Fire Cause",
                "Average Wildfire Size by Severity: Regional and Cause-Based Comparisons",
            ],
            horizontal=True,
            label_visibility="collapsed",
            format_func=lambda option: (
                "Fire Frequency & Cause"
                if option == "Wildfire Event Frequency Over Time by Fire Cause"
                else "Fire Size & Severity"
            ),
        )
        loading_placeholder = st.empty()
        loading_placeholder.info("Loading dashboard...")
        return dashboard, loading_placeholder


def render_dashboard_intro(dashboard: str) -> None:
    st.markdown(
        """
        <div id="how-to-interact"></div>
        <div class="section-card interaction-strip">
            <div class="section-eyebrow">How to Interact</div>
            <h2>Explore the Linked Views</h2>
            <ol class="interaction-list">
                <li>Select a province on the map to highlight it and update the cause summary for that region.</li>
                <li>Adjust the year control to compare long-term patterns with individual years.</li>
                <li>Select a fire cause in the bar chart to filter the mapped fire locations.</li>
                <li>Hover over provinces, bars, or fire points to inspect details such as year, agency, cause, and fire size.</li>
            </ol>
            <p class="interaction-note">
                Selections are linked across the dashboard, so changes in one view update
                the related information in the other.
            </p>
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
        notice = (
            "Fire activity is geographically concentrated, and reported causes vary "
            "substantially across provinces. Comparing the all-years view with individual "
            "years helps separate persistent regional patterns from year-specific variation."
        )
        strength_items = [
            "Linked selections reduce manual cross-referencing between province, cause, and location.",
            "Tooltips preserve record-level detail without crowding the main view.",
            "Province and cause filters support geographic and categorical exploration.",
        ]
        limitation_items = [
            "Dense point clusters in British Columbia and Alberta can create overlap.",
            "Reporting practices may differ by agency and historical period.",
            "The 20,000-row sample is exploratory, not the complete national record.",
        ]
    else:
        notice = (
            "Fire-size distributions are uneven, and a small number of large events can "
            "stand apart from typical fires. Severity filtering helps compare these "
            "distributions across provinces and reported causes while preserving "
            "individual-event context."
        )
        strength_items = [
            "The strip plot preserves individual events and makes outliers easier to notice.",
            "Linked summaries support regional and cause-based comparison.",
            "Severity filtering separates small, medium, large, and extreme events.",
        ]
        limitation_items = [
            "Severity classes cannot be viewed side by side.",
            "The overall distribution can be crowded before filtering.",
            "Single selections limit comparison of multiple provinces or causes at once.",
        ]

    def list_html(items: list[str]) -> str:
        return "".join(f"<li>{item}</li>" for item in items)

    st.markdown(
        f"""
        <div id="insights"></div>
        <div class="section-card">
            <div class="section-eyebrow">Dashboard Interpretation</div>
            <h2>Key Insights and Design Notes</h2>
            <div class="notice-panel">
                <h3>What to notice</h3>
                <p>{notice}</p>
            </div>
            <div class="interpretation-grid">
                <div class="interpretation-card">
                    <h3>Design strengths</h3>
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
    dashboard, loading_placeholder = render_dashboard_selector()

    render_dashboard_intro(dashboard)
    render_dashboard_chart(dashboard, fire_data_sample)
    loading_placeholder.empty()
    render_dashboard_interpretation(dashboard)


if __name__ == "__main__":
    main()
