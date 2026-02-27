"""
Vancouver Crime Patterns Dashboard (Neighbourhood polygon map + zoom-to-points)

Behavior requested:
- Choropleth (NOT zoomed): map has NO CRIME_GROUP legend; left Crime Type checklist shows ONLY text (no dots)
- Zoomed (selected neighbourhood): map switches to points colored by CRIME_GROUP (legend appears);
  left Crime Type checklist shows colored dots per type (same colors for same group)

How to run:
1) Put your Kaggle CSV at: data/raw/crimes.csv (or change DATA_PATH)
2) Download a Vancouver neighbourhood/local-area GeoJSON and save to: data/raw/local_areas.geojson
3) pip install dash plotly pandas numpy pyproj
4) python src/app.py
Open: http://127.0.0.1:8050
"""

from __future__ import annotations

import os
import json
import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dash import Dash, dcc, html, Input, Output, State, callback_context
from pyproj import Transformer

# -----------------------------
# Config
# -----------------------------
DATA_PATH = "data/raw/crimes.csv"
GEOJSON_PATH = "data/raw/local_areas.geojson"
#DEV_NROWS = None

DEV_NROWS = 200000
df = load_data(DATA_PATH, nrows=DEV_NROWS)

USECOLS = [
    "TYPE", "YEAR", "MONTH", "DAY", "HOUR", "MINUTE",
    "HUNDRED_BLOCK", "NEIGHBOURHOOD", "X", "Y",
]

TOD_OPTIONS = ["Morning (6–12)", "Afternoon (12–18)", "Evening (18–24)", "Night (0–6)"]

# -----------------------------
# Crime grouping (point colors)
# -----------------------------
GROUP_COLORS = {
    "Violent": "#d62728",      # red
    "Theft": "#ff7f0e",        # orange
    "Nonviolent": "#1f77b4",   # blue
}

def crime_group_from_type(t: str) -> str:
    s = str(t).lower()
    violent_kw = [
        "assault", "robbery", "homicide", "sexual", "rape", "kidnap",
        "weapon", "shoot", "stab", "violence", "murder"
    ]
    theft_kw = [
        "theft", "break and enter", "b&e", "burglary",
        "stolen", "shoplift", "larceny",
        "vehicle theft", "theft of vehicle", "theft from vehicle"
    ]
    if any(k in s for k in violent_kw):
        return "Violent"
    if any(k in s for k in theft_kw):
        return "Theft"
    return "Nonviolent"

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

    # group column for map point coloring
    df["CRIME_GROUP"] = df["TYPE"].apply(crime_group_from_type).astype("string")

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
def normalize_name(s: str) -> str:
    s = str(s).lower().strip()
    for ch in [".", ",", "-", "_", "/", "’", "'", "(", ")", "&"]:
        s = s.replace(ch, " ")
    s = " ".join(s.split())
    return s

def _geojson_feature_property_keys(geojson: dict) -> list[str]:
    feats = geojson.get("features", [])
    if not feats:
        return []
    props = feats[0].get("properties", {})
    return list(props.keys())

def detect_featureidkey_and_mapping(geojson: dict, df_neigh_values: list[str]) -> tuple[str, dict[str, str]]:
    candidate_props = [
        "name", "Name", "NAME",
        "local_area", "LOCAL_AREA", "LocalArea",
        "neighbourhood", "NEIGHBOURHOOD", "Neighbourhood",
        "area_name", "AREA_NAME",
    ]

    prop_keys = _geojson_feature_property_keys(geojson)
    feats = geojson.get("features", [])
    df_set = set([str(x).strip() for x in df_neigh_values if x is not None])

    best_prop = None
    best_overlap = -1
    best_geo_names = None

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

    if best_prop is None:
        if not prop_keys:
            return "properties.name", {}
        best_prop = prop_keys[0]
        best_geo_names = set(str(ft.get("properties", {}).get(best_prop, "")).strip() for ft in feats)

    mapping: dict[str, str] = {}
    geo_list = list(best_geo_names or [])
    geo_norm = {normalize_name(g): g for g in geo_list}

    for n in df_set:
        nn = normalize_name(n)
        if nn in geo_norm:
            mapping[n] = geo_norm[nn]

    featureidkey = f"properties.{best_prop}"
    return featureidkey, mapping

def clicked_neighbourhood_from_polygon(click_data: dict | None, name_mapping: dict[str, str]) -> str | None:
    if not click_data or "points" not in click_data or not click_data["points"]:
        return None
    pt = click_data["points"][0]
    if "location" not in pt:
        return None
    reverse_map = {v: k for k, v in name_mapping.items()}
    return reverse_map.get(pt["location"])

def get_feature_bounds(
    geojson: dict,
    featureidkey: str,
    feature_name: str,
    map_width_px: int = 800,
    map_height_px: int = 420,
    padding: float = 0.85,
):
    prop_key = featureidkey.split(".")[-1]
    for ft in geojson.get("features", []):
        if str(ft.get("properties", {}).get(prop_key)) == str(feature_name):
            geom = ft.get("geometry", {})
            coords = []

            def extract_coords(g):
                if g["type"] == "Polygon":
                    for ring in g["coordinates"]:
                        coords.extend(ring)
                elif g["type"] == "MultiPolygon":
                    for poly in g["coordinates"]:
                        for ring in poly:
                            coords.extend(ring)

            extract_coords(geom)
            if not coords:
                return None

            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            min_lon, max_lon = min(lons), max(lons)
            min_lat, max_lat = min(lats), max(lats)

            center = {"lon": (min_lon + max_lon) / 2, "lat": (min_lat + max_lat) / 2}

            lon_span = max(max_lon - min_lon, 1e-9)
            lat_span = max(max_lat - min_lat, 1e-9)

            lat_rad = math.radians(center["lat"])
            lon_span_adj = lon_span * math.cos(lat_rad)

            WORLD_SIZE = 512
            zoom_x = math.log2((map_width_px * padding * 360) / (lon_span_adj * WORLD_SIZE))
            zoom_y = math.log2((map_height_px * padding * 360) / (lat_span * WORLD_SIZE))
            zoom = min(zoom_x, zoom_y)
            zoom = max(9.5, min(15, zoom))

            return center, zoom
    return None

# -----------------------------
# Summary + charts
# -----------------------------
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

def fig_monthly(df_focus: pd.DataFrame):
    month_map = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    d = df_focus.copy()
    d["MONTH"] = pd.to_numeric(d["MONTH"], errors="coerce")
    d = d[d["MONTH"].between(1, 12)]
    counts = d["MONTH"].value_counts().reindex(range(1, 13), fill_value=0).sort_index()
    grp = pd.DataFrame({"MONTH": counts.index, "incidents": counts.values, "MONTH_NAME": [month_map[m] for m in counts.index]})
    fig = px.bar(grp, x="MONTH_NAME", y="incidents",
                 category_orders={"MONTH_NAME": list(month_map.values())},
                 title="Monthly trend (# incidents)")
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=300)
    fig.update_yaxes(title="# incidents")
    fig.update_xaxes(title="")
    return fig

def fig_hourly(df_focus: pd.DataFrame):
    grp = df_focus.groupby("HOUR", as_index=False).size().sort_values("HOUR")
    fig = px.bar(grp, x="HOUR", y="size", title="Hourly distribution (# incidents)")
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=300)
    fig.update_yaxes(title="# incidents")
    fig.update_xaxes(title="Hour of day")
    return fig

def fig_type_comparison(df_focus: pd.DataFrame):
    top_types = df_focus["TYPE"].value_counts().head(8).index.tolist()
    d = df_focus[df_focus["TYPE"].isin(top_types)]
    grp = d.groupby("TYPE", as_index=False).size().sort_values("size", ascending=True)
    fig = px.bar(grp, x="size", y="TYPE", orientation="h", title="Crime type comparison (top 8)")
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=300)
    fig.update_xaxes(title="# incidents")
    fig.update_yaxes(title="")
    return fig

def fig_yearly_trend(df_all: pd.DataFrame, types_selected, tod_selected, selected_neigh: str | None):
    d = filter_df(df_all, year=None, crime_types=types_selected, time_of_day=tod_selected).copy()
    d = d[(d["YEAR"] >= 2019) & (d["YEAR"] <= 2023)]

    title = "Yearly trend<br>(2019–2023)"
    if selected_neigh:
        d = d[d["NEIGHBOURHOOD"] == selected_neigh]
        title = f"Yearly trend in {selected_neigh}<br>(2019–2023)"

    counts = d.groupby("YEAR").size().reindex(range(2019, 2024), fill_value=0).reset_index(name="incidents")
    fig = px.line(counts, x="YEAR", y="incidents", markers=True, title=title)
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=280)
    fig.update_yaxes(title="# incidents")
    fig.update_xaxes(title="Year", dtick=1)
    return fig

# -----------------------------
# Map figure (choropleth or zoomed points)
#   - Choropleth: no legend
#   - Zoomed points: legend visible
# -----------------------------
def fig_neighbourhood_map(
    df_filt: pd.DataFrame,
    geojson: dict,
    featureidkey: str,
    name_mapping: dict[str, str],
    selected_neigh: str | None,
):
    map_center = {"lat": 49.2827, "lon": -123.1207}
    map_zoom = 11

    if selected_neigh and selected_neigh in name_mapping:
        selected_geo = name_mapping[selected_neigh]
        bounds = get_feature_bounds(geojson, featureidkey, selected_geo)
        if bounds:
            map_center, map_zoom = bounds

        df_points = df_filt[df_filt["NEIGHBOURHOOD"] == selected_neigh].copy()

        df_points["X"] = pd.to_numeric(df_points["X"], errors="coerce")
        df_points["Y"] = pd.to_numeric(df_points["Y"], errors="coerce")
        df_points = df_points.dropna(subset=["X", "Y"])

        if not df_points.empty:
            if df_points["X"].mean() > 1000:
                transformer = Transformer.from_crs("EPSG:26910", "EPSG:4326", always_xy=True)
                lons, lats = transformer.transform(df_points["X"].values, df_points["Y"].values)
                df_points["lon"] = lons
                df_points["lat"] = lats
            else:
                df_points["lon"] = df_points["X"]
                df_points["lat"] = df_points["Y"]

            df_points["DATETIME_STR"] = (
                df_points["YEAR"].astype(str) + "-" +
                df_points["MONTH"].astype(str).str.zfill(2) + "-" +
                df_points["DAY"].astype(str).str.zfill(2) + " " +
                df_points["HOUR"].astype(str).str.zfill(2) + ":" +
                df_points["MINUTE"].astype(str).str.zfill(2)
            )

        fig = px.scatter_mapbox(
            df_points,
            lat="lat",
            lon="lon",
            color="CRIME_GROUP",
            color_discrete_map=GROUP_COLORS,
            hover_name="TYPE",
            hover_data={
                "CRIME_GROUP": True,
                "DATETIME_STR": True,
                "HUNDRED_BLOCK": True,
                "lat": False,
                "lon": False,
            } if not df_points.empty else None,
            zoom=map_zoom,
            center=map_center,
            mapbox_style="open-street-map",
            title=f"Incidents in {selected_neigh}",
            height=420,
        )
        fig.update_traces(marker=dict(size=10, opacity=0.85))

        # neighbourhood boundary line
        prop_key = featureidkey.split(".")[-1]
        for ft in geojson.get("features", []):
            if str(ft.get("properties", {}).get(prop_key)) == str(selected_geo):
                geom = ft.get("geometry", {})
                if geom.get("type") == "Polygon":
                    polygons = [geom["coordinates"]]
                elif geom.get("type") == "MultiPolygon":
                    polygons = geom["coordinates"]
                else:
                    polygons = []

                for poly in polygons:
                    for ring in poly:
                        lons = [pt[0] for pt in ring]
                        lats = [pt[1] for pt in ring]
                        fig.add_trace(go.Scattermapbox(
                            lon=lons, lat=lats, mode="lines",
                            line=dict(width=3, color="black"),
                            hoverinfo="skip", showlegend=False
                        ))

        fig.update_layout(margin=dict(l=10, r=10, t=55, b=10))
        return fig

    # ---- DEFAULT: choropleth heatmap (no legend) ----
    counts = df_filt.groupby("NEIGHBOURHOOD", as_index=False).size().rename(columns={"size": "incidents"})
    counts["NEIGH_GEO"] = counts["NEIGHBOURHOOD"].map(name_mapping)
    counts = counts.dropna(subset=["NEIGH_GEO"])

    fig = px.choropleth_mapbox(
        counts,
        geojson=geojson,
        locations="NEIGH_GEO",
        featureidkey=featureidkey,
        color="incidents",
        mapbox_style="open-street-map",
        zoom=map_zoom,
        center=map_center,
        opacity=0.55,
        hover_name="NEIGH_GEO",
        hover_data={"incidents": True},
        title="Incidents by neighbourhood (click a polygon to zoom & see points)",
        height=420,
    )

    fig.update_layout(margin=dict(l=10, r=10, t=55, b=10))
    return fig

# -----------------------------
# Crime type checklist options
#   - plain (no dots): used when NOT zoomed
#   - dotted: used when zoomed
# -----------------------------
def make_type_options_plain(types_list: list[str]):
    return [{"label": str(t), "value": t} for t in types_list]

def make_type_options_dotted(types_list: list[str]):
    opts = []
    for t in types_list:
        grp = crime_group_from_type(t)
        dot_color = GROUP_COLORS.get(grp, "#999")

        label = html.Span(
            [
                html.Span(str(t)),
                html.Span(
                    style={
                        "display": "inline-block",
                        "width": "10px",
                        "height": "10px",
                        "marginLeft": "8px",
                        "borderRadius": "50%",
                        "backgroundColor": dot_color,
                        "flex": "0 0 auto",
                    }
                ),
            ],
            style={"display": "flex", "alignItems": "center"},
        )
        opts.append({"label": label, "value": t})
    return opts

# -----------------------------
# Initialize
# -----------------------------
df_all = load_data(DATA_PATH, nrows=DEV_NROWS)
geo = load_geojson(GEOJSON_PATH)

years = sorted(df_all["YEAR"].dropna().astype(int).unique().tolist())
crime_types_all = sorted(df_all["TYPE"].dropna().unique().tolist())
default_year = max(years) if years else None

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
    style={
        "fontFamily": "Arial",
        "backgroundColor": "#F7F7F7",
        "padding": "10px",
        "height": "100vh",
        "boxSizing": "border-box",
        "overflow": "hidden",
    },
    children=[
        dcc.Store(id="selected_neigh_store", data=None),
        html.H2("Vancouver Crime Patterns Dashboard", style={"textAlign": "center", "margin": "6px 0"}),
        html.Div(
            style={"display": "flex", "gap": "12px", "height": "calc(100vh - 60px)", "overflow": "hidden"},
            children=[
                # Left controls
                html.Div(
                    style={
                        "flex": "1",
                        "backgroundColor": "white",
                        "padding": "12px",
                        "borderRadius": "10px",
                        "height": "100%",
                        "overflowY": "auto",
                    },
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
                            options=make_type_options_plain(crime_types_all),
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
                    style={
                        "flex": "3",
                        "backgroundColor": "white",
                        "padding": "12px",
                        "borderRadius": "10px",
                        "height": "100%",
                        "minHeight": "0",
                        "overflowY": "auto",
                        "overflowX": "hidden",
                        "display": "flex",
                        "flexDirection": "column",
                        "gap": "10px",
                    },
                    children=[
                        html.Button(
                            "Back",
                            id="reset_map_btn",
                            n_clicks=0,
                            style={"display": "none", "marginBottom": "0px"}
                        ),

                        dcc.Graph(
                            id="map_graph",
                            figure=fig_neighbourhood_map(
                                filter_df(df_all, default_year, crime_types_all[:4], TOD_OPTIONS),
                                geojson=geo,
                                featureidkey=featureidkey,
                                name_mapping=name_mapping,
                                selected_neigh=None,
                            ),
                            style={"height": "420px", "width": "100%"},
                            config={"displayModeBar": True, "responsive": True},
                        ),

                        html.Div(
                            style={
                                "display": "flex",
                                "gap": "10px",
                                "flexWrap": "wrap",
                            },
                            children=[
                                html.Div(style={"flex": "1 1 320px"}, children=[dcc.Graph(id="monthly_graph", config={"displayModeBar": False})]),
                                html.Div(style={"flex": "1 1 320px"}, children=[dcc.Graph(id="hourly_graph", config={"displayModeBar": False})]),
                                html.Div(style={"flex": "1 1 320px"}, children=[dcc.Graph(id="type_graph", config={"displayModeBar": False})]),
                            ],
                        ),
                    ],
                ),

                # Right summary
                html.Div(
                    style={
                        "flex": "1",
                        "backgroundColor": "white",
                        "padding": "12px",
                        "borderRadius": "10px",
                        "height": "100%",
                        "overflowY": "auto",
                    },
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
                        ),

                        html.Hr(),
                        dcc.Graph(id="yearly_trend_graph", config={"displayModeBar": False}),
                    ],
                ),
            ],
        ),
    ],
)

# -----------------------------
# Reset filters callback
# -----------------------------
@app.callback(
    Output("year_dropdown", "value"),
    Output("type_checklist", "value"),
    Output("tod_checklist", "value"),
    Input("reset_btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset_filters(_n):
    return default_year, crime_types_all[:4], TOD_OPTIONS

# -----------------------------
# Store selected neighbourhood (persists while filters change)
# -----------------------------
@app.callback(
    Output("selected_neigh_store", "data"),
    Input("map_graph", "clickData"),
    Input("reset_map_btn", "n_clicks"),
    State("selected_neigh_store", "data"),
)

def update_selected_neigh(clickData, reset_clicks, current_selected):
    ctx = callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    if trigger == "reset_map_btn":
        return None

    if trigger == "map_graph":
        clicked = clicked_neighbourhood_from_polygon(clickData, name_mapping)
        if clicked:
            return clicked

    return current_selected

# -----------------------------
# Toggle type checklist dot display:
#   - not zoomed (no selected_neigh) -> plain
#   - zoomed (selected_neigh) -> dotted
# -----------------------------
@app.callback(
    Output("type_checklist", "options"),
    Input("selected_neigh_store", "data"),
)

def toggle_type_options(selected_neigh):
    if not selected_neigh:
        return make_type_options_plain(crime_types_all)
    return make_type_options_dotted(crime_types_all)


# -----------------------------
# Main update callback
# -----------------------------
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
    Output("reset_map_btn", "style"),
    Input("year_dropdown", "value"),
    Input("type_checklist", "value"),
    Input("tod_checklist", "value"),
    Input("selected_neigh_store", "data"),
)

def update_dashboard(year, types_selected, tod_selected, selected_neigh):
    df_f = filter_df(df_all, year, types_selected, tod_selected)
    df_focus = df_f if not selected_neigh else df_f[df_f["NEIGHBOURHOOD"] == selected_neigh]

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
        m_fig = px.bar(title="Monthly trend (# incidents)"); m_fig.update_layout(height=300)
        h_fig = px.bar(title="Hourly distribution (# incidents)"); h_fig.update_layout(height=300)
        t_fig = px.bar(title="Crime type comparison (top 8)"); t_fig.update_layout(height=300)

    summ = make_summary(df_f, selected_neigh)
    summ_year = f"Year: {year}" if year is not None else "Year: —"

    btn_style = {"display": "block"} if selected_neigh else {"display": "none"}

    return (
        map_fig, m_fig, h_fig, t_fig,
        summ_year,
        summ["selected_area"],
        f'{summ["total_incidents"]:,}',
        summ["peak_hour"],
        summ["top_type"],
        btn_style,
    )

# -----------------------------
# Yearly trend callback (2019–2023)
# -----------------------------
@app.callback(
    Output("yearly_trend_graph", "figure"),
    Input("type_checklist", "value"),
    Input("tod_checklist", "value"),
    Input("selected_neigh_store", "data"),
)

def update_yearly(types_selected, tod_selected, selected_neigh):
    return fig_yearly_trend(df_all, types_selected, tod_selected, selected_neigh)

# if __name__ == "__main__":
#     app.run(debug=True)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))