# Calitrans Dispatch Streamlit MVP

Internal dispatch dashboard that reads from Smartsheet and writes controlled updates back to Smartsheet, so dispatchers do not need to edit the main sheet directly.

## Phase 1 Features

- Read active loads from Smartsheet
- Display dispatch dashboard in Streamlit
- Filter by status, driver, and ready-for-export flag
- Update selected fields back to Smartsheet
- Export ready loads to CSV for ProfitTools workflow

## Setup

1. Create a Smartsheet API token.
2. Copy `.env.example` to `.env`.
3. Fill in:
   - `SMARTSHEET_ACCESS_TOKEN`
   - `SMARTSHEET_DISPATCH_SHEET_ID`
4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Run:

```bash
streamlit run app.py
```

## Safe Update Model

The app only updates fields listed in `config.py` under `EDITABLE_COLUMNS`.
This prevents accidental changes to key accounting, load, or customer fields.
