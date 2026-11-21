# ============================================================
# SOLAR TRACKER DATA EXPLORATION & VISUALIZATIONS DASHBOARD
# Built entirely with Python, Streamlit, Pandas and Plotly.
# Uses a CSV uploaded by the user, or built-in dashboard data.
# No Arduino, ESP32, or live hardware connection is required.
# ============================================================

from datetime import datetime, time, timedelta

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ---------------------- PAGE CONFIGURATION ----------------------
st.set_page_config(
    page_title="Solar Tracker | EDA Dashboard",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------- VISUAL THEME ----------------------
COLORS = [
    "#83CFC1",
    "#B8A7E8",
    "#F5AFA3",
    "#F4D27A",
    "#8FC5E8",
    "#E9A9CB",
    "#ADD18B",
    "#F2B98C"
]
BG = "#FFFEFC"
TEXT = "#38465A"
CONTINUOUS_COLORS = ["#BCE5DC", "#D1C4EF", "#F5B6AA"]

# Apply consistent Plotly styling to every chart.
def style_chart(fig, height=340):
    fig.update_layout(
        height=height,
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(family="Arial, sans-serif", color=TEXT, size=12),
        margin=dict(l=24, r=24, t=58, b=30),
        title_font=dict(size=16, color=TEXT),
        legend=dict(
            bgcolor="rgba(255,255,255,0.65)",
            borderwidth=0
        ),
        colorway=COLORS
    )
    fig.update_xaxes(showgrid=False, linecolor="#EAE5EC")
    fig.update_yaxes(gridcolor="#F0ECF1", zerolinecolor="#EAE5EC")
    return fig

def create_field_conditions_data(days=21):
    """Create a multi-week dataset with changing weather and operating conditions."""
    rng = np.random.default_rng(2026)
    periods_per_day = 96
    rows = days * periods_per_day
    timestamps = pd.date_range(
        end=pd.Timestamp.now().floor("15min"),
        periods=rows,
        freq="15min"
    )
    hours = timestamps.hour + timestamps.minute / 60
    day_number = np.arange(rows) // periods_per_day

    sunrise = 6.0 + 0.25 * np.sin(day_number / 7)
    sunset = 18.1 + 0.2 * np.cos(day_number / 9)
    daylight = np.clip(
        np.sin(np.pi * (hours - sunrise) / (sunset - sunrise)),
        0,
        None
    )

    daily_cloud = rng.choice([0.08, 0.22, 0.42, 0.62], size=days)
    cloud_factor = np.clip(
        1 - daily_cloud[day_number] + rng.normal(0, 0.07, rows),
        0.18,
        1
    )
    for day in range(days):
        if rng.random() < 0.55:
            start = day * periods_per_day + rng.integers(24, 64)
            duration = int(rng.integers(4, 17))
            cloud_factor[start:start + duration] *= rng.uniform(0.35, 0.72)

    irradiance = np.clip(
        daylight * (930 * cloud_factor + rng.normal(0, 18, rows)),
        0,
        1050
    )
    temperature = (
        20
        + 7 * np.sin(2 * np.pi * (hours - 8) / 24)
        + irradiance * 0.009
        + rng.normal(0, 1.4, rows)
    )
    voltage = np.clip(
        daylight * (18.2 - 0.035 * (temperature - 25))
        + rng.normal(0, 0.35, rows),
        0,
        21
    )
    current = np.clip(
        irradiance * 0.0031 + rng.normal(0, 0.055, rows),
        0,
        None
    )
    power = voltage * current * 0.92
    energy = np.cumsum(power * 0.25)

    sensor_base = irradiance * 0.52
    ldr_top = np.clip(320 + sensor_base + rng.normal(0, 32, rows), 0, 1023)
    ldr_bottom = np.clip(305 + sensor_base * 0.93 + rng.normal(0, 36, rows), 0, 1023)
    ldr_left = np.clip(315 + sensor_base * 0.97 + rng.normal(0, 38, rows), 0, 1023)
    ldr_right = np.clip(325 + sensor_base * 0.95 + rng.normal(0, 38, rows), 0, 1023)

    daylight_progress = np.clip((hours - sunrise) / (sunset - sunrise), 0, 1)
    azimuth = np.clip(
        daylight_progress * 180 + rng.normal(0, 2.2, rows),
        0,
        180
    )
    elevation = np.clip(daylight * 68 + rng.normal(0, 1.8, rows), 0, 90)
    target_azimuth = np.clip(azimuth + rng.normal(0, 2.8, rows), 0, 180)
    target_elevation = np.clip(elevation + rng.normal(0, 2.2, rows), 0, 90)
    status_choices = ["Normal", "Normal", "Normal", "Normal", "Warning"]

    return pd.DataFrame({
        "Timestamp": timestamps,
        "Temperature_C": temperature,
        "Irradiance_Wm2": irradiance,
        "Voltage_V": voltage,
        "Current_A": current,
        "Power_W": power,
        "Energy_Wh": energy,
        "LDR_Top": ldr_top,
        "LDR_Bottom": ldr_bottom,
        "LDR_Left": ldr_left,
        "LDR_Right": ldr_right,
        "Azimuth_Deg": azimuth,
        "Elevation_Deg": elevation,
        "Target_Azimuth_Deg": target_azimuth,
        "Target_Elevation_Deg": target_elevation,
        "Controller_Status": rng.choice(status_choices, rows),
        "Sensor_Status": rng.choice(status_choices, rows),
        "Motor_Status": rng.choice(status_choices, rows)
    })

# ---------------------- DATA LOADING ----------------------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(125deg, #E9DFFF 0%, #FCE1EC 48%, #DDF1FF 100%);
        background-attachment: fixed;
        color: #38465A;
    }
    [data-testid="stHeader"] { background: rgba(252, 245, 253, 0.78); }
    [data-testid="stAppDeployButton"],
    [data-testid="stMainMenu"],
    button[aria-label="Main menu"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F5EEFF 0%, #EEF8F6 100%);
    }
    section[data-testid="stSidebar"] * { color: #46556A; }
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] section {
        background: rgba(255, 255, 255, 0.76);
        border-color: #E5DDF2;
    }
    section[data-testid="stSidebar"] input {
        color: #38465A;
    }
    h1, h2, h3 { color: #38465A; letter-spacing: -0.025em; }
    h1 { font-weight: 750; }
    [data-testid="stCaptionContainer"] { color: #788397; }
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.88);
        border: 1px solid #EEE7EF;
        padding: 18px 20px;
        border-radius: 18px;
        box-shadow: 0 5px 18px rgba(84, 70, 104, 0.06);
    }
    div[data-testid="stHorizontalBlock"] > div:nth-child(4n+1) div[data-testid="stMetric"] { border-top: 3px solid #83CFC1; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(4n+2) div[data-testid="stMetric"] { border-top: 3px solid #B8A7E8; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(4n+3) div[data-testid="stMetric"] { border-top: 3px solid #F5AFA3; }
    div[data-testid="stHorizontalBlock"] > div:nth-child(4n+4) div[data-testid="stMetric"] { border-top: 3px solid #F4D27A; }
    div[data-testid="stMetricLabel"] { color: #788397; }
    div[data-testid="stMetricValue"] { color: #46556A; font-weight: 700; }
    div[data-testid="stDataFrame"], div[data-testid="stPlotlyChart"] {
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid #EEE7EF;
        border-radius: 18px;
        padding: 8px;
        box-shadow: 0 4px 16px rgba(84, 70, 104, 0.04);
    }
    div.stButton > button {
        background: #B5E2D8;
        color: #3D5A59;
        border: 0;
        border-radius: 12px;
        font-weight: 600;
    }
    div.stButton > button:hover { background: #9DD5C9; color: #304D4D; }
    hr { border-color: #EAE3ED; }
    .small-note { color: #8490A0; font-size: 0.88rem; }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("☀️ Solstice")
st.sidebar.caption("Solar intelligence dashboard")
st.sidebar.markdown("---")

uploaded_file = st.sidebar.file_uploader(
    "Upload your cleaned solar CSV",
    type=["csv"],
    help="Upload your preprocessed solar tracker dataset."
)

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        data_source = "Uploaded CSV"
    except Exception as error:
        st.error(f"Could not read the CSV file: {error}")
        st.stop()
else:
    df = create_field_conditions_data()
    data_source = "Site Conditions"

# Normalize column names only by trimming accidental spaces.
df.columns = [str(column).strip() for column in df.columns]

# Identify a timestamp column if one exists.
time_candidates = ["Timestamp", "timestamp", "Date", "Datetime", "date_time"]
time_col = next((c for c in time_candidates if c in df.columns), None)
if time_col:
    df[time_col] = pd.to_datetime(df[time_col], errors="coerce")

# Sidebar filters.
st.sidebar.markdown("### Filters")
invalid_time_range = False
if time_col and df[time_col].notna().any():
    valid_timestamps = df[time_col].dropna()
    first_timestamp = valid_timestamps.min()
    last_timestamp = valid_timestamps.max()

    start_columns = st.sidebar.columns(2)
    with start_columns[0]:
        start_date = st.date_input(
            "Start date",
            value=first_timestamp.date(),
            key="filter_start_date"
        )
    with start_columns[1]:
        end_date = st.date_input(
            "End date",
            value=last_timestamp.date(),
            key="filter_end_date"
        )

    time_columns = st.sidebar.columns(2)
    with time_columns[0]:
        start_time = st.time_input(
            "Start time",
            value=time.min,
            step=timedelta(minutes=1),
            key="filter_start_time"
        )
    with time_columns[1]:
        end_time = st.time_input(
            "End time",
            value=time(23, 59),
            step=timedelta(minutes=1),
            key="filter_end_time"
        )

    start_at = pd.Timestamp(datetime.combine(start_date, start_time))
    end_at = pd.Timestamp(datetime.combine(end_date, end_time))
    if isinstance(valid_timestamps.dtype, pd.DatetimeTZDtype):
        timezone = valid_timestamps.dt.tz
        start_at = start_at.tz_localize(timezone)
        end_at = end_at.tz_localize(timezone)

    if start_at <= end_at:
        df = df[df[time_col].between(start_at, end_at, inclusive="both")]
    else:
        invalid_time_range = True
        df = df.iloc[0:0]
else:
    st.sidebar.info("No usable timestamp column was found.")

numeric_columns = df.select_dtypes(include=np.number).columns.tolist()
if not numeric_columns:
    st.error("The uploaded dataset does not contain numeric columns to analyse.")
    st.stop()

# ---------------------- HEADER ----------------------
st.title("☀️ Solar Tracker Analytics")
st.markdown(
    "A clearer view of energy production, site conditions and tracker performance."
)
st.caption(f"{data_source}  ·  {len(df):,} records in the current view")

if df.empty:
    if invalid_time_range:
        st.warning("The start date and time must be earlier than or equal to the end date and time.")
    else:
        st.warning("No records match the selected date and time range. Adjust the filters.")
    st.stop()

# ---------------------- NAVIGATION ----------------------
pages = ["Overview", "Data Exploration", "Performance Analysis", "Sensor & Tracking", "Data Quality", "Reports"]
page = st.sidebar.radio("Navigate", pages)

# Helper function: return a column if it exists.
def has_col(name):
    return name in df.columns

def metric_value(column, operation="mean"):
    if not has_col(column):
        return None
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return None
    if operation == "sum":
        return values.sum()
    if operation == "max":
        return values.max()
    return values.mean()

# ---------------------- OVERVIEW PAGE ----------------------
if page == "Overview":
    st.subheader("Performance overview")

    metric_specs = [
        ("Average Power", "Power_W", "W", "mean"),
        ("Total Energy", "Energy_Wh", "Wh", "max"),
        ("Average Voltage", "Voltage_V", "V", "mean"),
        ("Average Current", "Current_A", "A", "mean")
    ]
    cols = st.columns(4)
    for container, (label, column, unit, operation) in zip(cols, metric_specs):
        value = metric_value(column, operation)
        if value is None:
            container.metric(label, "N/A")
        else:
            container.metric(label, f"{value:,.2f} {unit}")

    st.markdown("### Dataset snapshot")
    left, right = st.columns([1.25, 1])
    with left:
        st.dataframe(df.head(12), use_container_width=True, hide_index=True)
    with right:
        summary = df[numeric_columns].describe().T.round(2)
        st.dataframe(summary, use_container_width=True)

    st.markdown("### Solar output trend")
    if time_col and has_col("Power_W"):
        trend = px.line(
            df.sort_values(time_col), x=time_col, y="Power_W",
            title="Power output over time", color_discrete_sequence=[COLORS[0]]
        )
        st.plotly_chart(style_chart(trend), use_container_width=True)
    elif has_col("Power_W"):
        trend = px.line(df, y="Power_W", title="Power output by record")
        st.plotly_chart(style_chart(trend), use_container_width=True)
    else:
        st.info("Power_W column was not found. Upload a dataset containing this field.")

# ---------------------- DATA EXPLORATION PAGE ----------------------
elif page == "Data Exploration":
    st.subheader("Explore the dataset")
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", f"{len(df):,}")
    c2.metric("Columns", f"{df.shape[1]:,}")
    c3.metric("Numeric features", f"{len(numeric_columns):,}")

    st.markdown("### Dataset preview")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("### Descriptive statistics")
    st.dataframe(df[numeric_columns].describe().T.round(3), use_container_width=True)

    st.markdown("### Choose a variable to inspect")
    selected_column = st.selectbox("Numeric variable", numeric_columns)
    values = pd.to_numeric(df[selected_column], errors="coerce").dropna()

    a, b = st.columns(2)
    with a:
        hist = px.histogram(
            x=values, nbins=30, title=f"Distribution of {selected_column}",
            color_discrete_sequence=[COLORS[1]]
        )
        st.plotly_chart(style_chart(hist), use_container_width=True)
    with b:
        box = px.box(
            y=values, points="outliers", title=f"Box plot of {selected_column}",
            color_discrete_sequence=[COLORS[2]]
        )
        st.plotly_chart(style_chart(box), use_container_width=True)

# ---------------------- PERFORMANCE ANALYSIS PAGE ----------------------
elif page == "Performance Analysis":
    st.subheader("Solar performance analysis")

    if has_col("Irradiance_Wm2") and has_col("Power_W"):
        a, b = st.columns(2)
        with a:
            scatter = px.scatter(
                df, x="Irradiance_Wm2", y="Power_W",
                color="Temperature_C" if has_col("Temperature_C") else None,
                title="Irradiance vs power output",
                color_continuous_scale=CONTINUOUS_COLORS
            )
            st.plotly_chart(style_chart(scatter), use_container_width=True)
        with b:
            if time_col:
                area = px.area(
                    df.sort_values(time_col), x=time_col, y="Power_W",
                    title="Power output area chart",
                    color_discrete_sequence=[COLORS[2]]
                )
            else:
                area = px.area(
                    df, y="Power_W", title="Power output area chart",
                    color_discrete_sequence=[COLORS[2]]
                )
            st.plotly_chart(style_chart(area), use_container_width=True)

    if has_col("Temperature_C") and has_col("Power_W"):
        temp = px.scatter(
            df, x="Temperature_C", y="Power_W",
            title="Temperature vs power",
            color_discrete_sequence=[COLORS[4]],
            trendline="ols"
        )
        st.plotly_chart(style_chart(temp), use_container_width=True)

    electrical = [c for c in ["Voltage_V", "Current_A", "Power_W"] if has_col(c)]
    if electrical:
        st.markdown("### Electrical parameter comparison")
        melted = df[electrical].melt(var_name="Parameter", value_name="Value")
        bar = px.box(
            melted, x="Parameter", y="Value", color="Parameter",
            title="Spread of electrical measurements",
            color_discrete_sequence=COLORS
        )
        st.plotly_chart(style_chart(bar), use_container_width=True)

    if has_col("Power_W"):
        st.markdown("### Power distribution")
        pie_data = pd.cut(
            df["Power_W"], bins=4,
            labels=["Low", "Moderate", "High", "Very high"],
            duplicates="drop"
        ).value_counts().reset_index()
        pie_data.columns = ["Power range", "Count"]
        donut = px.pie(
            pie_data, names="Power range", values="Count", hole=0.55,
            title="Power output categories",
            color_discrete_sequence=COLORS
        )
        st.plotly_chart(style_chart(donut), use_container_width=True)

# ---------------------- SENSOR & TRACKING PAGE ----------------------
elif page == "Sensor & Tracking":
    st.subheader("LDR sensor and dual-axis tracking analysis")

    ldr_columns = [c for c in ["LDR_Top", "LDR_Bottom", "LDR_Left", "LDR_Right"] if has_col(c)]
    if ldr_columns:
        st.markdown("### LDR sensor readings")
        ldr_data = df[ldr_columns].mean().reset_index()
        ldr_data.columns = ["Sensor", "Average reading"]
        bar = px.bar(
            ldr_data, x="Sensor", y="Average reading", color="Sensor",
            title="Average reading from each LDR sensor",
            color_discrete_sequence=COLORS
        )
        st.plotly_chart(style_chart(bar), use_container_width=True)

        ldr_long = df[ldr_columns].reset_index().melt(
            id_vars="index", var_name="Sensor", value_name="Reading"
        )
        line = px.line(
            ldr_long, x="index", y="Reading", color="Sensor",
            title="LDR readings across records",
            color_discrete_sequence=COLORS
        )
        st.plotly_chart(style_chart(line), use_container_width=True)
    else:
        st.info("No standard LDR columns were found.")

    angle_columns = [c for c in ["Azimuth_Deg", "Elevation_Deg",
                                  "Target_Azimuth_Deg", "Target_Elevation_Deg"]
                     if has_col(c)]
    if angle_columns:
        st.markdown("### Tracking angles")
        angle_data = df[angle_columns].reset_index().melt(
            id_vars="index", var_name="Angle", value_name="Degrees"
        )
        angle_chart = px.line(
            angle_data, x="index", y="Degrees", color="Angle",
            title="Actual and target tracking angles",
            color_discrete_sequence=COLORS
        )
        st.plotly_chart(style_chart(angle_chart), use_container_width=True)

        if has_col("Azimuth_Deg") and has_col("Elevation_Deg"):
            polar = px.scatter(
                df, x="Azimuth_Deg", y="Elevation_Deg",
                title="Azimuth and elevation relationship",
                color="Power_W" if has_col("Power_W") else None,
                color_continuous_scale=CONTINUOUS_COLORS
            )
            st.plotly_chart(style_chart(polar), use_container_width=True)

# ---------------------- DATA QUALITY PAGE ----------------------
elif page == "Data Quality":
    st.subheader("Data quality assessment")

    missing = df.isna().sum().sort_values(ascending=False)
    duplicates = int(df.duplicated().sum())
    quality1, quality2, quality3 = st.columns(3)
    quality1.metric("Missing cells", f"{int(df.isna().sum().sum()):,}")
    quality2.metric("Duplicate rows", f"{duplicates:,}")
    quality3.metric("Complete rows", f"{int(df.notna().all(axis=1).sum()):,}")

    missing_df = missing.reset_index()
    missing_df.columns = ["Column", "Missing values"]
    missing_chart = px.bar(
        missing_df, x="Column", y="Missing values",
        title="Missing values by column",
        color="Missing values",
        color_continuous_scale=["#BCE5DC", "#F5B6AA"]
    )
    st.plotly_chart(style_chart(missing_chart), use_container_width=True)

    st.markdown("### Potential outliers (IQR method)")
    outlier_rows = []
    for column in numeric_columns:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if series.empty:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        count = int(((series < lower) | (series > upper)).sum())
        outlier_rows.append({
            "Column": column,
            "Outlier count": count,
            "Lower bound": round(lower, 3),
            "Upper bound": round(upper, 3)
        })
    outlier_df = pd.DataFrame(outlier_rows).sort_values("Outlier count", ascending=False)
    st.dataframe(outlier_df, use_container_width=True, hide_index=True)

    st.caption("IQR flags potential outliers for investigation; it does not automatically mean the values are incorrect.")

    status_columns = [c for c in ["Controller_Status", "Sensor_Status", "Motor_Status"] if has_col(c)]
    if status_columns:
        st.markdown("### Component status distribution")
        status_long = df[status_columns].melt(var_name="Component", value_name="Status")
        status_chart = px.histogram(
            status_long, x="Component", color="Status", barmode="group",
            title="Controller, sensor and motor status",
            color_discrete_sequence=COLORS
        )
        st.plotly_chart(style_chart(status_chart), use_container_width=True)

# ---------------------- REPORTS PAGE ----------------------
elif page == "Reports":
    st.subheader("Reports and data export")
    st.write("Filter the current dataset and download the resulting records.")

    if time_col and df[time_col].notna().any():
        report_dates = df[time_col].dropna()
        first_report_timestamp = report_dates.min()
        last_report_timestamp = report_dates.max()
        report_columns = st.columns(2)
        with report_columns[0]:
            report_start_date = st.date_input(
                "Report start date",
                value=first_report_timestamp.date(),
                key="report_start_date"
            )
        with report_columns[1]:
            report_end_date = st.date_input(
                "Report end date",
                value=last_report_timestamp.date(),
                key="report_end_date"
            )
        report_time_columns = st.columns(2)
        with report_time_columns[0]:
            report_start_time = st.time_input(
                "Report start time",
                value=time.min,
                step=timedelta(minutes=1),
                key="report_start_time"
            )
        with report_time_columns[1]:
            report_end_time = st.time_input(
                "Report end time",
                value=time(23, 59),
                step=timedelta(minutes=1),
                key="report_end_time"
            )
        report_start = pd.Timestamp(datetime.combine(report_start_date, report_start_time))
        report_end = pd.Timestamp(datetime.combine(report_end_date, report_end_time))
        if isinstance(report_dates.dtype, pd.DatetimeTZDtype):
            timezone = report_dates.dt.tz
            report_start = report_start.tz_localize(timezone)
            report_end = report_end.tz_localize(timezone)

        if report_start <= report_end:
            report_df = df[df[time_col].between(report_start, report_end, inclusive="both")].copy()
        else:
            report_df = df.iloc[0:0].copy()
            st.warning("The report start date and time must be earlier than or equal to the end.")
    else:
        report_df = df.copy()
        st.info("No timestamp column detected. Exporting all currently filtered records.")

    st.metric("Records in report", f"{len(report_df):,}")
    st.dataframe(report_df.head(20), use_container_width=True, hide_index=True)

    csv_bytes = report_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download filtered data as CSV",
        data=csv_bytes,
        file_name="solar_tracker_eda_report.csv",
        mime="text/csv",
        use_container_width=True
    )

    if not report_df.empty:
        numeric_report = report_df.select_dtypes(include=np.number)
        if not numeric_report.empty:
            summary_csv = numeric_report.describe().T.to_csv().encode("utf-8")
            st.download_button(
                "⬇️ Download statistical summary",
                data=summary_csv,
                file_name="solar_tracker_summary.csv",
                mime="text/csv"
            )

# ---------------------- FOOTER ----------------------
st.markdown("---")
st.markdown(
    '<p class="small-note">Solstice Solar Analytics · Built-in views are intended for exploration; '
    'upload a CSV to analyse your own measurements.</p>',
    unsafe_allow_html=True
)
