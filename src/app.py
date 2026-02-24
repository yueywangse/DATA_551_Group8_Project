
"""
Vancouver Crime Patterns Dashboard (Prototype with neighbourhood polygon map)

How to run:
1) Put your Kaggle CSV at: data/raw/crime.csv (or change DATA_PATH)
2) Download a Vancouver neighbourhood/local-area GeoJSON and save to: data/geo/local_areas.geojson
3) Install deps: pip install dash plotly pandas numpy
4) Run: python src/app.py
Open: http://127.0.0.1:8050

Your dataset columns (from screenshot):
TYPE, YEAR, MONTH, DAY, HOUR, MINUTE, HUNDRED_BLOCK, NEIGHBOURHOOD, X, Y
"""

from __future__ import annotations

import json
import numpy as np
import pandas as pd

from dash import Dash, dcc, html, Input, Output
import plotly.express as px


# -----------------------------
# Config
# -----------------------------
DATA_PATH = "data/raw/crimes.csv"                 # path  to the dataset
GEOJSON_PATH = "data/raw/local_areas.geojson"    # path to the map json file
DEV_NROWS = None  # set to e.g. 200000 during dev for speed, or None for full file

USECOLS = [
    "TYPE", "YEAR", "MONTH", "DAY", "HOUR", "MINUTE",
    "HUNDRED_BLOCK", "NEIGHBOURHOOD", "X", "Y",
]

TOD_OPTIONS = ["Morning (6–12)", "Afternoon (12–18)", "Evening (18–24)", "Night (0–6)"]


# -----------------------------
# Data load + prep
# -----------------------------
def load_data(path: str, nrows: int | None = None) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=USECOLS, nrows=nrows)

    df["TYPE"] = df["TYPE"].astype("string")
    df["NEIGHBOURHOOD"] = df["NEIGHBOURHOOD"].astype("string")

    for c in ["YEAR", "MONTH", "DAY", "HOUR", "MINUTE"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    df["DATE"] = pd.to_datetime(
        dict(year=df["YEAR"], month=df["MONTH"], day=df["DAY"]),
        errors="coerce",
    )

    hr = df["HOUR"].astype("float")
    tod = pd.Series(index=df.index, dtype="string")
    tod[(hr >= 6) & (hr < 12)] = "Morning (6–12)"
    tod[(hr >= 12) & (hr < 18)] = "Afternoon (12–18)"
    tod[(hr >= 18) & (hr < 24)] = "Evening (18–24)"
    tod[(hr >= 0) & (hr < 6)] = "Night (0–6)"
    df["TIME_OF_DAY"] = tod.astype("string")

    df = df.dropna(subset=["YEAR", "TYPE", "NEIGHBOURHOOD", "HOUR", "MONTH"])
    return df


def load_geojson(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# -----------------------------
# Filtering
# -----------------------------
def filter_df(
    df: pd.DataFrame,
    year: int | None,
    crime_types: list[str] | None,
    time_of_day: list[str] | None,
) -> pd.DataFrame:
    out = df
    if year is not None:
        out = out[out["YEAR"] == year]
    if crime_types:
        out = out[out["TYPE"].isin(crime_types)]
    if time_of_day:
        out = out[out["TIME_OF_DAY"].isin(time_of_day)]
    return out


# -----------------------------
# GeoJSON matching helpers
# -----------------------------
def _geojson_feature_property_keys(geojson: dict) -> list[str]:
    feats = geojson.get("features", [])
    if not feats:
        return []
    props = feats[0].get("properties", {})
    return list(props.keys())


def detect_featureidkey_and_mapping(geojson: dict, df_neigh_values: list[str]) -> tuple[str, dict[str, str]]:
    """
    Tries common GeoJSON property names and returns:
      - featureidkey string like "properties.name"
      - mapping dict from df neighbourhood names -> GeoJSON neighbourhood names (identity if match)

    This makes the prototype resilient if the GeoJSON uses different property keys.
    """
    candidate_props = [
        "name", "Name", "NAME",
        "local_area", "LOCAL_AREA", "LocalArea",
        "neighbourhood", "NEIGHBOURHOOD", "Neighbourhood",
        "area_name", "AREA_NAME",
    ]

    prop_keys = _geojson_feature_property_keys(geojson)
    feats = geojson.get("features", [])

    # Build GeoJSON name sets for each candidate property
    best_prop = None
    best_overlap = -1
    best_geo_names = None

    df_set = set([str(x).strip() for x in df_neigh_values if x is not None])

    for prop in candidate_props:
        if prop not in prop_keys:
            continue
        geo_names = set()
        for ft in feats:
            v = ft.get("properties", {}).get(prop)
            if v is not None:
                geo_names.add(str(v).strip())

        overlap = len(df_set.intersection(geo_names))
        if overlap > best_overlap:
            best_overlap = overlap
            best_prop = prop
            best_geo_names = geo_names

    # If none matched, fall back to first property key (still works if user adjusts mapping later)
    if best_prop is None:
        if not prop_keys:
            # No properties at all — extremely unlikely, but guard anyway
            return "properties.name", {}
        best_prop = prop_keys[0]
        best_geo_names = set(str(ft.get("properties", {}).get(best_prop, "")).strip() for ft in feats)

    # Mapping: for prototype, try identity + simple normalization
    # If you later find mismatches, add explicit rules to this mapping.
    mapping: dict[str, str] = {}
    geo_list = list(best_geo_names or [])
    geo_norm = {normalize_name(g): g for g in geo_list}

    for n in df_set:
        nn = normalize_name(n)
        if nn in geo_norm:
            mapping[n] = geo_norm[nn]
        else:
            # leave unmapped — it just won't appear on choropleth
            pass

    featureidkey = f"properties.{best_prop}"
    return featureidkey, mapping


def normalize_name(s: str) -> str:
    # lower, remove punctuation-ish, collapse spaces
    s = s.lower().strip()
    for ch in [".", ",", "-", "_", "/", "’", "'", "(", ")", "&"]:
        s = s.replace(ch, " ")
    s = " ".join(s.split())
    return s


# -----------------------------
# Summary + charts
# -----------------------------
def clicked_neighbourhood(click_data: dict | None) -> str | None:
    """
    For choropleth polygons, clickData points often include:
      point["location"] = the value from locations=
    """
    if not click_data or "points" not in click_data or not click_data["points"]:
        return None
    return click_data["points"][0].get("location")


def make_summary(df_filt: pd.DataFrame, selected_neigh: str | None) -> dict:
    d = df_filt
    selected_area_label = "All neighbourhoods"

    if selected_neigh:
        d = d[d["NEIGHBOURHOOD"] == selected_neigh]
        selected_area_label = selected_neigh

    total = int(len(d))

    if total > 0:
        peak_hour = d["HOUR"].value_counts().idxmax()
        peak_hour_str = f"{int(peak_hour):02d}:00–{(int(peak_hour) + 1) % 24:02d}:00"
        top_type = str(d["TYPE"].value_counts().idxmax())
    else:
        peak_hour_str = "—"
        top_type = "—"

    return {
        "selected_area": selected_area_label,
        "total_incidents": total,
        "peak_hour": peak_hour_str,
        "top_type": top_type,
    }


def neighbourhood_counts(df_filt: pd.DataFrame) -> pd.DataFrame:
    return (
        df_filt.groupby("NEIGHBOURHOOD", as_index=False)
        .size()
        .rename(columns={"size": "incidents"})
    )


def fig_neighbourhood_map(
    df_filt: pd.DataFrame,
    geojson: dict,
    featureidkey: str,
    name_mapping: dict[str, str],
    selected_neigh: str | None,
):
    counts = neighbourhood_counts(df_filt).copy()

    # Map df neighbourhood labels to geojson labels (if matchable)
    counts["NEIGH_GEO"] = counts["NEIGHBOURHOOD"].map(name_mapping)
    counts = counts.dropna(subset=["NEIGH_GEO"])

    # If everything drops out due to mismatch, show an empty map with a helpful title
    if counts.empty:
        fig = px.choropleth_mapbox(
            pd.DataFrame({"NEIGH_GEO": [], "incidents": []}),
            geojson=geojson,
            locations="NEIGH_GEO",
            featureidkey=featureidkey,
            color="incidents",
            mapbox_style="open-street-map",
            zoom=11,
            center={"lat": 49.2827, "lon": -123.1207},
            opacity=0.55,
            title="Neighbourhood map (name matching needed)",
        )
        fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
        return fig

    # Choropleth
    fig = px.choropleth_mapbox(
        counts,
        geojson=geojson,
        locations="NEIGH_GEO",
        featureidkey=featureidkey,
        color="incidents",
        mapbox_style="open-street-map",   # no token needed
        zoom=11,
        center={"lat": 49.2827, "lon": -123.1207},
        opacity=0.55,
        hover_name="NEIGH_GEO",
        hover_data={"incidents": True},
        title="Incidents by neighbourhood (click a polygon to filter)",
    )

    # Highlight selected neighbourhood border (visual affordance)
    if selected_neigh and selected_neigh in name_mapping:
        selected_geo = name_mapping[selected_neigh]
        # Add outline by re-plotting selected polygon in a second layer (simple approach)
        # We do this by adding an extra trace with the same geojson but a constant color.
        selected_df = pd.DataFrame({"NEIGH_GEO": [selected_geo], "incidents": [counts["incidents"].max()]})
        sel = px.choropleth_mapbox(
            selected_df,
            geojson=geojson,
            locations="NEIGH_GEO",
            featureidkey=featureidkey,
            color="incidents",
            color_continuous_scale=["rgba(0,0,0,0)", "rgba(0,0,0,0)"],  # transparent fill
            mapbox_style="open-street-map",
            zoom=11,
            center={"lat": 49.2827, "lon": -123.1207},
            opacity=0.0,
        )
        for tr in sel.data:
            tr.marker = getattr(tr, "marker", {})
            # outline effect
            tr.marker.line = {"width": 4, "color": "black"}
            tr.showlegend = False
            fig.add_trace(tr)

    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


def fig_monthly(df_focus: pd.DataFrame):
    d = df_focus.copy()
    month_map = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
    d["MONTH_NAME"] = d["MONTH"].astype(int).map(month_map)

    grp = (
        d.groupby(["MONTH", "MONTH_NAME"], as_index=False)
        .size()
        .sort_values("MONTH")
    )
    fig = px.bar(grp, x="MONTH_NAME", y="size", title="Monthly trend (# incidents)")
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    fig.update_yaxes(title="# incidents")
    fig.update_xaxes(title="")
    return fig


def fig_hourly(df_focus: pd.DataFrame):
    grp = (
        df_focus.groupby("HOUR", as_index=False)
        .size()
        .sort_values("HOUR")
    )
    fig = px.bar(grp, x="HOUR", y="size", title="Hourly distribution (# incidents)")
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    fig.update_yaxes(title="# incidents")
    fig.update_xaxes(title="Hour of day")
    return fig


def fig_type_comparison(df_focus: pd.DataFrame):
    top_types = df_focus["TYPE"].value_counts().head(8).index.tolist()
    d = df_focus[df_focus["TYPE"].isin(top_types)]
    grp = (
        d.groupby("TYPE", as_index=False)
        .size()
        .sort_values("size", ascending=True)
    )
    fig = px.bar(grp, x="size", y="TYPE", orientation="h", title="Crime type comparison (top 8)")
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    fig.update_xaxes(title="# incidents")
    fig.update_yaxes(title="")
    return fig


# -----------------------------
# Initialize
# -----------------------------
df_all = load_data(DATA_PATH, nrows=DEV_NROWS)
geo = load_geojson(GEOJSON_PATH)

years = sorted(df_all["YEAR"].dropna().astype(int).unique().tolist())
crime_types_all = sorted(df_all["TYPE"].dropna().unique().tolist())

default_year = max(years) if years else None

# Detect how to match NEIGHBOURHOOD labels to GeoJSON polygons
featureidkey, name_mapping = detect_featureidkey_and_mapping(
    geojson=geo,
    df_neigh_values=sorted(df_all["NEIGHBOURHOOD"].dropna().unique().tolist())[:500],
)

# -----------------------------
# App
# -----------------------------
app = Dash(__name__)
server = app.server

app.layout = html.Div(
    style={"fontFamily": "Arial", "backgroundColor": "#F7F7F7", "padding": "10px"},
    children=[
        html.H2("Vancouver Crime Patterns Dashboard", style={"textAlign": "center"}),

        html.Div(
            style={"display": "flex", "gap": "12px"},
            children=[
                # Left controls
                html.Div(
                    style={"flex": "1", "backgroundColor": "white", "padding": "12px", "borderRadius": "10px"},
                    children=[
                        html.H4("FILTER CRIME DATA"),

                        html.Label("Year"),
                        dcc.Dropdown(
                            id="year_dropdown",
                            options=[{"label": str(y), "value": int(y)} for y in years],
                            value=default_year,
                            clearable=False,
                        ),

                        html.Br(),
                        html.Label("Crime Type Filter"),
                        dcc.Checklist(
                            id="type_checklist",
                            options=[{"label": t, "value": t} for t in crime_types_all],
                            value=crime_types_all[:4],
                            inputStyle={"marginRight": "8px"},
                        ),

                        html.Hr(),
                        html.Label("Time Filter"),
                        dcc.Checklist(
                            id="tod_checklist",
                            options=[{"label": t, "value": t} for t in TOD_OPTIONS],
                            value=TOD_OPTIONS,
                            inputStyle={"marginRight": "8px"},
                        ),

                        html.Br(),
                        html.Button("Reset filters", id="reset_btn", n_clicks=0),

                        html.Hr(),
                        html.Div(
                            style={"fontSize": "12px", "color": "#666"},
                            children=[
                                "Map note: This uses neighbourhood polygons (GeoJSON). ",
                                "If the map shows blank, your NEIGHBOURHOOD names may not match the GeoJSON names. ",
                                "In that case, add a mapping dictionary in code."
                            ],
                        ),
                    ],
                ),

                # Center: map + charts
                html.Div(
                    style={"flex": "2.2", "backgroundColor": "white", "padding": "12px", "borderRadius": "10px"},
                    children=[
                        dcc.Graph(
                            id="map_graph",
                            figure=fig_neighbourhood_map(
                                filter_df(df_all, default_year, crime_types_all[:4], TOD_OPTIONS),
                                geojson=geo,
                                featureidkey=featureidkey,
                                name_mapping=name_mapping,
                                selected_neigh=None,
                            ),
                            style={"height": "420px"},
                            config={"displayModeBar": True},  # enables zoom/pan tools
                        ),

                        html.Div(
                            style={"display": "flex", "gap": "10px"},
                            children=[
                                html.Div(style={"flex": "1"}, children=[dcc.Graph(id="monthly_graph")]),
                                html.Div(style={"flex": "1"}, children=[dcc.Graph(id="hourly_graph")]),
                                html.Div(style={"flex": "1"}, children=[dcc.Graph(id="type_graph")]),
                            ],
                        ),
                    ],
                ),

                # Right summary
                html.Div(
                    style={"flex": "1", "backgroundColor": "white", "padding": "12px", "borderRadius": "10px"},
                    children=[
                        html.H4("INCIDENT SUMMARY"),
                        html.Div(id="summary_year", style={"fontSize": "18px", "fontWeight": "bold"}),

                        html.Br(),
                        html.Div(["Selected Area: ", html.Span(id="summary_area", style={"fontWeight": "bold"})]),
                        html.Br(),
                        html.Div(["Total Incidents: ", html.Span(id="summary_total", style={"fontWeight": "bold", "fontSize": "24px"})]),
                        html.Br(),
                        html.Div(["Peak Hour: ", html.Span(id="summary_peak", style={"fontWeight": "bold"})]),
                        html.Br(),
                        html.Div(["Top Crime Type: ", html.Span(id="summary_top_type", style={"fontWeight": "bold"})]),

                        html.Hr(),
                        html.Div(
                            style={"fontSize": "12px", "color": "#555"},
                            children="Tip: Click a neighbourhood polygon to filter the charts."
                        )
                    ],
                ),
            ],
        ),
    ],
)


# Reset filters callback
@app.callback(
    Output("year_dropdown", "value"),
    Output("type_checklist", "value"),
    Output("tod_checklist", "value"),
    Input("reset_btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset_filters(_n):
    return default_year, crime_types_all[:4], TOD_OPTIONS


# Main update callback
@app.callback(
    Output("map_graph", "figure"),
    Output("monthly_graph", "figure"),
    Output("hourly_graph", "figure"),
    Output("type_graph", "figure"),
    Output("summary_year", "children"),
    Output("summary_area", "children"),
    Output("summary_total", "children"),
    Output("summary_peak", "children"),
    Output("summary_top_type", "children"),
    Input("year_dropdown", "value"),
    Input("type_checklist", "value"),
    Input("tod_checklist", "value"),
    Input("map_graph", "clickData"),
)
def update_dashboard(year, types_selected, tod_selected, clickData):
    df_f = filter_df(df_all, year, types_selected, tod_selected)

    # Determine selected neighbourhood from map click
    selected_geo_name = clicked_neighbourhood(clickData)  # this is GeoJSON label
    selected_neigh = None
    if selected_geo_name:
        # reverse map geo_name -> df neighbourhood name if possible
        reverse_map = {v: k for k, v in name_mapping.items()}
        selected_neigh = reverse_map.get(selected_geo_name)

    df_focus = df_f
    if selected_neigh:
        df_focus = df_f[df_f["NEIGHBOURHOOD"] == selected_neigh]

    map_fig = fig_neighbourhood_map(
        df_f,
        geojson=geo,
        featureidkey=featureidkey,
        name_mapping=name_mapping,
        selected_neigh=selected_neigh,
    )

    if len(df_focus):
        m_fig = fig_monthly(df_focus)
        h_fig = fig_hourly(df_focus)
        t_fig = fig_type_comparison(df_focus)
    else:
        m_fig = px.bar(title="Monthly trend (# incidents)")
        h_fig = px.bar(title="Hourly distribution (# incidents)")
        t_fig = px.bar(title="Crime type comparison (top 8)")

    summ = make_summary(df_f, selected_neigh)
    summ_year = f"Year: {year}" if year is not None else "Year: —"

    return (
        map_fig, m_fig, h_fig, t_fig,
        summ_year,
        summ["selected_area"],
        f'{summ["total_incidents"]:,}',
        summ["peak_hour"],
        summ["top_type"],
    )


if __name__ == "__main__":
    # Dash v3+: use app.run (run_server is deprecated)
    app.run(debug=True)
