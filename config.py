import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

SMARTSHEET_ACCESS_TOKEN = os.getenv("SMARTSHEET_ACCESS_TOKEN") or st.secrets.get("SMARTSHEET_ACCESS_TOKEN")
SMARTSHEET_DISPATCH_SHEET_ID = os.getenv("SMARTSHEET_DISPATCH_SHEET_ID") or st.secrets.get("SMARTSHEET_DISPATCH_SHEET_ID")

COLUMN_MAP = {
    "load_id": "Load ID",
    "customer": "Customer",
    "pickup": "Pickup",
    "delivery": "Delivery",
    "status": "Status",
    "driver": "Driver",
    "truck": "Truck",
    "dispatcher_notes": "Dispatcher Notes",
}

EDITABLE_COLUMNS = [
    "Status",
    "Driver",
    "Truck",
    "Dispatcher Notes",
]

ACTIVE_STATUSES = [
    "Ready to Dispatch",
    "Assigned",
    "En Route to Pickup",
    "Hold/Need Info",
]