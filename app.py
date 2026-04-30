import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta

st.set_page_config(page_title="RTT STATUS", layout="wide")

st.title("DASHBOARD")

# =====================================================
# FILE UPLOADS
# =====================================================
new_file = st.file_uploader("Upload new.csv", type=["csv"])
resolved_file = st.file_uploader("Upload resolved.csv", type=["csv"])
closed_file = st.file_uploader("Upload closed.csv", type=["csv"])

# =====================================================
# WORKGROUP FILTER
# =====================================================
allowed_workgroups = [
    "L1-Rakuten-EPC-OPS",
    "L1-Rakuten-CGNAT-OPS",
    "L1-Rakuten-ETWS-OPS",
    "L1-Rakuten-PACO-CIOT-OPS",
    "L1-Rakuten-DPI-OPS",
    "L3-Allot-DPI-CORE",
    "L2-RAKUTEN-PACO-SA",
    "L2-RAKUTEN-PACO-QCM",
    "L3-RAKUTEN-PACO-TG"
]

# =====================================================
# DATE SETUP
# =====================================================
today = datetime.now().date()
yesterday = today - timedelta(days=1)
day2 = today - timedelta(days=2)

# =====================================================
# SAFE DATE PARSER
# =====================================================
def parse_date(val):
    if pd.isna(val):
        return None
    val = str(val).split("\n")[0].replace("JST", "").strip()
    return pd.to_datetime(val, errors="coerce")

# =====================================================
# AGEING PARSER (FIXED: DAYS + HOURS + MINUTES)
# =====================================================
def extract_total_days(ageing):
    try:
        ageing = str(ageing).lower()

        days = 0
        hours = 0
        minutes = 0

        day_match = re.search(r'(\d+)\s*day', ageing)
        hour_match = re.search(r'(\d+)\s*hour', ageing)
        min_match = re.search(r'(\d+)\s*minute', ageing)

        if day_match:
            days = int(day_match.group(1))
        if hour_match:
            hours = int(hour_match.group(1))
        if min_match:
            minutes = int(min_match.group(1))

        return days + (hours / 24) + (minutes / 1440)

    except:
        return 0

# =====================================================
# RESOLVED + CLOSED METRICS
# =====================================================
resolved_closed_metrics = {}

if resolved_file and closed_file:

    res_df = pd.read_csv(resolved_file)
    cl_df = pd.read_csv(closed_file)

    res_df = res_df[res_df["Assignee Workgroup"].isin(allowed_workgroups)]
    cl_df = cl_df[cl_df["Assignee Workgroup"].isin(allowed_workgroups)]

    # ---------------- RESOLVED ----------------
    res_df["Created On"] = res_df["Created On & By"].apply(parse_date)
    res_df["Resolved On"] = res_df["Resolved On & By"].apply(parse_date)

    res_df = res_df.dropna(subset=["Created On", "Resolved On"])

    res_df["Created_Date"] = res_df["Created On"].dt.date
    res_df["Resolved_Date"] = res_df["Resolved On"].dt.date

    res_df["TRUE"] = res_df["Created_Date"] == res_df["Resolved_Date"]
    res_df["FALSE"] = res_df["Created_Date"] != res_df["Resolved_Date"]

    # ---------------- CLOSED ----------------
    cl_df["Created On"] = cl_df["Created On & By"].apply(parse_date)
    cl_df["Closed On"] = cl_df["Closed On & By"].apply(parse_date)

    cl_df = cl_df.dropna(subset=["Created On", "Closed On"])

    cl_df["Created_Date"] = cl_df["Created On"].dt.date
    cl_df["Closed_Date"] = cl_df["Closed On"].dt.date

    cl_df["TRUE"] = cl_df["Created_Date"] == cl_df["Closed_Date"]
    cl_df["FALSE"] = cl_df["Created_Date"] != cl_df["Closed_Date"]

    for wg in allowed_workgroups:

        res_true = res_df[res_df["Assignee Workgroup"] == wg]["TRUE"].sum()
        res_false = res_df[res_df["Assignee Workgroup"] == wg]["FALSE"].sum()

        cl_true = cl_df[cl_df["Assignee Workgroup"] == wg]["TRUE"].sum()
        cl_false = cl_df[cl_df["Assignee Workgroup"] == wg]["FALSE"].sum()

        resolved_closed_metrics[wg] = {
            "Resolved_New": res_true + cl_true,
            "Resolved_Old": res_false + cl_false
        }

# =====================================================
# NEW RTT STATUS
# =====================================================
if new_file:

    df_new = pd.read_csv(new_file)
    df_new = df_new[df_new["Assignee Workgroup"].isin(allowed_workgroups)]

    df_new["Created On"] = df_new["Created On & By"].apply(parse_date)
    df_new = df_new.dropna(subset=["Created On"])

    df_new["Created_Date"] = df_new["Created On"].dt.date

    df_new["OLD"] = df_new["Created_Date"] <= day2
    df_new["NEW"] = df_new["Created_Date"] == yesterday

    df_new["Ageing"] = df_new["Ageing"].astype(str).str.strip()

    report = []

    for wg in allowed_workgroups:

        temp = df_new[df_new["Assignee Workgroup"] == wg].copy()

        old_cnt = temp["OLD"].sum()
        new_cnt = temp["NEW"].sum()

        resolved_old = resolved_closed_metrics.get(wg, {}).get("Resolved_Old", 0)
        resolved_new = resolved_closed_metrics.get(wg, {}).get("Resolved_New", 0)

        # =================================================
        # AGEING CALCULATION FIXED
        # =================================================
        temp["Ageing_Days"] = temp["Ageing"].apply(extract_total_days)

        gt7_cnt = temp[temp["Ageing_Days"] >= 7].shape[0]

        gt3_cnt = temp[
            (temp["Ageing_Days"] >= 3) &
            (temp["Ageing_Days"] < 7)
        ].shape[0]

        # =================================================
        # TOTAL RTTs = NEW RTTs ONLY (as requested)
        # =================================================
        total = new_cnt

        report.append({
            "Work Group": wg,
            "Old RTTs (Before Yesterday)": old_cnt,
            "New RTTs (Yesterday)": new_cnt,
            "Old RTTs resolved (Yesterday)": resolved_old,
            "Resolved New RTTs (Yesterday)": resolved_new,
            "Total RTTs": total,
            ">3 Days RTTs": gt3_cnt,
            ">7 Days RTTs": gt7_cnt
        })

    report_df = pd.DataFrame(report)

    # TOTAL ROW
    total_row = {
        "Work Group": "TOTAL",
        "Old RTTs (Before Yesterday)": report_df["Old RTTs (Before Yesterday)"].sum(),
        "New RTTs (Yesterday)": report_df["New RTTs (Yesterday)"].sum(),
        "Old RTTs resolved (Yesterday)": report_df["Old RTTs resolved (Yesterday)"].sum(),
        "Resolved New RTTs (Yesterday)": report_df["Resolved New RTTs (Yesterday)"].sum(),
        "Total RTTs": report_df["Total RTTs"].sum(),
        ">3 Days RTTs": report_df[">3 Days RTTs"].sum(),
        ">7 Days RTTs": report_df[">7 Days RTTs"].sum()
    }

    report_df = pd.concat([report_df, pd.DataFrame([total_row])], ignore_index=True)

    st.subheader("📌 RTT STATUS")
    st.dataframe(report_df, use_container_width=True)

else:
    st.info("Upload new.csv to view NEW RTT STATUS")