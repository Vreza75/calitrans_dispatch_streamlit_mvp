from __future__ import annotations

import os
import tempfile
from typing import Any, Dict, List
from urllib import response

import pandas as pd
import smartsheet
from smartsheet.models import Cell, Row

from config import SMARTSHEET_ACCESS_TOKEN, SMARTSHEET_DISPATCH_SHEET_ID, EDITABLE_COLUMNS


class DispatchSmartsheetClient:
    def __init__(self) -> None:
        if not SMARTSHEET_ACCESS_TOKEN:
            raise RuntimeError("Missing SMARTSHEET_ACCESS_TOKEN in .env")
        if not SMARTSHEET_DISPATCH_SHEET_ID:
            raise RuntimeError("Missing SMARTSHEET_DISPATCH_SHEET_ID in .env")

        self.client = smartsheet.Smartsheet(SMARTSHEET_ACCESS_TOKEN)
        self.client.errors_as_exceptions(True)
        self.sheet_id = SMARTSHEET_DISPATCH_SHEET_ID
        self.access_token = SMARTSHEET_ACCESS_TOKEN

    def get_sheet(self):
        return self.client.Sheets.get_sheet(self.sheet_id)

    def get_column_lookup(self, sheet=None) -> Dict[str, int]:
        sheet = sheet or self.get_sheet()
        return {col.title: col.id for col in sheet.columns}

    def rows_to_dataframe(self, sheet=None) -> pd.DataFrame:
        sheet = sheet or self.get_sheet()
        columns_by_id = {col.id: col.title for col in sheet.columns}

        records: List[Dict[str, Any]] = []
        for row in sheet.rows:
            record: Dict[str, Any] = {"_row_id": row.id}
            for cell in row.cells:
                column_name = columns_by_id.get(cell.column_id)
                if column_name:
                    record[column_name] = cell.value
            records.append(record)

        return pd.DataFrame(records)

    def update_row_fields(self, row_id: int, updates: Dict[str, Any]) -> None:
        column_lookup = self.get_column_lookup()

        invalid = [column for column in updates if column not in EDITABLE_COLUMNS]
        if invalid:
            raise ValueError(f"Columns not allowed to update from app: {invalid}")

        cells = []
        for column_name, value in updates.items():
            column_id = column_lookup.get(column_name)
            if not column_id:
                raise ValueError(f"Column not found in Smartsheet: {column_name}")
            cells.append(Cell({"column_id": column_id, "value": value}))

        updated_row = Row()
        updated_row.id = row_id
        updated_row.cells = cells

        self.client.Sheets.update_rows(self.sheet_id, [updated_row])
    def attach_file_to_row(self, row_id, uploaded_file):
        import requests

        url = f"https://api.smartsheet.com/2.0/sheets/{self.sheet_id}/rows/{row_id}/attachments"

        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type or "application/pdf"
            )
        }

        response = requests.post(url, headers=headers, files=files)

        if response.status_code not in [200, 201]:
            raise Exception(f"Attachment upload failed: {response.status_code} - {response.text}")

        return response.json()

    def add_row(self, row_data: dict):
        sheet = self.get_sheet()

        column_map = {
            column.title: column.id
            for column in sheet.columns
    }

        cells = []

        for column_name, value in row_data.items():
            if column_name not in column_map:
                continue

            if value is None or str(value).strip() == "":
                continue

            cells.append({
            "columnId": column_map[column_name],
            "value": str(value)
        })

        new_row = {
            "toBottom": True,
            "cells": cells
    }

        response = self.client.Sheets.add_rows(
            self.sheet_id,
            [new_row]
           
    )
        created_row = response.result[0]
        return created_row.id

        