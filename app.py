import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime
import time

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
