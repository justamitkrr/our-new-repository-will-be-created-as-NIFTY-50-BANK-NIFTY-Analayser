
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime


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

selected_index = st.selectbox(
    "Select Index",
    options=list(INDEX_OPTIONS.keys()),
    index=0
)

selected_symbol = INDEX_OPTIONS[
    selected_index
]


# ============================================================
# HISTORY SELECTION
# ============================================================

history_options = {
    "1 Month": "1mo",
    "3 Months": "3mo",
    "6 Months": "6mo",
    "1 Year": "1y",
    "2 Years": "2y",
    "3 Years": "3y",
    "5 Years": "5y"
}


selected_history = st.selectbox(
    "Select History",
    options=list(history_options.keys()),
    index=6
)


yahoo_period = history_options[
    selected_history
]


# ============================================================
# DOWNLOAD MARKET DATA
# ============================================================

@st.cache_data(ttl=300)
def download_market_data(
    symbol,
    period
):

    data = yf.download(
        symbol,
        period=period,
        interval="1d",
        auto_adjust=False,
        progress=False
    )

    if isinstance(
        data.columns,
        pd.MultiIndex
    ):

        data.columns = (
            data.columns
            .get_level_values(0)
        )

    return data


# ============================================================
# LOAD DATA
# ============================================================

try:

    market_data = download_market_data(
        selected_symbol,
        yahoo_period
    )


    if market_data.empty:

        st.error(
            "No market data received."
        )


    else:

        market_data = (
            market_data
            .reset_index()
        )


        market_data["Date"] = pd.to_datetime(
            market_data["Date"]
        )


        market_data = (
            market_data
            .sort_values("Date")
            .reset_index(drop=True)
        )


        # ====================================================
        # BASIC INFORMATION
        # ====================================================

        latest_row = market_data.iloc[-1]


        latest_close = float(
            latest_row["Close"]
        )


        latest_open = float(
            latest_row["Open"]
        )


        latest_high = float(
            latest_row["High"]
        )


        latest_low = float(
            latest_row["Low"]
        )


        if len(market_data) >= 2:

            previous_close = float(
                market_data.iloc[-2]["Close"]
            )

        else:

            previous_close = np.nan


        if pd.notna(previous_close):

            market_change = (
                latest_close
                -
                previous_close
            )


            market_change_pct = (
                market_change
                /
                previous_close
                *
                100
            )

        else:

            market_change = np.nan
            market_change_pct = np.nan


        latest_date = (
            market_data.iloc[-1]["Date"]
            .strftime("%d %b %Y")
        )


        # ====================================================
        # DISPLAY
        # ====================================================

        st.success(
            f"{selected_index} data loaded successfully."
        )


        st.write(
            f"Latest available trading date: **{latest_date}**"
        )


        col1, col2, col3, col4 = st.columns(4)


        col1.metric(
            "Latest Close",
            f"{latest_close:,.2f}"
        )


        col2.metric(
            "Previous Close",
            f"{previous_close:,.2f}"
        )


        col3.metric(
            "Change",
            f"{market_change:+,.2f}"
        )


        col4.metric(
            "Change %",
            f"{market_change_pct:+.2f}%"
        )


        col5, col6, col7 = st.columns(3)


        col5.metric(
            "Open",
            f"{latest_open:,.2f}"
        )


        col6.metric(
            "High",
            f"{latest_high:,.2f}"
        )


        col7.metric(
            "Low",
            f"{latest_low:,.2f}"
        )


except Exception as error:

    st.error(
        "Market data could not be loaded."
    )

    st.exception(error)


# ============================================================
# EXACT 4/8 HISTORICAL ANALYSIS
# ============================================================

st.divider()

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
    # DIRECTION FILTER
    # --------------------------------------------------------

    direction_filter = st.selectbox(
        "Direction Filter",
        [
            "All",
            "Bullish",
            "Bearish"
        ]
    )


    if direction_filter == "Bullish":

        displayed_dates = special_dates[
            special_dates["Direction"] == "Bullish"
        ].copy()


    elif direction_filter == "Bearish":

        displayed_dates = special_dates[
            special_dates["Direction"] == "Bearish"
        ].copy()


    else:

        displayed_dates = special_dates.copy()


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
    # FAMILY ANALYSIS
    # ========================================================

    st.markdown(
        "### 4 Family vs 8 Family"
    )


    family_rows = []


    for family in [
        "4 Family",
        "8 Family"
    ]:

        family_data = special_dates[
            special_dates["Family"] == family
        ]


        family_total = len(
            family_data
        )


        family_bullish = (
            family_data["Direction"]
            .eq("Bullish")
            .sum()
        )


        family_bearish = (
            family_data["Direction"]
            .eq("Bearish")
            .sum()
        )


        family_directional = (
            family_bullish
            +
            family_bearish
        )


        if family_directional > 0:

            family_bullish_pct = (
                family_bullish
                /
                family_directional
                *
                100
            )


            family_bearish_pct = (
                family_bearish
                /
                family_directional
                *
                100
            )


        else:

            family_bullish_pct = np.nan
            family_bearish_pct = np.nan


        family_rows.append({

            "Family":
                family,

            "Dates":
                family_total,

            "Bullish":
                family_bullish,

            "Bearish":
                family_bearish,

            "Bullish %":
                family_bullish_pct,

            "Bearish %":
                family_bearish_pct

        })


    family_summary = pd.DataFrame(
        family_rows
    )


    st.dataframe(
        family_summary.style.format({
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
                "Direction"
            ]
        ].copy()


        # Preferred date format:
        # 06 Oct 2026

        date_table["Date"] = (
            date_table["Date"]
            .dt.strftime("%d %b %Y")
        )


        date_table = (
            date_table
            .sort_values(
                "Date",
                ascending=False
            )
            .reset_index(drop=True)
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
    # SIMPLE FAMILY COMPARISON CHART
    # ========================================================

    st.markdown(
        "### 4 Family vs 8 Family — Same-Day Direction"
    )


    family_chart_rows = []


    for family in [
        "4 Family",
        "8 Family"
    ]:

        temp = chart_48[
            chart_48["Family"] == family
        ]


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


        total_directional = (
            bullish
            +
            bearish
        )


        if total_directional > 0:

            bullish_pct = (
                bullish
                /
                total_directional
                *
                100
            )


            bearish_pct = (
                bearish
                /
                total_directional
                *
                100
            )


        else:

            bullish_pct = 0
            bearish_pct = 0


        family_chart_rows.append({

            "Family":
                family,

            "Bullish %":
                bullish_pct,

            "Bearish %":
                bearish_pct

        })


    family_chart_app = (
        pd.DataFrame(
            family_chart_rows
        )
        .set_index("Family")
    )


    st.bar_chart(
        family_chart_app
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
                datetime.now().strftime(
                    "%d %b %Y %I:%M %p"
                )
            ]

        })


        # ----------------------------------------------------
        # FAMILY SUMMARY
        # ----------------------------------------------------

        family_excel_rows = []


        for family in [
            "4 Family",
            "8 Family"
        ]:

            temp = forward_48[
                forward_48["Family"] == family
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


            directional = (
                bullish
                +
                bearish
            )


            if directional > 0:

                bullish_pct = (
                    bullish
                    /
                    directional
                    *
                    100
                )


                bearish_pct = (
                    bearish
                    /
                    directional
                    *
                    100
                )

            else:

                bullish_pct = np.nan
                bearish_pct = np.nan


            family_excel_rows.append({

                "Family":
                    family,

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


        family_excel = pd.DataFrame(
            family_excel_rows
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


            family_excel.to_excel(
                writer,
                sheet_name="Family Analysis",
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
        "Forward Performance, Family Analysis and Method sheets."
    )
