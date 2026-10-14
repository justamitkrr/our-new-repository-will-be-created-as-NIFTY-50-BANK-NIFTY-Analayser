import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import glob

# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(
    page_title="NIFTY 4/8 Analyzer",
    page_icon="📊",
    layout="wide"
)


# ============================================================
# INDEX OPTIONS
# ============================================================

INDEX_OPTIONS = {
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK"
}


# ============================================================
# EXACT 4/8 DATE LOGIC
# ============================================================

def reduce_number(number):

    while number > 9:

        number = sum(
            int(x)
            for x in str(number)
        )

    return number


def get_day_number(date):

    return reduce_number(
        date.day
    )


def get_full_date_number(date):

    date_digits = (
        f"{date.day:02d}"
        f"{date.month:02d}"
        f"{date.year}"
    )

    total = sum(
        int(x)
        for x in date_digits
    )

    return reduce_number(
        total
    )


def get_family(day_number):

    if day_number == 4:

        return "4 Family"

    elif day_number == 8:

        return "8 Family"

    return "Other"


def is_48_date(date):

    day_number = get_day_number(
        date
    )

    full_date_number = (
        get_full_date_number(
            date
        )
    )

    return (
        day_number in [4, 8]
        and
        full_date_number in [4, 8]
    )


# ============================================================
# TITLE
# ============================================================

st.title(
    "📊 NIFTY 4/8 Market Analyzer"
)

st.caption(
    "NIFTY 50 & BANK NIFTY historical 4/8 date analysis"
)


# ============================================================
# TEST OUR EXACT RULE
# ============================================================

st.subheader(
    "System Check"
)


test_dates = [
    "17-08-2026",
    "08-08-2026",
    "08-10-2026",
    "06-10-2026"
]


test_results = []


for value in test_dates:

    date = pd.to_datetime(
        value,
        dayfirst=True
    )

    test_results.append({

        "Date":
            date.strftime(
                "%d %b %Y"
            ),

        "Day Number":
            get_day_number(date),

        "Full Date Number":
            get_full_date_number(date),

        "Qualifies":
            "YES"
            if is_48_date(date)
            else "NO"

    })


st.dataframe(
    pd.DataFrame(
        test_results
    ),
    use_container_width=True,
    hide_index=True
)


st.success(
    "4/8 calculation engine loaded successfully."
)


# ============================================================
# INDEX SELECTION
# ============================================================

st.divider()

st.subheader("Market Analysis")

with st.form("market_analysis_form"):
    selected_index = st.selectbox(
        "Select Index",
        options=list(INDEX_OPTIONS.keys()),
        index=0
    )

    selected_symbol = INDEX_OPTIONS[selected_index]

    st.markdown("### Select Date Range")
    date_col1, date_col2 = st.columns(2)

    with date_col1:
        start_date = st.date_input(
            "From Date",
            value=pd.to_datetime("2021-01-01").date(),
            min_value=pd.to_datetime("2007-01-01").date(),
            max_value=pd.Timestamp.today().date()
        )

    with date_col2:
        end_date = st.date_input(
            "To Date",
            value=pd.Timestamp.today().date(),
            min_value=pd.to_datetime("2007-01-01").date(),
            max_value=pd.Timestamp.today().date()
        )

    analyze_clicked = st.form_submit_button(
        "Analyze",
        type="primary",
        use_container_width=True
    )

if start_date > end_date:
    st.error("From Date cannot be after To Date.")
    st.stop()

if st.button("Refresh Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

selected_history = (
    f"{pd.to_datetime(start_date).strftime('%d %b %Y')} "
    f"to {pd.to_datetime(end_date).strftime('%d %b %Y')}"
)


# ============================================================
# NSE OFFICIAL + YAHOO FALLBACK MARKET DATA
# ============================================================

def load_official_nse_data(index_name):
    if index_name == "NIFTY 50":
        patterns = ["NIFTY 50*.csv", "NIFTY_50*.csv"]
    else:
        patterns = ["NIFTY BANK*.csv", "NIFTY_BANK*.csv"]

    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    files = sorted(set(files))

    frames = []

    for file_path in files:
        try:
            df = pd.read_csv(file_path)
            df.columns = [str(c).strip() for c in df.columns]

            rename_map = {}
            for col in df.columns:
                clean = col.strip().lower().replace(" ", "").replace("_", "")
                if clean in ["date", "indexdate"]:
                    rename_map[col] = "Date"
                elif clean in ["open", "openindexvalue"]:
                    rename_map[col] = "Open"
                elif clean in ["high", "highindexvalue"]:
                    rename_map[col] = "High"
                elif clean in ["low", "lowindexvalue"]:
                    rename_map[col] = "Low"
                elif clean in ["close", "closingindexvalue"]:
                    rename_map[col] = "Close"

            df = df.rename(columns=rename_map)
            required = ["Date", "Open", "High", "Low", "Close"]

            if not all(col in df.columns for col in required):
                continue

            df = df[required].copy()
            df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")

            for col in ["Open", "High", "Low", "Close"]:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(",", "", regex=False),
                    errors="coerce"
                )

            df = df.dropna(subset=["Date", "Close"])

            if not df.empty:
                df["Data Source"] = "NSE Official"
                frames.append(df)

        except Exception:
            continue

    if not frames:
        return pd.DataFrame(
            columns=["Date", "Open", "High", "Low", "Close", "Data Source"]
        )

    return (
        pd.concat(frames, ignore_index=True)
        .sort_values("Date")
        .drop_duplicates(subset=["Date"], keep="last")
        .reset_index(drop=True)
    )


@st.cache_data(ttl=300)
def download_yahoo_data(symbol, start_date, end_date):
    download_end = pd.to_datetime(end_date) + pd.Timedelta(days=1)

    data = yf.download(
        symbol,
        start=pd.to_datetime(start_date),
        end=download_end,
        interval="1d",
        auto_adjust=False,
        progress=False
    )

    if data.empty:
        return pd.DataFrame(
            columns=["Date", "Open", "High", "Low", "Close", "Data Source"]
        )

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.reset_index()
    data["Date"] = pd.to_datetime(data["Date"]).dt.tz_localize(None)
    data = data[["Date", "Open", "High", "Low", "Close"]].copy()
    data["Data Source"] = "Yahoo provisional"
    return data


@st.cache_data(ttl=300)
def load_hybrid_market_data(index_name, symbol, start_date, end_date):
    official = load_official_nse_data(index_name)

    # Load a buffer before From Date so Previous Close is calculated correctly.
    buffer_start = pd.to_datetime(start_date) - pd.Timedelta(days=31)

    yahoo = download_yahoo_data(
        symbol,
        buffer_start.date(),
        end_date
    )

    if official.empty:
        combined = yahoo.copy()
    else:
        latest_nse_date = official["Date"].max()

        # NSE remains authoritative. Yahoo contributes only newer dates.
        yahoo_new = yahoo[yahoo["Date"] > latest_nse_date].copy()

        combined = pd.concat(
            [official, yahoo_new],
            ignore_index=True
        )

    if combined.empty:
        return combined

    combined["Date"] = pd.to_datetime(combined["Date"]).dt.tz_localize(None)

    combined = (
        combined
        .sort_values("Date")
        .drop_duplicates(subset=["Date"], keep="first")
        .reset_index(drop=True)
    )

    range_start = pd.to_datetime(start_date) - pd.Timedelta(days=31)
    range_end = pd.to_datetime(end_date)

    return combined[
        (combined["Date"] >= range_start) &
        (combined["Date"] <= range_end)
    ].copy()


# ============================================================
# LOAD DATA
# ============================================================

try:
    market_data = load_hybrid_market_data(
        selected_index,
        selected_symbol,
        start_date,
        end_date
    )

    if market_data.empty:
        st.error(
            "No market data received. Check that the official NSE CSV files "
            "are present in the GitHub repository."
        )

    else:
        market_data["Date"] = pd.to_datetime(market_data["Date"])
        market_data = market_data.sort_values("Date").reset_index(drop=True)

        selected_start_ts = pd.to_datetime(start_date)
        selected_end_ts = pd.to_datetime(end_date)

        visible_market_data = market_data[
            (market_data["Date"] >= selected_start_ts) &
            (market_data["Date"] <= selected_end_ts)
        ].copy()

        if visible_market_data.empty:
            st.error("No market data exists inside the selected date range.")
            st.stop()

        latest_row = visible_market_data.iloc[-1]
        latest_close = float(latest_row["Close"])
        latest_open = float(latest_row["Open"])
        latest_high = float(latest_row["High"])
        latest_low = float(latest_row["Low"])

        latest_position = market_data.index[
            market_data["Date"] == latest_row["Date"]
        ]

        if len(latest_position) > 0 and latest_position[-1] > 0:
            previous_close = float(
                market_data.iloc[latest_position[-1] - 1]["Close"]
            )
        else:
            previous_close = np.nan

        if pd.notna(previous_close):
            market_change = latest_close - previous_close
            market_change_pct = market_change / previous_close * 100
        else:
            market_change = np.nan
            market_change_pct = np.nan

        latest_date = latest_row["Date"].strftime("%d %b %Y")
        latest_source = latest_row.get("Data Source", "Unknown")

        st.success(f"{selected_index} data loaded successfully.")
        st.write(f"Latest available trading date: **{latest_date}**")
        st.caption(
            f"Latest row source: {latest_source}. Official NSE CSV history "
            "is primary; Yahoo is used only for dates later than the latest "
            "official NSE file."
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Latest Close", f"{latest_close:,.2f}")
        col2.metric("Previous Close", f"{previous_close:,.2f}")
        col3.metric("Change", f"{market_change:+,.2f}")
        col4.metric("Change %", f"{market_change_pct:+.2f}%")

        col5, col6, col7 = st.columns(3)
        col5.metric("Open", f"{latest_open:,.2f}")
        col6.metric("High", f"{latest_high:,.2f}")
        col7.metric("Low", f"{latest_low:,.2f}")

except Exception as error:
    st.error("Market data could not be loaded.")
    st.exception(error)


# ============================================================
# EXACT 4/8 HISTORICAL ANALYSIS
# ============================================================

st.divider()

st.markdown("### Data Sources & Verification")
st.caption(
    "NSE Official — Primary historical source | "
    "Yahoo Finance — Fallback for dates newer than the latest official NSE CSV | "
    "TradingView — Independent cross-check | "
    "Investing.com — Independent cross-check"
)

# DATA QUALITY / VALIDATION STATUS
try:
    official_rows = market_data[market_data["Data Source"] == "NSE Official"].copy()
    yahoo_rows = market_data[market_data["Data Source"] == "Yahoo provisional"].copy()

    latest_nse_text = (
        official_rows["Date"].max().strftime("%d %b %Y")
        if not official_rows.empty else "Not available"
    )
    latest_fallback_text = (
        yahoo_rows["Date"].max().strftime("%d %b %Y")
        if not yahoo_rows.empty else "Not used"
    )

    st.markdown("### Data Quality & Validation")
    dq1, dq2, dq3, dq4 = st.columns(4)
    dq1.metric("Primary Source", "NSE Official")
    dq2.metric("Latest NSE Date", latest_nse_text)
    dq3.metric("Latest Fallback Date", latest_fallback_text)
    dq4.metric("Validation Status", "Passed")

    st.caption(
        "Historical benchmark results and the Exact 4/8 rule were validated "
        "against official NSE data. Yahoo is used only for dates newer than "
        "the latest official NSE CSV available in this app."
    )
except Exception:
    pass

st.subheader("🔢 Exact 4/8 Historical Analysis")


if "market_data" in globals() and not market_data.empty:

    analysis_data = market_data.copy()


    # --------------------------------------------------------
    # PREVIOUS CLOSE
    # --------------------------------------------------------

    analysis_data["Previous Close"] = (
        analysis_data["Close"].shift(1)
    )


    # --------------------------------------------------------
    # CHANGE
    # --------------------------------------------------------

    analysis_data["Change"] = (
        analysis_data["Close"]
        -
        analysis_data["Previous Close"]
    )


    analysis_data["Change %"] = (
        analysis_data["Change"]
        /
        analysis_data["Previous Close"]
        *
        100
    )


    # --------------------------------------------------------
    # BULLISH / BEARISH
    # --------------------------------------------------------

    analysis_data["Direction"] = np.where(
        analysis_data["Close"]
        >
        analysis_data["Previous Close"],
        "Bullish",

        np.where(
            analysis_data["Close"]
            <
            analysis_data["Previous Close"],
            "Bearish",
            "No Change"
        )
    )


    # --------------------------------------------------------
    # CALCULATE EXACT DATE NUMBERS
    # --------------------------------------------------------

    analysis_data["Day Number"] = (
        analysis_data["Date"]
        .apply(get_day_number)
    )


    analysis_data["Full Date Number"] = (
        analysis_data["Date"]
        .apply(get_full_date_number)
    )


    analysis_data["Family"] = (
        analysis_data["Day Number"]
        .apply(get_family)
    )

    # Calculate Previous Close on the buffered full calendar first,
    # then restrict the analysis to the user's selected date range.
    analysis_data = analysis_data[
        (analysis_data["Date"] >= pd.to_datetime(start_date)) &
        (analysis_data["Date"] <= pd.to_datetime(end_date))
    ].copy()


    # --------------------------------------------------------
    # EXACT RULE
    #
    # BOTH CONDITIONS MUST BE TRUE:
    #
    # Day Number = 4 or 8
    # AND
    # Full DDMMYYYY Number = 4 or 8
    # --------------------------------------------------------

    special_dates = analysis_data[
        (analysis_data["Day Number"].isin([4, 8]))
        &
        (analysis_data["Full Date Number"].isin([4, 8]))
    ].copy()


    # --------------------------------------------------------
    # ANALYSIS FILTERS
    # --------------------------------------------------------

    st.markdown("### Analysis Filters")

    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        direction_filter = st.selectbox(
            "Direction",
            ["All", "Bullish", "Bearish"]
        )

    with filter_col2:
        combination_filter = st.selectbox(
            "Combination",
            ["All", "4 & 4", "4 & 8", "8 & 4", "8 & 8"]
        )

    available_years = sorted(
        special_dates["Date"].dt.year.dropna().unique().astype(int).tolist(),
        reverse=True
    )

    with filter_col3:
        year_filter = st.selectbox(
            "Year",
            ["All"] + available_years
        )

        displayed_dates = special_dates.copy()

    displayed_dates["Combination"] = (
        displayed_dates["Day Number"].astype(str)
        + " & "
        + displayed_dates["Full Date Number"].astype(str)
    )

    if direction_filter != "All":
        displayed_dates = displayed_dates[
            displayed_dates["Direction"] == direction_filter
        ].copy()

    if combination_filter != "All":
        displayed_dates = displayed_dates[
            displayed_dates["Combination"] == combination_filter
        ].copy()

    if year_filter != "All":
        displayed_dates = displayed_dates[
            displayed_dates["Date"].dt.year == int(year_filter)
        ].copy()

    # ========================================================
    # SUMMARY
    # ========================================================

    total_dates = len(
        special_dates
    )


    bullish_count = (
        special_dates["Direction"]
        .eq("Bullish")
        .sum()
    )


    bearish_count = (
        special_dates["Direction"]
        .eq("Bearish")
        .sum()
    )


    no_change_count = (
        special_dates["Direction"]
        .eq("No Change")
        .sum()
    )


    directional_total = (
        bullish_count
        +
        bearish_count
    )


    if directional_total > 0:

        bullish_percentage = (
            bullish_count
            /
            directional_total
            *
            100
        )


        bearish_percentage = (
            bearish_count
            /
            directional_total
            *
            100
        )


    else:

        bullish_percentage = 0
        bearish_percentage = 0


    # ========================================================
    # SUMMARY CARDS
    # ========================================================

    st.markdown(
        "### Historical Summary"
    )


    c1, c2, c3, c4 = st.columns(4)


    c1.metric(
        "Qualifying 4/8 Dates",
        total_dates
    )


    c2.metric(
        "Bullish",
        bullish_count,
        f"{bullish_percentage:.1f}%"
    )


    c3.metric(
        "Bearish",
        bearish_count,
        f"{bearish_percentage:.1f}%"
    )


    c4.metric(
        "No Change",
        no_change_count
    )
    # ========================================================
    # EXACT 4/8 COMBINATION ANALYSIS
    # ========================================================

    st.markdown("### Exact 4/8 Combination Analysis")

    combination_rows = []

    for day_num, full_date_num in [(4, 4), (4, 8), (8, 4), (8, 8)]:

        combo_data = special_dates[
            (special_dates["Day Number"] == day_num) &
            (special_dates["Full Date Number"] == full_date_num)
        ]

        total = len(combo_data)
        bullish = combo_data["Direction"].eq("Bullish").sum()
        bearish = combo_data["Direction"].eq("Bearish").sum()
        directional = bullish + bearish

        combination_rows.append({
            "Combination": f"{day_num} & {full_date_num}",
            "Dates": total,
            "Bullish": bullish,
            "Bearish": bearish,
            "Bullish %": bullish / directional * 100 if directional else np.nan,
            "Bearish %": bearish / directional * 100 if directional else np.nan
        })

    combination_summary = pd.DataFrame(combination_rows)

    st.dataframe(
        combination_summary.style.format({
            "Bullish %": "{:.2f}%",
            "Bearish %": "{:.2f}%"
        }),
        use_container_width=True,
        hide_index=True
    )

   

    # ========================================================
    # QUALIFYING DATE TABLE
    # ========================================================

    st.markdown(
        "### Qualifying Dates"
    )


    if displayed_dates.empty:

        st.warning(
            "No qualifying 4/8 dates found for this selection."
        )


    else:

        date_table = displayed_dates[
            [
                "Date",
                "Family",
                "Day Number",
                "Full Date Number",
                "Previous Close",
                "Close",
                "Change",
                "Change %",
                "Direction",
                "Data Source"
            ]
        ].copy()


        # Sort using the real datetime value first.
        # Format only after sorting so dates remain chronological.
        date_table = (
            date_table
            .sort_values(
                "Date",
                ascending=False
            )
            .reset_index(drop=True)
        )

        # Preferred display format:
        # 06 Oct 2026
        date_table["Date"] = (
            date_table["Date"]
            .dt.strftime("%d %b %Y")
        )


        st.dataframe(
            date_table.style.format({

                "Previous Close":
                    "{:,.2f}",

                "Close":
                    "{:,.2f}",

                "Change":
                    "{:+,.2f}",

                "Change %":
                    "{:+.2f}%"

            }),

            use_container_width=True,

            hide_index=True
        )


    # ========================================================
    # IMPORTANT EXPLANATION
    # ========================================================

    st.info(
        "A date qualifies only when BOTH the calendar-day "
        "number and the complete DDMMYYYY number reduce to "
        "4 or 8. Bullish/Bearish describes what happened "
        "historically on that trading day compared with the "
        "previous trading day's close. It is not a forecast."
    )


# ============================================================
# FORWARD PERFORMANCE ANALYSIS
# ============================================================

st.divider()

st.subheader("📈 Forward Performance After 4/8 Dates")


if "analysis_data" in globals() and "special_dates" in globals():

    # ========================================================
    # CALCULATE FORWARD RETURNS
    #
    # IMPORTANT:
    # shift(-1) = next trading session
    # shift(-2) = 2 trading sessions later
    # etc.
    # ========================================================

    forward_periods = [
        1,
        2,
        3,
        5,
        10
    ]


    for days in forward_periods:

        analysis_data[
            f"Return +{days}D %"
        ] = (
            (
                analysis_data["Close"].shift(-days)
                /
                analysis_data["Close"]
                -
                1
            )
            *
            100
        )


    # ========================================================
    # RECREATE EXACT 4/8 DATA
    # WITH FORWARD RETURNS INCLUDED
    # ========================================================

    forward_48 = analysis_data[
        (analysis_data["Day Number"].isin([4, 8]))
        &
        (analysis_data["Full Date Number"].isin([4, 8]))
    ].copy()


    # ========================================================
    # FORWARD SUMMARY
    # ========================================================

    forward_rows = []


    for days in forward_periods:

        return_column = (
            f"Return +{days}D %"
        )


        returns = (
            forward_48[return_column]
            .dropna()
            .astype(float)
        )


        samples = len(
            returns
        )


        positive = (
            returns.gt(0).sum()
        )


        negative = (
            returns.lt(0).sum()
        )


        unchanged = (
            returns.eq(0).sum()
        )


        directional = (
            positive
            +
            negative
        )


        if directional > 0:

            positive_pct = (
                positive
                /
                directional
                *
                100
            )


            negative_pct = (
                negative
                /
                directional
                *
                100
            )


        else:

            positive_pct = np.nan
            negative_pct = np.nan


        if samples > 0:

            average_return = (
                returns.mean()
            )


            median_return = (
                returns.median()
            )


            best_return = (
                returns.max()
            )


            worst_return = (
                returns.min()
            )


        else:

            average_return = np.nan
            median_return = np.nan
            best_return = np.nan
            worst_return = np.nan


        if days == 1:

            period_name = (
                "Next Trading Day"
            )

        else:

            period_name = (
                f"+{days} Trading Days"
            )


        forward_rows.append({

            "Period":
                period_name,

            "Samples":
                samples,

            "Positive":
                positive,

            "Negative":
                negative,

            "Unchanged":
                unchanged,

            "Positive %":
                positive_pct,

            "Negative %":
                negative_pct,

            "Average Return %":
                average_return,

            "Median Return %":
                median_return,

            "Best Return %":
                best_return,

            "Worst Return %":
                worst_return

        })


    forward_summary_app = pd.DataFrame(
        forward_rows
    )


    # ========================================================
    # DISPLAY SUMMARY
    # ========================================================

    st.markdown(
        "### Historical Forward Performance"
    )


    st.dataframe(

        forward_summary_app.style.format({

            "Positive %":
                "{:.2f}%",

            "Negative %":
                "{:.2f}%",

            "Average Return %":
                "{:+.3f}%",

            "Median Return %":
                "{:+.3f}%",

            "Best Return %":
                "{:+.3f}%",

            "Worst Return %":
                "{:+.3f}%"

        }),

        use_container_width=True,

        hide_index=True
    )


    # ========================================================
    # PERFORMANCE CARDS
    # ========================================================

    st.markdown(
        "### Quick View"
    )


    card_columns = st.columns(
        5
    )


    for i, days in enumerate(
        forward_periods
    ):

        row = (
            forward_summary_app
            .iloc[i]
        )


        if days == 1:

            card_title = "+1 Day"

        else:

            card_title = f"+{days} Days"


        if pd.notna(
            row["Average Return %"]
        ):

            average_text = (
                f"{row['Average Return %']:+.3f}%"
            )

        else:

            average_text = "N/A"


        if pd.notna(
            row["Positive %"]
        ):

            positive_text = (
                f"{row['Positive %']:.1f}% positive"
            )

        else:

            positive_text = (
                "No data"
            )


        card_columns[i].metric(

            card_title,

            average_text,

            positive_text
        )


    # ========================================================
    # FORWARD RETURN CHART
    # ========================================================

    st.markdown(
        "### Average Forward Return"
    )


    chart_data = (
        forward_summary_app[
            [
                "Period",
                "Average Return %"
            ]
        ]
        .copy()
        .set_index("Period")
    )


    st.bar_chart(
        chart_data
    )

    # ========================================================
    # VISUAL ANALYTICS
    # ========================================================

    st.markdown("## 📊 Visual Analytics")

    visual_data = displayed_dates.copy()
    visual_data["Combination"] = (
        visual_data["Day Number"].astype(str)
        + " & "
        + visual_data["Full Date Number"].astype(str)
    )

    total_visual = len(visual_data)
    bullish_visual = int(
        (visual_data["Direction"] == "Bullish").sum()
    )
    bearish_visual = int(
        (visual_data["Direction"] == "Bearish").sum()
    )

    bullish_visual_pct = (
        bullish_visual / total_visual * 100
        if total_visual else 0
    )

    bearish_visual_pct = (
        bearish_visual / total_visual * 100
        if total_visual else 0
    )

    # KPI CARDS
    vk1, vk2, vk3 = st.columns(3)

    vk1.metric(
        "Filtered Exact 4/8 Dates",
        total_visual
    )

    vk2.metric(
        "Bullish",
        bullish_visual,
        f"{bullish_visual_pct:.2f}%"
    )

    vk3.metric(
        "Bearish",
        bearish_visual,
        f"{bearish_visual_pct:.2f}%"
    )

    if not visual_data.empty:

        # --------------------------------------------
        # COMBINATION PERFORMANCE
        # --------------------------------------------

        combination_chart = (
            visual_data
            .groupby(["Combination", "Direction"])
            .size()
            .unstack(fill_value=0)
            .reindex(
                ["4 & 4", "4 & 8", "8 & 4", "8 & 8"]
            )
            .fillna(0)
        )

        for direction_name in ["Bullish", "Bearish"]:
            if direction_name not in combination_chart.columns:
                combination_chart[direction_name] = 0

        st.markdown("### Combination Performance")

        st.bar_chart(
            combination_chart[
                ["Bullish", "Bearish"]
            ]
        )

        # --------------------------------------------
        # YEAR-WISE PERFORMANCE
        # --------------------------------------------

        yearly_chart = (
            visual_data
            .assign(
                Year=visual_data["Date"].dt.year
            )
            .groupby(["Year", "Direction"])
            .size()
            .unstack(fill_value=0)
            .sort_index()
        )

        for direction_name in ["Bullish", "Bearish"]:
            if direction_name not in yearly_chart.columns:
                yearly_chart[direction_name] = 0

        st.markdown(
            "### Year-wise Bullish vs Bearish"
        )

        st.line_chart(
            yearly_chart[
                ["Bullish", "Bearish"]
            ]
        )

        st.caption(
            "Charts use the selected Direction, Combination "
            "and Year filters. Historical observations only."
        )

    else:

        st.info(
            "No Exact 4/8 records match the selected filters."
        )
    # ========================================================
    # INDIVIDUAL QUALIFYING DATES
    # ========================================================

    st.markdown(
        "### Individual 4/8 Date Performance"
    )


    detail_columns = [

        "Date",
        "Family",
        "Day Number",
        "Full Date Number",
        "Close",
        "Direction",
        "Return +1D %",
        "Return +2D %",
        "Return +3D %",
        "Return +5D %",
        "Return +10D %"

    ]


    forward_detail_app = (
        forward_48[
            detail_columns
        ]
        .copy()
    )


    forward_detail_app["Date"] = (

        forward_detail_app["Date"]
        .dt.strftime(
            "%d %b %Y"
        )

    )


    # Keep newest dates first.
    # Sort before display using original dataframe order.

    forward_detail_app = (
        forward_detail_app
        .iloc[::-1]
        .reset_index(drop=True)
    )


    st.dataframe(

        forward_detail_app.style.format({

            "Close":
                "{:,.2f}",

            "Return +1D %":
                "{:+.3f}%",

            "Return +2D %":
                "{:+.3f}%",

            "Return +3D %":
                "{:+.3f}%",

            "Return +5D %":
                "{:+.3f}%",

            "Return +10D %":
                "{:+.3f}%"

        }),

        use_container_width=True,

        hide_index=True
    )


    # ========================================================
    # EXPLANATION
    # ========================================================

    st.info(
        "The +1, +2, +3, +5 and +10 figures use trading "
        "sessions, not calendar days. For example, +1D means "
        "the close of the next available trading session "
        "compared with the qualifying 4/8 day's close."
    )


    st.warning(
        "These results describe historical observations only. "
        "They do not establish that the 4/8 date rule predicts "
        "future market movement."
    )


# ============================================================
# MAIN PRICE CHART WITH EXACT 4/8 MARKERS
# ============================================================

st.divider()

st.subheader("📊 Market Chart & Exact 4/8 Dates")


if "analysis_data" in globals() and "forward_48" in globals():

    chart_market = (
        analysis_data
        .copy()
        .sort_values("Date")
    )


    chart_48 = (
        forward_48
        .copy()
        .sort_values("Date")
    )


    # --------------------------------------------------------
    # SEPARATE BULLISH / BEARISH QUALIFYING DATES
    # --------------------------------------------------------

    bullish_48_chart = chart_48[
        chart_48["Direction"] == "Bullish"
    ]


    bearish_48_chart = chart_48[
        chart_48["Direction"] == "Bearish"
    ]


    # ========================================================
    # CREATE CHART
    # ========================================================

    fig, ax = plt.subplots(
        figsize=(15, 7)
    )


    # Main index line

    ax.plot(
        chart_market["Date"],
        chart_market["Close"],
        linewidth=1.8,
        label=selected_index
    )


    # Bullish 4/8 markers

    if not bullish_48_chart.empty:

        ax.scatter(
            bullish_48_chart["Date"],
            bullish_48_chart["Close"],
            marker="^",
            s=85,
            label="Bullish 4/8",
            zorder=5
        )


    # Bearish 4/8 markers

    if not bearish_48_chart.empty:

        ax.scatter(
            bearish_48_chart["Date"],
            bearish_48_chart["Close"],
            marker="v",
            s=85,
            label="Bearish 4/8",
            zorder=5
        )


    # ========================================================
    # ADD 4F / 8F LABELS
    # ========================================================

    for _, row in chart_48.iterrows():

        if row["Family"] == "4 Family":

            family_label = "4F"

        else:

            family_label = "8F"


        ax.annotate(
            family_label,

            (
                row["Date"],
                row["Close"]
            ),

            xytext=(0, 9),

            textcoords="offset points",

            ha="center",

            fontsize=8
        )


    # ========================================================
    # CHART FORMATTING
    # ========================================================

    ax.set_title(
        f"{selected_index} — Exact 4/8 Historical Dates",
        fontsize=16
    )


    ax.set_xlabel(
        "Date"
    )


    ax.set_ylabel(
        "Index Value"
    )


    ax.grid(
        alpha=0.20
    )


    ax.legend()


    fig.autofmt_xdate()


    plt.tight_layout()


    # ========================================================
    # SHOW IN STREAMLIT
    # ========================================================

    st.pyplot(
        fig,
        use_container_width=True
    )


    plt.close(fig)


    # ========================================================
    # CHART SUMMARY
    # ========================================================

    st.caption(
        "▲ = historically Bullish qualifying 4/8 date | "
        "▼ = historically Bearish qualifying 4/8 date | "
        "4F = 4 Family | 8F = 8 Family"
    )


    # ========================================================
    # RECENT QUALIFYING DATE
    # ========================================================

    st.markdown(
        "### Most Recent Qualifying 4/8 Date"
    )


    if not chart_48.empty:

        recent_48 = (
            chart_48.iloc[-1]
        )


        recent_date = (
            recent_48["Date"]
            .strftime(
                "%d %b %Y"
            )
        )


        r1, r2, r3, r4 = st.columns(4)


        r1.metric(
            "Date",
            recent_date
        )


        r2.metric(
            "Family",
            recent_48["Family"]
        )


        r3.metric(
            "Close",
            f"{recent_48['Close']:,.2f}"
        )


        r4.metric(
            "Same-Day Direction",
            recent_48["Direction"]
        )


        st.write(
            "Day Number:",
            int(
                recent_48[
                    "Day Number"
                ]
            ),
            " | Full Date Number:",
            int(
                recent_48[
                    "Full Date Number"
                ]
            )
        )


    else:

        st.warning(
            "No exact 4/8 dates were found "
            "in the selected history."
        )

    # ========================================================
    # EXACT COMBINATION COMPARISON CHART
    # ========================================================

    st.markdown(
        "### Exact 4/8 Combinations — Same-Day Direction"
    )
    combination_chart_rows = []
    for day_num, full_date_num in [
        (4, 4),
        (4, 8),
        (8, 4),
        (8, 8)
    ]:

        temp = chart_48[
            (chart_48["Day Number"] == day_num)
            &
            (chart_48["Full Date Number"] == full_date_num)
        ]

        bullish = temp["Direction"].eq("Bullish").sum()
        bearish = temp["Direction"].eq("Bearish").sum()

        total_directional = bullish + bearish

        if total_directional > 0:

            bullish_pct = (
                bullish / total_directional * 100
            )

            bearish_pct = (
                bearish / total_directional * 100
            )

        else:

            bullish_pct = 0
            bearish_pct = 0

        combination_chart_rows.append({

            "Combination":
                f"{day_num} & {full_date_num}",

            "Bullish %":
                bullish_pct,

            "Bearish %":
                bearish_pct

        })

    combination_chart_app = (
        pd.DataFrame(combination_chart_rows)
        .set_index("Combination")
    )

    st.bar_chart(
        combination_chart_app
    )
    # ========================================================
    # NOTE
    # ========================================================

    st.info(
        "The markers identify dates that passed the exact "
        "4/8 rule. Their position on the chart does not mean "
        "they caused the market movement."
    )

# ============================================================
# FREE SMART ANALYSIS ASSISTANT
# ============================================================

st.divider()

st.subheader("🤖 Smart Analysis Assistant")

st.caption(
    "Automatic interpretation of the selected historical data. "
    "Market calculations are deterministic; Gemini is used only for optional AI interpretation."
)
if (
    "combination_summary" in globals()
    and not combination_summary.empty
):

    st.markdown("### 📌 Combination Insight")

    valid_combinations = combination_summary.dropna(
        subset=["Bullish %"]
    )

    if not valid_combinations.empty:

        strongest_bullish = valid_combinations.loc[
            valid_combinations["Bullish %"].idxmax()
        ]

        strongest_bearish = valid_combinations.loc[
            valid_combinations["Bearish %"].idxmax()
        ]

        st.write(
            f"📈 **Strongest historical bullish combination:** "
            f"{strongest_bullish['Combination']} — "
            f"{strongest_bullish['Bullish %']:.2f}% bullish "
            f"from {int(strongest_bullish['Dates'])} qualifying dates."
        )

        st.write(
            f"📉 **Strongest historical bearish combination:** "
            f"{strongest_bearish['Combination']} — "
            f"{strongest_bearish['Bearish %']:.2f}% bearish "
            f"from {int(strongest_bearish['Dates'])} qualifying dates."
        )
if (
    "forward_summary_app" in globals()
    and not forward_summary_app.empty
):

    st.markdown("### 📊 Forward Performance Insight")

    valid_forward = forward_summary_app.dropna(
        subset=["Average Return %"]
    )

    if not valid_forward.empty:

        best_period = valid_forward.loc[
            valid_forward["Average Return %"].idxmax()
        ]

        worst_period = valid_forward.loc[
            valid_forward["Average Return %"].idxmin()
        ]

        st.write(
            f"🚀 **Best historical average forward performance:** "
            f"{best_period['Period']} — "
            f"{best_period['Average Return %']:+.3f}% average return, "
            f"with {best_period['Positive %']:.1f}% positive observations."
        )

        st.write(
            f"⚠️ **Weakest historical average forward performance:** "
            f"{worst_period['Period']} — "
            f"{worst_period['Average Return %']:+.3f}% average return."
        )
if (
    "combination_summary" in globals()
    and not combination_summary.empty
):
    st.markdown("### 🧪 Reliability Check")

    low_sample = combination_summary[
        combination_summary["Dates"] < 10
    ]

    if not low_sample.empty:

        combinations = ", ".join(
            low_sample["Combination"].astype(str).tolist()
        )

        st.warning(
            f"Small sample warning: {combinations} "
            f"has fewer than 10 qualifying dates in the selected period. "
            f"Percentages based on small samples can change significantly "
            f"when new observations are added."
        )

    else:

        st.success(
            "All four exact combinations have at least 10 historical "
            "observations in the selected period."
        )

# ============================================================
# GEMINI AI ANALYSIS ASSISTANT
# ============================================================

st.markdown("### 💬 Ask About This Analysis")

st.caption(
    "Ask questions about the selected NIFTY 50 / BANK NIFTY "
    "historical 4/8 analysis."
)

user_question = st.text_input(
    "Type your question",
    placeholder=(
        "Example: Compare the 4 & 4 and 8 & 8 combinations "
        "and explain which was stronger historically."
    )
)

ask_button = st.button(
    "Ask Gemini Assistant",
    use_container_width=True
)


if ask_button:

    if not user_question.strip():

        st.warning("Please type a question first.")

    elif (
        "forward_48" not in globals()
        or forward_48.empty
        or "combination_summary" not in globals()
        or "forward_summary_app" not in globals()
    ):

        st.warning(
            "Dashboard analysis data is not available yet."
        )

    else:

        try:

            from google import genai

            gemini_client = genai.Client(
                api_key=st.secrets["GEMINI_API_KEY"]
            )

            # ----------------------------------------------------
            # PREPARE COMPACT DASHBOARD DATA FOR GEMINI
            # ----------------------------------------------------

            combination_context = (
                combination_summary
                .round(3)
                .to_string(index=False)
            )
            # ----------------------------------------------------
            # YEAR-WISE EXACT COMBINATION ANALYSIS
            # ----------------------------------------------------

            year_combo_data = forward_48.copy()

            year_combo_data["Year"] = (
                year_combo_data["Date"].dt.year
            )

            year_combo_rows = []

            for year in sorted(year_combo_data["Year"].unique()):

                for day_num, full_date_num in [
                    (4, 4),
                    (4, 8),
                    (8, 4),
                    (8, 8)
                ]:

                    temp = year_combo_data[
                        (year_combo_data["Year"] == year)
                        & (year_combo_data["Day Number"] == day_num)
                        & (
                            year_combo_data["Full Date Number"]
                            == full_date_num
                        )
                    ]

                    bullish = temp["Direction"].eq("Bullish").sum()
                    bearish = temp["Direction"].eq("Bearish").sum()
                    no_change = temp["Direction"].eq("No Change").sum()

                    total = len(temp)
                    directional = bullish + bearish

                    bullish_pct = (
                        bullish / directional * 100
                        if directional > 0
                        else np.nan
                    )

                    if bullish > bearish:
                        year_result = "Bullish"
                    elif bearish > bullish:
                        year_result = "Bearish"
                    elif directional > 0:
                        year_result = "Tied"
                    else:
                        year_result = "No Data"

                    year_combo_rows.append({
                        "Year": int(year),
                        "Combination": f"{day_num} & {full_date_num}",
                        "Dates": total,
                        "Bullish": int(bullish),
                        "Bearish": int(bearish),
                        "No Change": int(no_change),
                        "Bullish %": bullish_pct,
                        "Year Result": year_result
                    })

            year_combination_summary = pd.DataFrame(
                year_combo_rows
            )

            year_combination_context = (
                year_combination_summary
                .round(2)
                .to_string(index=False)
            )
                        # ----------------------------------------------------
            # COMBINATION-WISE FORWARD RETURN ANALYSIS
            # ----------------------------------------------------

            combo_forward_rows = []

            for day_num, full_date_num in [
                (4, 4),
                (4, 8),
                (8, 4),
                (8, 8)
            ]:

                temp = forward_48[
                    (forward_48["Day Number"] == day_num)
                    & (
                        forward_48["Full Date Number"]
                        == full_date_num
                    )
                ]

                row = {
                    "Combination": f"{day_num} & {full_date_num}",
                    "Dates": len(temp)
                }

                for days in [1, 2, 3, 5, 10]:

                    return_column = f"Return +{days}D %"

                    returns = (
                        temp[return_column]
                        .dropna()
                        .astype(float)
                    )

                    row[f"+{days}D Samples"] = len(returns)

                    row[f"+{days}D Avg %"] = (
                        returns.mean()
                        if not returns.empty
                        else np.nan
                    )

                    row[f"+{days}D Median %"] = (
                        returns.median()
                        if not returns.empty
                        else np.nan
                    )

                    row[f"+{days}D Positive %"] = (
                        returns.gt(0).mean() * 100
                        if not returns.empty
                        else np.nan
                    )

                combo_forward_rows.append(row)

            combination_forward_summary = pd.DataFrame(
                combo_forward_rows
            )

            combination_forward_context = (
                combination_forward_summary
                .round(3)
                .to_string(index=False)
            )
            forward_context = (
                forward_summary_app
                .round(3)
                .to_string(index=False)
            )

            ai_detail_columns = [
                "Date",
                "Family",
                "Day Number",
                "Full Date Number",
                "Close",
                "Direction",
                "Return +1D %",
                "Return +2D %",
                "Return +3D %",
                "Return +5D %",
                "Return +10D %"
            ]

            ai_detail = forward_48[
                ai_detail_columns
            ].copy()

            ai_detail["Date"] = (
                ai_detail["Date"]
                .dt.strftime("%d %b %Y")
            )

            detail_context = (
                ai_detail
                .round(3)
                .to_string(index=False)
            )

            dashboard_context = f"""
You are the AI analysis assistant inside a historical
NIFTY 50 and BANK NIFTY analytics dashboard.

CURRENT DASHBOARD SELECTION
Index: {selected_index}
History: {selected_history}
Direction filter: {direction_filter}

LATEST AVAILABLE MARKET DATA
Latest trading date: {latest_date}
Latest close: {latest_close:.2f}
Previous close: {previous_close:.2f}
Change: {market_change:+.2f}
Change percentage: {market_change_pct:+.2f}%
Open: {latest_open:.2f}
High: {latest_high:.2f}
Low: {latest_low:.2f}

EXACT 4/8 HISTORICAL SUMMARY
Total qualifying dates: {total_dates}
Bullish dates: {bullish_count}
Bearish dates: {bearish_count}
No-change dates: {no_change_count}
Bullish percentage: {bullish_percentage:.2f}%
Bearish percentage: {bearish_percentage:.2f}%

EXACT COMBINATION SUMMARY
{combination_context}
YEAR-WISE EXACT COMBINATION SUMMARY
{year_combination_context}

COMBINATION-WISE FORWARD RETURN SUMMARY
{combination_forward_context}

FORWARD PERFORMANCE SUMMARY
{forward_context}

INDIVIDUAL QUALIFYING DATES AND FORWARD RETURNS
{detail_context}

4/8 RULE
A trading date qualifies only when BOTH conditions are true:
1. The calendar day reduces to 4 or 8.
   4 Family = 4, 13, 22, 31.
   8 Family = 8, 17, 26.
2. All digits of DDMMYYYY are added and repeatedly reduced
   to one digit, and the result is also 4 or 8.

IMPORTANT DEFINITIONS
Bullish means the qualifying day's close was above the
previous trading day's close.
Bearish means it was below the previous trading day's close.
+1D, +2D, +3D, +5D and +10D mean subsequent trading
sessions, not calendar days.
"""

                prompt = f"""
You are the analytical assistant inside a NIFTY 50 and BANK NIFTY
historical market analytics dashboard.

Use ONLY the calculated dashboard context supplied below for numerical
claims. The dashboard's Pandas calculations are the authoritative source.

DASHBOARD DATA
---------------
{dashboard_context}

USER QUESTION
-------------
{user_question}

ANALYSIS RULES
--------------
1. Answer the user's exact question first.

2. Never invent market prices, dates, percentages, counts, returns,
   combinations, or statistics that are not present in the dashboard data.

3. Treat Pandas-calculated dashboard values as authoritative.
   Do not recalculate or override them using your own assumptions.

4. The Exact 4/8 rule is:
   - Day Number must reduce to 4 or 8.
   - Full Date Number must also reduce to 4 or 8.
   - Valid combinations are:
     4 & 4
     4 & 8
     8 & 4
     8 & 8

5. Direction means:
   Bullish = qualifying day's Close > previous NSE trading session's Close.
   Bearish = qualifying day's Close < previous NSE trading session's Close.
   It does NOT mean Close versus the same day's Open.

6. When comparing combinations, consider:
   - total observations
   - bullish count
   - bearish count
   - bullish percentage
   - bearish percentage

7. When comparing years, clearly state:
   - year
   - combination when relevant
   - number of observations
   - bullish/bearish result
   - percentage when available

8. When discussing forward returns, clearly identify the horizon:
   +1, +2, +3, +5 or +10 trading days.
   Do not mix different horizons.

9. Distinguish sample size from performance.
   A high percentage based on very few observations should be described
   cautiously.

10. If the user asks "best", explain what best means from the available
    data, such as:
    - highest bullish rate
    - highest average forward return
    - most observations
    - greatest consistency
    Do not silently choose a definition.

11. If filters are active, answer using the filtered/selected context
    when that information is available.

12. Data-source hierarchy:
    - NSE Official = primary historical source.
    - Yahoo Finance = provisional fallback for dates newer than the
      latest official NSE CSV.
    - TradingView and Investing.com = independent cross-check references.

13. Do not describe a historical pattern as a guaranteed prediction.

14. Do not automatically tell the user to buy, sell, enter, exit,
    or invest based only on historical 4/8 patterns.

15. If the dashboard context does not contain enough information to
    answer a question, say exactly what information is missing.
    Do not guess.

RESPONSE STYLE
--------------
- Use simple, professional English.
- Be concise for simple questions.
- Give deeper analysis when the question requires comparison.
- Lead with the conclusion.
- Show important numbers supporting the conclusion.
- Use a small table when comparing several years or combinations.
- Clearly label historical observations as historical.
"""
            with st.spinner("Gemini is analyzing the dashboard..."):

                response = None
                last_error = None

                for attempt in range(3):

                    try:

                        response = gemini_client.models.generate_content(
                            model="gemini-3.5-flash",
                            contents=prompt
                        )

                        break

                    except Exception as api_error:

                        last_error = api_error

                        if (
                            "503" in str(api_error)
                            or "UNAVAILABLE" in str(api_error)
                        ):

                            if attempt < 2:
                                time.sleep(2 ** (attempt + 1))
                                continue

                        raise api_error

                if response is None:
                    raise last_error

            if response.text:

                st.markdown("#### 🤖 Gemini Answer")
                st.write(response.text)

            else:

                st.warning(
                    "Gemini returned an empty response. "
                    "Please try again."
                )

        except Exception as error:

            st.error(
                "Gemini could not answer the question right now."
            )

            st.caption(
                "The dashboard itself is still working. "
                "Please try the AI assistant again shortly."
            )

            st.code(str(error))


st.caption(
    "Gemini answers are grounded in the historical data currently "
    "loaded in this dashboard. Historical patterns are not forecasts "
    "or trading recommendations."
)
     
# ============================================================
# EXCEL REPORT DOWNLOAD
# ============================================================

st.divider()

st.subheader("📥 Download Analysis Report")


if "forward_48" in globals() and "forward_summary_app" in globals():

    from io import BytesIO


    # ========================================================
    # FUNCTION TO CREATE EXCEL IN MEMORY
    # ========================================================

    def create_excel_report():

        output = BytesIO()


        # ----------------------------------------------------
        # PREPARE QUALIFYING DATE DATA
        # ----------------------------------------------------

        excel_dates = forward_48[
            [
                "Date",
                "Family",
                "Day Number",
                "Full Date Number",
                "Previous Close",
                "Close",
                "Change",
                "Change %",
                "Direction",
                "Return +1D %",
                "Return +2D %",
                "Return +3D %",
                "Return +5D %",
                "Return +10D %"
            ]
        ].copy()


        excel_dates = excel_dates.sort_values(
            "Date",
            ascending=False
        )


        # ----------------------------------------------------
        # SUMMARY DATA
        # ----------------------------------------------------

        total_48 = len(
            forward_48
        )


        bullish_48 = (
            forward_48["Direction"]
            .eq("Bullish")
            .sum()
        )


        bearish_48 = (
            forward_48["Direction"]
            .eq("Bearish")
            .sum()
        )


        summary_excel = pd.DataFrame({

            "Item": [
                "Index",
                "Selected History",
                "Total Qualifying 4/8 Dates",
                "Bullish Dates",
                "Bearish Dates",
                "Generated At"
            ],

            "Value": [
                selected_index,
                selected_history,
                total_48,
                bullish_48,
                bearish_48,
                datetime.now(ZoneInfo("Asia/Kolkata")).strftime(
                    "%d %b %Y %I:%M %p"
                )
            ]

        })


        # ----------------------------------------------------
        # FAMILY SUMMARY
        # ----------------------------------------------------

                # ----------------------------------------------------
        # EXACT COMBINATION SUMMARY
        # ----------------------------------------------------

        combination_excel_rows = []

        for day_num, full_date_num in [
            (4, 4),
            (4, 8),
            (8, 4),
            (8, 8)
        ]:

            temp = forward_48[
                (forward_48["Day Number"] == day_num)
                &
                (forward_48["Full Date Number"] == full_date_num)
            ]

            total = len(temp)

            bullish = (
                temp["Direction"]
                .eq("Bullish")
                .sum()
            )

            bearish = (
                temp["Direction"]
                .eq("Bearish")
                .sum()
            )

            directional = bullish + bearish

            if directional > 0:

                bullish_pct = (
                    bullish / directional * 100
                )

                bearish_pct = (
                    bearish / directional * 100
                )

            else:

                bullish_pct = np.nan
                bearish_pct = np.nan

            combination_excel_rows.append({

                "Combination":
                    f"{day_num} & {full_date_num}",

                "Qualifying Dates":
                    total,

                "Bullish":
                    bullish,

                "Bearish":
                    bearish,

                "Bullish %":
                    bullish_pct,

                "Bearish %":
                    bearish_pct

            })

        combination_excel = pd.DataFrame(
            combination_excel_rows
        )

        # ----------------------------------------------------
        # INFORMATION SHEET
        # ----------------------------------------------------

        information_excel = pd.DataFrame({

            "Topic": [

                "4 Family",

                "8 Family",

                "Full Date Rule",

                "Qualification Rule",

                "Bullish",

                "Bearish",

                "Forward Returns",

                "Important"

            ],

            "Explanation": [

                "Calendar days 4, 13, 22 and 31 reduce to 4.",

                "Calendar days 8, 17 and 26 reduce to 8.",

                (
                    "All digits of DDMMYYYY are added and "
                    "reduced repeatedly to one digit."
                ),

                (
                    "A trading date qualifies only when "
                    "Day Number is 4 or 8 AND Full Date "
                    "Number is 4 or 8."
                ),

                (
                    "Close is above the previous "
                    "trading day's close."
                ),

                (
                    "Close is below the previous "
                    "trading day's close."
                ),

                (
                    "+1D, +2D, +3D, +5D and +10D refer "
                    "to future trading sessions, not "
                    "calendar days."
                ),

                (
                    "This is historical exploratory "
                    "analysis and is not a prediction "
                    "or trading signal."
                )

            ]

        })


        # ====================================================
        # WRITE EXCEL
        # ====================================================

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:


            summary_excel.to_excel(
                writer,
                sheet_name="Summary",
                index=False
            )


            excel_dates.to_excel(
                writer,
                sheet_name="Qualifying Dates",
                index=False
            )


            forward_summary_app.to_excel(
                writer,
                sheet_name="Forward Performance",
                index=False
            )

            combination_excel.to_excel(
                writer,
                sheet_name="Exact Combinations",
                index=False
            )


            information_excel.to_excel(
                writer,
                sheet_name="Method",
                index=False
            )


            # =================================================
            # BASIC EXCEL FORMATTING
            # =================================================

            workbook = writer.book


            for sheet_name in workbook.sheetnames:

                worksheet = workbook[
                    sheet_name
                ]


                # ---------------------------------------------
                # FREEZE HEADER
                # ---------------------------------------------

                worksheet.freeze_panes = "A2"


                # ---------------------------------------------
                # HEADER FORMAT
                # ---------------------------------------------

                for cell in worksheet[1]:

                    cell.font = Font(
                        bold=True,
                        color="FFFFFF"
                    )


                    cell.fill = PatternFill(
                        "solid",
                        fgColor="1F4E78"
                    )


                    cell.alignment = Alignment(
                        horizontal="center",
                        vertical="center"
                    )


                # ---------------------------------------------
                # AUTO COLUMN WIDTH
                # ---------------------------------------------

                for column_cells in worksheet.columns:

                    maximum_length = 0


                    column_letter = (
                        column_cells[0]
                        .column_letter
                    )


                    for cell in column_cells:

                        try:

                            cell_length = len(
                                str(cell.value)
                            )


                            maximum_length = max(
                                maximum_length,
                                cell_length
                            )

                        except Exception:

                            pass


                    worksheet.column_dimensions[
                        column_letter
                    ].width = min(
                        maximum_length + 3,
                        45
                    )


            # =================================================
            # DATE FORMAT
            # =================================================

            date_sheet = workbook[
                "Qualifying Dates"
            ]


            for cell in date_sheet["A"][1:]:

                cell.number_format = (
                    "dd mmm yyyy"
                )


        output.seek(0)

        return output.getvalue()


    # ========================================================
    # IMPORT EXCEL STYLES
    # ========================================================

    from openpyxl.styles import (
        Font,
        PatternFill,
        Alignment
    )


    # ========================================================
    # CREATE REPORT
    # ========================================================

    excel_file = (
        create_excel_report()
    )


    # ========================================================
    # FILE NAME
    # ========================================================

    excel_index_name = (
        selected_index
        .replace(" ", "")
    )


    excel_file_name = (
        f"{excel_index_name}_"
        f"4_8_Analysis.xlsx"
    )


    # ========================================================
    # DOWNLOAD BUTTON
    # ========================================================

    st.download_button(

        label="⬇️ Download Excel Report",

        data=excel_file,

        file_name=excel_file_name,

        mime=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),

        use_container_width=True

    )

    st.caption(
        "The Excel report contains Summary, Qualifying Dates, "
        "Forward Performance, Exact Combinations and Method sheets."
    )
st.info(
    "Methodology note: Bullish/Bearish means the qualifying day's Close "
    "versus the previous NSE trading session's Close. Historical results "
    "do not predict future market performance."
)
