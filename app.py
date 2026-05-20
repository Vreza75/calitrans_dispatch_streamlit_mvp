from pathlib import Path
import base64
import pandas as pd
import streamlit as st

from smartsheet_client import DispatchSmartsheetClient
from validators import validate_dispatch_rows
from profittools_export import export_ready_loads

def filter_table(df, search_text="", status_filter="All"):
    filtered = df.copy()

    if status_filter != "All" and "Status" in filtered.columns:
        filtered = filtered[filtered["Status"] == status_filter]

    if search_text:
        search_text = search_text.lower()
        filtered = filtered[
            filtered.astype(str)
            .apply(lambda row: row.str.lower().str.contains(search_text).any(), axis=1)
        ]

    return filtered
st.set_page_config(
    page_title="Calitrans Dispatch Center",
    page_icon="🚚",
    layout="wide",
)


def load_css():
    st.markdown(Path("theme.css").read_text(encoding="utf-8"), unsafe_allow_html=True)


def image_to_base64(path: str) -> str:
    file_path = Path(path)
    if not file_path.exists():
        return ""
    return base64.b64encode(file_path.read_bytes()).decode("utf-8")


load_css()


@st.cache_data(ttl=60)
def load_dispatch_data() -> pd.DataFrame:
    client = DispatchSmartsheetClient()
    sheet = client.get_sheet()
    return client.rows_to_dataframe(sheet)


def refresh_data():
    st.cache_data.clear()


banner_b64 = image_to_base64("assets/header_banner.png")

if banner_b64:
    st.markdown(f"""
    <div class="banner-wrapper">
        <img class="header-banner" src="data:image/png;base64,{banner_b64}" />
    </div>
    """, unsafe_allow_html=True)
else:
    st.error("Header banner not found. Save it as assets/header_banner.png")


try:
    df = load_dispatch_data()
except Exception as exc:
    st.error(f"Could not load Smartsheet data: {exc}")
    st.stop()

if df.empty:
    st.warning("No rows found in the dispatch sheet.")
    st.stop()

required_columns = [
    "_row_id", "Load ID", "Customer", "Pickup", "Delivery",
    "Status", "Driver", "Truck", "Dispatcher Notes"
]
for col in required_columns:
    if col not in df.columns:
        df[col] = None


active_statuses = ["Ready to Dispatch", "Assigned", "En Route to Pickup", "Hold/Need Info"]
active_count = len(df[df["Status"].isin(active_statuses)])
ready_count = len(df[df["Status"] == "Ready to Dispatch"])
assigned_count = len(df[df["Status"] == "Assigned"])
hold_count = len(df[df["Status"] == "Hold/Need Info"])
exported_count = len(df[df["Status"] == "Exported to ProfitTools"])


def kpi_card(icon, label, value, sub, css_class):
    st.markdown(f"""
    <div class="kpi-card">
      <div class="kpi-icon {css_class}">{icon}</div>
      <div>
        <div class="kpi-label {css_class}">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    kpi_card("🚛", "Active Loads", active_count, "Total active loads", "kpi-blue")
with k2:
    kpi_card("✅", "Ready", ready_count, "Ready to dispatch", "kpi-green")
with k3:
    kpi_card("👤", "Assigned", assigned_count, "Currently assigned", "kpi-orange")
with k4:
    kpi_card("⚠️", "Hold / Need Info", hold_count, "Needs attention", "kpi-yellow")
with k5:
    kpi_card("📤", "Exported", exported_count, "ProfitTools exported", "kpi-blue")


st.markdown("<br>", unsafe_allow_html=True)

display_columns = [
    "_row_id",
    "Load ID",
    "Customer",
    "Pickup",
    "Delivery",
    "Status",
    "Driver",
    "Truck",
    "Dispatcher Notes",
]
display_columns = [col for col in display_columns if col in df.columns]


def show_load_table(data: pd.DataFrame, title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)

    editable_columns = [
        "Status",
        "Driver",
        "Truck",
        "Dispatcher Notes",
    ]

    driver_options = [""] + sorted([str(x) for x in df["Driver"].dropna().unique() if str(x).strip()])

    column_config = {
        "_row_id": st.column_config.TextColumn("_row_id", disabled=True),
        "Load ID": st.column_config.TextColumn("Load ID", disabled=True),
        "Customer": st.column_config.TextColumn("Customer", disabled=True),
        "Pickup": st.column_config.TextColumn("Pickup", disabled=True),
        "Delivery": st.column_config.TextColumn("Delivery", disabled=True),
        "Status": st.column_config.SelectboxColumn(
            "Status",
            options=[
                "Ready to Dispatch",
                "Assigned",
                "En Route to Pickup",
                "Hold/Need Info",
                "Cancelled",
                "Exported to ProfitTools",
            ],
        ),
        "Driver": st.column_config.SelectboxColumn("Driver", options=driver_options),
        "Truck": st.column_config.TextColumn("Truck"),
        "Dispatcher Notes": st.column_config.TextColumn("Dispatcher Notes"),
    }

    edited_data = st.data_editor(
        data[display_columns],
        use_container_width=True,
        hide_index=True,
        disabled=[col for col in display_columns if col not in editable_columns],
        column_config=column_config,
        key=f"{title}_editor",
        height=390,
    )

    if st.button(f"💾 Save {title} Changes", key=f"{title}_save"):
        client = DispatchSmartsheetClient()
        changes_saved = 0

        original = data[display_columns].reset_index(drop=True)
        edited = edited_data.reset_index(drop=True)

        for i in range(len(edited)):
            row_id = int(edited.loc[i, "_row_id"])
            updates = {}

            for col in editable_columns:
                if col not in original.columns or col not in edited.columns:
                    continue

                old_value = original.loc[i, col]
                new_value = edited.loc[i, col]

                old_value = "" if pd.isna(old_value) else old_value
                new_value = "" if pd.isna(new_value) else new_value

                if old_value != new_value:
                    updates[col] = new_value

            if updates:
                client.update_row_fields(row_id, updates)
                changes_saved += 1

        if changes_saved:
            st.success(f"Saved changes to {changes_saved} row(s).")
            refresh_data()
            st.rerun()
        else:
            st.info("No changes detected.")


tabs = st.tabs([
    "📋 Load Board",
    "📥 OTR Imports",
    "📤 OTR Exports",
    "🚛 OTR Local Imports",
    "📁 Exported Files"
])
with tabs[0]:
    st.subheader("📋 Load Board")

    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        search_text = st.text_input(
            "Search Load Board",
            placeholder="Search Load ID, Customer, Driver, Status...",
            key="load_board_search"
        )

    with col2:
        status_filter = st.selectbox(
            "Status",
            ["All", "New", "Ready to Dispatch", "Assigned", "Picked Up", "Delivered", "Hold / Need Info", "Exported"],
            key="load_board_status"
        )

    with col3:
        st.write("")
        st.write("")
        search_button = st.button("🔍 Search", key="load_board_search_btn")

    filtered_df = filter_table(load_board_df, search_text, status_filter)
    st.dataframe(filtered_df, use_container_width=True)


with tabs[1]:
    st.subheader("📥 OTR Imports")

    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        search_text = st.text_input(
            "Search OTR Imports",
            placeholder="Search customer, file name, load ID...",
            key="otr_import_search"
        )

    with col2:
        status_filter = st.selectbox(
            "Status",
            ["All", "New", "Ready to Import", "Imported", "Needs Review", "Error", "Duplicate"],
            key="otr_import_status"
        )

    with col3:
        st.write("")
        st.write("")
        search_button = st.button("🔍 Search", key="otr_import_search_btn")

    filtered_df = filter_table(otr_imports_df, search_text, status_filter)
    st.dataframe(filtered_df, use_container_width=True)


with tabs[2]:
    st.subheader("📤 OTR Exports")

    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        search_text = st.text_input(
            "Search OTR Exports",
            placeholder="Search export file, customer, status...",
            key="otr_export_search"
        )

    with col2:
        status_filter = st.selectbox(
            "Status",
            ["All", "New", "Ready to Export", "Exported", "Failed Export", "Needs Review"],
            key="otr_export_status"
        )

    with col3:
        st.write("")
        st.write("")
        search_button = st.button("🔍 Search", key="otr_export_search_btn")

    filtered_df = filter_table(otr_exports_df, search_text, status_filter)
    st.dataframe(filtered_df, use_container_width=True)


with tabs[3]:
    st.subheader("🚛 OTR Local Imports")

    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        search_text = st.text_input(
            "Search OTR Local Imports",
            placeholder="Search local import, customer, load ID...",
            key="otr_local_import_search"
        )

    with col2:
        status_filter = st.selectbox(
            "Status",
            ["All", "New", "Ready to Import", "Imported", "Needs Review", "Error"],
            key="otr_local_import_status"
        )

    with col3:
        st.write("")
        st.write("")
        search_button = st.button("🔍 Search", key="otr_local_import_search_btn")

    filtered_df = filter_table(otr_local_imports_df, search_text, status_filter)
    st.dataframe(filtered_df, use_container_width=True)


with tabs[4]:
    st.subheader("📁 Exported Files")

    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        search_text = st.text_input(
            "Search Exported Files",
            placeholder="Search file name, date, status...",
            key="exported_files_search"
        )

    with col2:
        status_filter = st.selectbox(
            "Status",
            ["All", "Generated", "Sent to ProfitTools", "Sent to QuickBooks", "Failed", "Archived"],
            key="exported_files_status"
        )

    with col3:
        st.write("")
        st.write("")
        search_button = st.button("🔍 Search", key="exported_files_search_btn")

    filtered_df = filter_table(exported_files_df, search_text, status_filter)
    st.dataframe(filtered_df, use_container_width=True)

st.markdown("""
<div class="footer-band">
🇨🇴 Orgullosamente Colombianos · Calitrans Dispatch Center
</div>
""", unsafe_allow_html=True)