import os
from dotenv import load_dotenv

load_dotenv()

SMARTSHEET_ACCESS_TOKEN = os.getenv("SMARTSHEET_ACCESS_TOKEN")
SMARTSHEET_DISPATCH_SHEET_ID = os.getenv("SMARTSHEET_DISPATCH_SHEET_ID")

# Update these names to exactly match your Smartsheet columns.
COLUMN_MAP = {
    "load_id": "Load#",
    "customer": "Customer",
    "pickup": "Pickup",
    "delivery": "Delivery",
    "status": "Status",
    "driver": "Driver",
    "truck": "Truck",
    "trailer": "Container Number",
    "dispatcher_notes": "Dispatcher Notes",
    
}

# Only these columns are allowed to be changed from the app.
EDITABLE_COLUMNS = [
    "Status",
    "Driver",
    "Truck",
    "Trailer",
    "Container Number",
    "Dispatcher Notes",
    
    
]

ACTIVE_STATUSES = [
    "Open",
    "Assigned",
    "Dispatched",
    "In Transit",
    "At Pickup",
    "At Delivery",
    "Hold",
]
