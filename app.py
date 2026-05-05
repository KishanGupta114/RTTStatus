import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="RTT STATUS", layout="wide")

# =====================================================
# PAGE SELECTOR
# =====================================================
page = st.sidebar.selectbox("Select Page", ["RTT Dashboard", "Tracker"])
st.sidebar.caption("Version: v1.2.0")

# =====================================================
# SETTINGS
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

today = datetime.now().date()
yesterday = today - timedelta(days=1)
day2 = today - timedelta(days=2)

# =====================================================
# FUNCTIONS
# =====================================================
def parse_date(val):
    if pd.isna(val):
        return None
    val = str(val).split("\n")[0].replace("JST", "").strip()
    return pd.to_datetime(val, errors="coerce")

def extract_total_days(ageing):
    try:
        ageing = str(ageing).lower()

        years = int(re.search(r'(\d+)\s*year', ageing).group(1)) if re.search(r'(\d+)\s*year', ageing) else 0
        months = int(re.search(r'(\d+)\s*month', ageing).group(1)) if re.search(r'(\d+)\s*month', ageing) else 0
        days = int(re.search(r'(\d+)\s*day', ageing).group(1)) if re.search(r'(\d+)\s*day', ageing) else 0
        hours = int(re.search(r'(\d+)\s*hour', ageing).group(1)) if re.search(r'(\d+)\s*hour', ageing) else 0
        minutes = int(re.search(r'(\d+)\s*minute', ageing).group(1)) if re.search(r'(\d+)\s*minute', ageing) else 0

        return (years * 365) + (months * 30) + days + (hours / 24) + (minutes / 1440)

    except:
        return 0

# =====================================================
# DASHBOARD
# =====================================================
if page == "RTT Dashboard":

    st.title("DASHBOARD")

    new_file = st.file_uploader("Upload new.csv", type=["csv"])
    resolved_file = st.file_uploader("Upload resolved.csv", type=["csv"])
    closed_file = st.file_uploader("Upload closed.csv", type=["csv"])
    rvs_file = st.file_uploader("Upload rvs.csv", type=["csv"])
    rpt_file = st.file_uploader("Upload rpt.csv", type=["csv"])

    resolved_closed_metrics = {}
    rvs_metrics = {}
    rpt_metrics = {}

    # RVS
    if rvs_file:
        rvs_df = pd.read_csv(rvs_file)

        if "Assignee Workgroup" not in rvs_df.columns:
            st.error("❌ 'Assignee Workgroup' missing in rvs.csv")
            st.stop()

        rvs_df = rvs_df[rvs_df["Assignee Workgroup"].isin(allowed_workgroups)]

        if "Ageing" in rvs_df.columns:
            rvs_df["Ageing_Days"] = rvs_df["Ageing"].astype(str).apply(extract_total_days)
        else:
            rvs_df["Ageing_Days"] = 0

        for wg in allowed_workgroups:
            temp = rvs_df[rvs_df["Assignee Workgroup"] == wg]

            rvs_metrics[wg] = {
                "Total_RVS": temp.shape[0],
                ">7_RVS": temp[temp["Ageing_Days"] >= 7].shape[0]
            }

    # RPT
    if rpt_file:
        rpt_df = pd.read_csv(rpt_file)

        if "Assignee Workgroup" not in rpt_df.columns:
            st.error("❌ 'Assignee Workgroup' missing in rpt.csv")
            st.stop()

        rpt_df = rpt_df[rpt_df["Assignee Workgroup"].isin(allowed_workgroups)]

        for wg in allowed_workgroups:
            rpt_metrics[wg] = {
                "Total_RPT": rpt_df[rpt_df["Assignee Workgroup"] == wg].shape[0]
            }

    # RESOLVED + CLOSED
    if resolved_file and closed_file:

        res_df = pd.read_csv(resolved_file)
        cl_df = pd.read_csv(closed_file)

        if "Assignee Workgroup" not in res_df.columns or "Assignee Workgroup" not in cl_df.columns:
            st.error("❌ Workgroup column missing")
            st.stop()

        res_df = res_df[res_df["Assignee Workgroup"].isin(allowed_workgroups)]
        cl_df = cl_df[cl_df["Assignee Workgroup"].isin(allowed_workgroups)]

        res_df["Created On"] = res_df["Created On & By"].apply(parse_date)
        res_df["Resolved On"] = res_df["Resolved On & By"].apply(parse_date)
        res_df = res_df.dropna(subset=["Created On", "Resolved On"])

        cl_df["Created On"] = cl_df["Created On & By"].apply(parse_date)
        cl_df["Closed On"] = cl_df["Closed On & By"].apply(parse_date)
        cl_df = cl_df.dropna(subset=["Created On", "Closed On"])

        for wg in allowed_workgroups:

            res_temp = res_df[res_df["Assignee Workgroup"] == wg]
            cl_temp = cl_df[cl_df["Assignee Workgroup"] == wg]

            resolved_closed_metrics[wg] = {
                "Resolved_New": (res_temp["Created On"].dt.date == res_temp["Resolved On"].dt.date).sum() +
                                (cl_temp["Created On"].dt.date == cl_temp["Closed On"].dt.date).sum(),

                "Resolved_Old": (res_temp["Created On"].dt.date != res_temp["Resolved On"].dt.date).sum() +
                                (cl_temp["Created On"].dt.date != cl_temp["Closed On"].dt.date).sum()
            }

    # MAIN RTT
    if new_file:

        df_new = pd.read_csv(new_file)

        if "Assignee Workgroup" not in df_new.columns:
            st.error("❌ 'Assignee Workgroup' missing in new.csv")
            st.stop()

        df_new = df_new[df_new["Assignee Workgroup"].isin(allowed_workgroups)]

        df_new["Created On"] = df_new["Created On & By"].apply(parse_date)
        df_new = df_new.dropna(subset=["Created On"])

        df_new["Created_Date"] = df_new["Created On"].dt.date
        df_new["OLD"] = df_new["Created_Date"] <= day2
        df_new["NEW"] = df_new["Created_Date"] == yesterday

        if "Ageing" in df_new.columns:
            df_new["Ageing_Days"] = df_new["Ageing"].astype(str).apply(extract_total_days)
        else:
            df_new["Ageing_Days"] = 0

        report = []

        for wg in allowed_workgroups:

            temp = df_new[df_new["Assignee Workgroup"] == wg]

            report.append({
                "Work Group": wg,
                "Old  RTTs (Before Yesterday)": temp["OLD"].sum(),
                "Old RTTs resolved (Yesterday)": resolved_closed_metrics.get(wg, {}).get("Resolved_Old", 0),
                "New RTTs (Yesterday)": temp["NEW"].sum(),
                "Resolved New RTTs (Yesterday)": resolved_closed_metrics.get(wg, {}).get("Resolved_New", 0),
                "Total RTTs": temp["NEW"].sum() + temp["OLD"].sum(),
                ">3 Days RTTs": temp[(temp["Ageing_Days"] >= 3) & (temp["Ageing_Days"] < 7)].shape[0],
                ">7 Days RTTs": temp[temp["Ageing_Days"] >= 7].shape[0],
                "Total RVS": rvs_metrics.get(wg, {}).get("Total_RVS", 0),
                ">7 Days RVS": rvs_metrics.get(wg, {}).get(">7_RVS", 0),
                "Total PTN/RPT": rpt_metrics.get(wg, {}).get("Total_RPT", 0)
            })

        report_df = pd.DataFrame(report)

        total_row = {"Work Group": "TOTAL"}
        for col in report_df.columns[1:]:
            total_row[col] = report_df[col].sum()

        report_df = pd.concat([report_df, pd.DataFrame([total_row])], ignore_index=True)

        st.subheader("📌 FINAL DASHBOARD")
        st.dataframe(report_df, width="stretch")

    else:
        st.info("Upload new.csv to view dashboard")

# =====================================================
# TRACKER
# =====================================================
if page == "Tracker":

    st.title("📝 Issue Tracker")

    file_path = "tracker.csv"

    if os.path.exists(file_path):
        tracker_df = pd.read_csv(file_path)
    else:
        tracker_df = pd.DataFrame(columns=["Date", "Type", "Description"])

    # ADD ENTRY
    with st.form("form"):
        t = st.selectbox("Type", ["Bug", "Feature", "Improvement", "Query"])
        d = st.text_area("Description")

        if st.form_submit_button("Add"):
            if d.strip():
                tracker_df = pd.concat([tracker_df, pd.DataFrame([{
                    "Date": datetime.now(),
                    "Type": t,
                    "Description": d
                }])])
                tracker_df.to_csv(file_path, index=False)
                st.success("Added ✅")
                st.rerun()

    st.subheader("📋 Entries")
    st.dataframe(tracker_df, width="stretch")

    # DELETE ENTRY (FIXED)
    if not tracker_df.empty:

        st.subheader("🗑 Delete Entry")

        selected_index = st.selectbox(
            "Select entry to delete",
            tracker_df.index
        )

        if st.button("Delete Selected"):
            tracker_df = tracker_df.drop(selected_index).reset_index(drop=True)
            tracker_df.to_csv(file_path, index=False)

            st.success("Deleted successfully ✅")
            st.rerun()