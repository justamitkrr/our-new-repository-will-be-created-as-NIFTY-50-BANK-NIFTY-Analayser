
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

