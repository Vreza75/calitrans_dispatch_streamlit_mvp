from pathlib import Path
from urllib.parse import quote, unquote
import base64
import pandas as pd
import streamlit as st

from smartsheet_client import DispatchSmartsheetClient


st.set_page_config(
    page_title="Calitrans Dispatch Center",
    page_icon="🚚",
    layout="wide",
)


# -----------------------------
# Helpers
# -----------------------------

def load_css():
    css_path = Path("theme.css")
    if css_path.exists():
        st.markdown(css_path.read_text(encoding="utf-8"), unsafe_allow_html=True)


def image_to_base64(path: str) -> str:
    file_path = Path(path)
    if not file_path.exists():
        return ""
    return base64.b64encode(file_path.read_bytes()).decode("utf-8")


@st.cache_data(ttl=60)
def load_dispatch_data() -> pd.DataFrame:
    client = DispatchSmartsheetClient()
    sheet = client.get_sheet()
    return client.rows_to_dataframe(sheet)


def refresh_data():
    st.cache_data.clear()


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()

    for col in required_columns:
        if col not in df.columns:
            df[col] = None

    df["TYPE"] = df["TYPE"].astype(str).str.strip()
    df["Status"] = df["Status"].astype(str).str.strip()
    df["Booking Number"] = df["Booking Number"].astype(str).str.strip()

    return df


def filter_table(df, search_text="", status_filter="All"):
    filtered = df.copy()

    if status_filter != "All" and "Status" in filtered.columns:
        filtered = filtered[filtered["Status"].astype(str).str.strip() == status_filter]

    if search_text:
        search_text = search_text.lower()
        filtered = filtered[
            filtered.astype(str)
            .apply(lambda row: row.str.lower().str.contains(search_text).any(), axis=1)
        ]

    return filtered


def normalize_type(value):
    return (
        str(value)
        .strip()
        .lower()
        .replace("exports", "export")
        .replace("imports", "import")
    )


def get_type_rows(df, type_name):
    if "TYPE" not in df.columns:
        return df.iloc[0:0]

    normalized_type = df["TYPE"].apply(normalize_type)
    target = normalize_type(type_name)

    return df[normalized_type == target]


def get_booking_summary(data: pd.DataFrame):
    data = data.copy()

    date_col = "Date" if "Date" in data.columns else "Created Date"

    if date_col in data.columns:
        data["Date"] = data[date_col]
        data = data.sort_values("Date")

    data["Booking Number"] = data["Booking Number"].astype(str).str.strip()
    data = data[data["Booking Number"] != ""]
    data = data[data["Booking Number"].str.lower() != "none"]

    if data.empty:
        return pd.DataFrame(columns=summary_columns)

    summary = (
        data.groupby("Booking Number", as_index=False)
        .agg({
            "Date": "first",
            "Customer": "first",
            "Warehouse": "first",
            "Reference Number": "first",
        })
    )

    return summary[[col for col in summary_columns if col in summary.columns]]


def show_booking_summary(data: pd.DataFrame, title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)

    summary_df = get_booking_summary(data)

    if summary_df.empty:
        st.info("No bookings found.")
        return

    header = st.columns([1.2, 1.5, 2, 2, 1.5])
    header[0].markdown("**Date**")
    header[1].markdown("**Booking #**")
    header[2].markdown("**Customer**")
    header[3].markdown("**Warehouse**")
    header[4].markdown("**Reference #**")

    for _, row in summary_df.iterrows():
        booking = str(row["Booking Number"])
        current_tab = st.session_state.get("current_tab", "load_board")
        booking_url = f"?booking={quote(booking)}&tab={current_tab}"

        col1, col2, col3, col4, col5 = st.columns([1.2, 1.5, 2, 2, 1.5])

        col1.write(row.get("Date", ""))
        col2.markdown(
            f'<a href="{booking_url}">{booking}</a>',
            unsafe_allow_html=True,
        )
        col3.write(row.get("Customer", ""))
        col4.write(row.get("Warehouse", ""))
        col5.write(row.get("Reference Number", ""))


def save_day_changes(original_df, edited_df, editable_columns):
    client = DispatchSmartsheetClient()
    changes_saved = 0

    original = original_df.reset_index(drop=True)
    edited = edited_df.reset_index(drop=True)

    for i in range(len(edited)):
        row_id = int(original.loc[i, "_row_id"])
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

    return changes_saved


# -----------------------------
# Column Config
# -----------------------------

summary_columns = [
    "Date",
    "Booking Number",
    "Customer",
    "Warehouse",
    "Reference Number",
]

detail_columns = [
    "Date",
    "Delivery Need Date",
    "Container Number",
    "Warehouse",
    "Address",
    "Status",
    "LFD",
    "Driver",
    "Truck #",
    "Chassis",
    "Size",
    "Booking Number",
    "Billing Notes",
    "Dispatcher Notes",
]

editable_day_columns = [
    "Status",
    "Driver",
    "Truck #",
    "Chassis",
    "Dispatcher Notes",
]

day_display_columns = [
    "Date",
    "Delivery Need Date",
    "Container Number",
    "Warehouse",
    "Status",
    "LFD",
    "Driver",
    "Truck #",
    "Chassis",
    "Size",
    "Booking Number",
    "Dispatcher Notes",
]

required_columns = list(set(
    summary_columns
    + detail_columns
    + editable_day_columns
    + [
        "_row_id",
        "TYPE",
        "Load ID",
        "Customer",
        "Reference Number",
        "Port",
        "Document Cutoff",
        "Created Date",
    ]
))

otr_status_options = [
    "New",
    "Hold/Need Info",
    "Ready to Dispatch",
    "Assigned",
    "En Route to Pickup",
    "At Pickup",
    "Loaded",
    "En Route To Delivery",
    "Delivered",
    "POD Received",
    "Ready for ProfitTools",
    "Exported to ProfitTools",
    "Invoiced",
    "Closed",
    "Cancelled",
    "Returning Empty",
]


# -----------------------------
# Load Page Assets
# -----------------------------

load_css()

banner_b64 = image_to_base64("assets/header_banner.png")

if banner_b64:
    st.markdown(
        f"""
        <div class="banner-wrapper">
            <img class="header-banner" src="data:image/png;base64,{banner_b64}" />
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------
# Load Smartsheet Data
# -----------------------------

try:
    df = load_dispatch_data()
except Exception as exc:
    st.error(f"Could not load Smartsheet data: {exc}")
    st.stop()

if df.empty:
    st.warning("No rows found in the dispatch sheet.")
    st.stop()

df = clean_df(df)


# -----------------------------
# Booking Detail Page
# -----------------------------

selected_booking = st.query_params.get("booking", None)

if selected_booking:
    selected_booking = unquote(str(selected_booking))

    booking_df = df[
        df["Booking Number"]
        .astype(str)
        .str.strip()
        .eq(selected_booking.strip())
    ].copy()

    main_customer = (
        booking_df["Customer"].dropna().astype(str).iloc[0]
        if not booking_df.empty and "Customer" in booking_df.columns
        else ""
    )

    st.markdown("<div style='margin-top:-35px'></div>", unsafe_allow_html=True)
    st.markdown(f"### Main Customer: {main_customer}")
    st.title(f"📦 Booking Details: {selected_booking}")

    delivery_col = "Delivery Need Date"

    if delivery_col not in booking_df.columns:
        st.warning("Missing Smartsheet column: Delivery Need Date")
    else:
        booking_df[delivery_col] = pd.to_datetime(
            booking_df[delivery_col],
            errors="coerce",
        )

        delivery_dates = (
            booking_df[delivery_col]
            .dropna()
            .sort_values()
            .dt.date
            .unique()
        )

        st.markdown("### 📅 Weekly Live Status")

        if len(delivery_dates) == 0:
            st.info("No delivery need dates found for this booking.")
        else:
            delivery_tabs = st.tabs([
                pd.to_datetime(d).strftime("%A %B %d")
                for d in delivery_dates
            ])

            for tab, delivery_date in zip(delivery_tabs, delivery_dates):
                with tab:
                    day_df = booking_df[
                        booking_df[delivery_col].dt.date == delivery_date
                    ].copy()

                    if day_df.empty:
                        st.info("No loads for this day.")
                        continue

                    visible_day_columns = [
                        col for col in day_display_columns
                        if col in day_df.columns
                    ]

                    edited_day = st.data_editor(
                        day_df[visible_day_columns],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Status": st.column_config.SelectboxColumn(
                                "Status",
                                options=otr_status_options,
                            )
                        },
                        disabled=[
                            col for col in visible_day_columns
                            if col not in editable_day_columns
                        ],
                        key=f"day_editor_{delivery_date}",
                        height=330,
                    )

                    if st.button(
                        f"💾 Save {pd.to_datetime(delivery_date).strftime('%A %B %d')} Changes",
                        key=f"save_day_{delivery_date}",
                    ):
                        changes_saved = save_day_changes(
                            day_df,
                            edited_day,
                            editable_day_columns,
                        )

                        if changes_saved:
                            st.success(f"Saved {changes_saved} change(s).")
                            refresh_data()
                            st.rerun()
                        else:
                            st.info("No changes detected.")

    return_tab = st.query_params.get("tab", "load_board")

   

    if return_tab:
        st.info(f"Returned from booking detail. Open tab: {return_tab.replace('_', ' ').title()}")
    if st.button("⬅ Back to Dashboard"):
        st.query_params.clear()
        st.query_params["tab"] = return_tab
        st.rerun()

    st.stop()


# -----------------------------
# KPI Cards
# -----------------------------

active_statuses = [
    "Ready to Dispatch",
    "Assigned",
    "En Route to Pickup",
    "Hold/Need Info",
]

active_count = len(df[df["Status"].isin(active_statuses)])
ready_count = len(df[df["Status"] == "Ready to Dispatch"])
assigned_count = len(df[df["Status"] == "Assigned"])
hold_count = len(df[df["Status"] == "Hold/Need Info"])
exported_count = len(df[df["Status"] == "Exported to ProfitTools"])


def kpi_card(icon, label, value, sub, css_class):
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-icon {css_class}">{icon}</div>
          <div>
            <div class="kpi-label {css_class}">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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


# -----------------------------
# Main Tabs
# -----------------------------

tabs = st.tabs([
    "➕ New Load Entry",
    "📋 Load Board",
    "🚛 OTR Imports",
    "🚛 OTR Exports",
    "🚛 OTR Local Imports",
    "📋 Files to Export",
])


with tabs[0]:
    st.subheader("➕ New Load Entry")

    uploaded_file = st.file_uploader(
        "Upload Order PDF",
        type=["pdf"],
        key="new_load_pdf",
    )

    with st.form("new_load_form"):
        load_type = st.selectbox(
            "TYPE",
            ["OTR Import", "OTR Export", "OTR Local imports"],
        )

        customer = st.text_input("Customer")
        booking_number = st.text_input("Booking Number")
        container_number = st.text_input("Container Number")
        chassis = st.text_input("Chassis")
        port = st.text_input("Port")
        warehouse = st.text_input("Warehouse")
        document_cutoff = st.date_input("Document Cutoff")
        delivery_need_date = st.date_input("Delivery Need Date")
        notes = st.text_area("Dispatcher Notes")

        submitted = st.form_submit_button("Create Load")

    if submitted:
        new_row = {
            "TYPE": load_type,
            "Customer": customer,
            "Booking Number": booking_number,
            "Container Number": container_number,
            "Chassis": chassis,
            "Port": port,
            "Warehouse": warehouse,
            "Document Cutoff": str(document_cutoff),
            "Delivery Need Date": str(delivery_need_date),
            "Status": "New",
            "Dispatcher Notes": notes,
        }

        client = DispatchSmartsheetClient()
        row_id = client.add_row(new_row)

        if uploaded_file is not None:
            client.attach_file_to_row(row_id, uploaded_file)

        st.success("Load created.")
        refresh_data()
        st.rerun()


with tabs[1]:
    st.subheader("📋 Load Board")

    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        search_text = st.text_input(
            "Search Load Board",
            placeholder="Search Booking #, Customer, Warehouse, Status...",
            key="load_board_search",
        )

    with col2:
        status_filter = st.selectbox(
            "Status",
            ["All"] + otr_status_options,
            key="load_board_status",
        )

    with col3:
        st.write("")
        st.write("")
        st.button("🔍 Search", key="load_board_search_btn")
    st.session_state["current_tab"] = "load_board"
    filtered_df = filter_table(df, search_text, status_filter)
    show_booking_summary(filtered_df, "Load Board")


with tabs[2]:
    st.subheader("🚛 OTR Imports")

    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        search_text = st.text_input(
            "Search OTR Imports",
            placeholder="Search Booking #, Customer, Warehouse...",
            key="otr_import_search",
        )

    with col2:
        status_filter = st.selectbox(
            "Status",
            ["All"] + otr_status_options,
            key="otr_import_status",
        )

    with col3:
        st.write("")
        st.write("")
        st.button("🔍 Search", key="otr_import_search_btn")
    st.session_state["current_tab"] = "otr_imports"
    otr_import_df = get_type_rows(df, "OTR Import")
    filtered_df = filter_table(otr_import_df, search_text, status_filter)
    show_booking_summary(filtered_df, "OTR Imports")


with tabs[3]:
    st.subheader("🚛 OTR Exports")

    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        search_text = st.text_input(
            "Search OTR Exports",
            placeholder="Search Booking #, Customer, Warehouse...",
            key="otr_export_search",
        )

    with col2:
        status_filter = st.selectbox(
            "Status",
            ["All"] + otr_status_options,
            key="otr_export_status",
        )

    with col3:
        st.write("")
        st.write("")
        st.button("🔍 Search", key="otr_export_search_btn")
    st.session_state["current_tab"] = "otr_exports"
    otr_export_df = get_type_rows(df, "OTR Export")
    filtered_df = filter_table(otr_export_df, search_text, status_filter)
    show_booking_summary(filtered_df, "OTR Exports")


with tabs[4]:
    st.subheader("🚛 OTR Local Imports")

    col1, col2, col3 = st.columns([3, 2, 1])

    with col1:
        search_text = st.text_input(
            "Search OTR Local Imports",
            placeholder="Search Booking #, Customer, Warehouse...",
            key="otr_local_import_search",
        )

    with col2:
        status_filter = st.selectbox(
            "Status",
            ["All"] + otr_status_options,
            key="otr_local_import_status",
        )

    with col3:
        st.write("")
        st.write("")
        st.button("🔍 Search", key="otr_local_import_search_btn")

    otr_local_import_df = get_type_rows(df, "OTR Local Import")
    filtered_df = filter_table(otr_local_import_df, search_text, status_filter)
    show_booking_summary(filtered_df, "OTR Local Imports")


with tabs[5]:
    st.subheader("📋 Files to Export")

    export_df = df[df["Status"] == "Ready for ProfitTools"].copy()

    show_booking_summary(export_df, "Files to Export")


st.markdown(
    """
    <div class="footer-band">
    🇨🇴 Orgullosamente Colombianos · Calitrans Dispatch Center
    </div>
    """,
    unsafe_allow_html=True,
)