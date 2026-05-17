"""Small Google Docs and Sheets client used by the content agent."""

from __future__ import annotations

import os

from src.config import Settings


CONTENT_CALENDAR_HEADERS = [
    "Post ID",
    "Week Commencing",
    "Post Date",
    "Post Time",
    "Platform",
    "Format",
    "Content Pillar",
    "Topic / Hook",
    "Post Objective",
    "CTA / Offer",
    "Risk Level",
    "Draft Text",
    "Caption",
    "SEO Keywords",
    "Design Prompt",
    "Image Asset Link",
    "Source / Evidence Notes",
    "Clinical QA",
    "Food Pairing QA",
    "Brand QA",
    "Visual QA",
    "Human Review Needed",
    "Ready for Buffer",
    "Buffer Channel ID",
    "Buffer Status",
    "Buffer Post ID",
]


class GoogleWorkspaceClient:
    """Reads context from Google Workspace and appends rows to Sheets."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._sheets = None
        self._docs = None
        self.can_connect = self._credentials_available()

    def _credentials_available(self) -> bool:
        """Check whether Google credentials are likely available."""
        return bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")) or bool(
            os.getenv("GOOGLE_CLOUD_PROJECT")
        )

    def _get_sheets_service(self):
        """Create the Google Sheets API client lazily."""
        from google.auth import default
        from googleapiclient.discovery import build

        if self._sheets is None:
            credentials, _ = default(
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            self._sheets = build("sheets", "v4", credentials=credentials)
        return self._sheets

    def _get_docs_service(self):
        """Create the Google Docs API client lazily."""
        from google.auth import default
        from googleapiclient.discovery import build

        if self._docs is None:
            credentials, _ = default(
                scopes=["https://www.googleapis.com/auth/documents.readonly"]
            )
            self._docs = build("docs", "v1", credentials=credentials)
        return self._docs

    def read_sop_text(self) -> str:
        """Read the SOP Google Doc as plain text."""
        if not self.can_connect:
            return ""
        try:
            document = (
                self._get_docs_service()
                .documents()
                .get(documentId=self.settings.sop_document_id)
                .execute()
            )
        except Exception:
            return ""

        paragraphs = []
        for item in document.get("body", {}).get("content", []):
            paragraph = item.get("paragraph")
            if not paragraph:
                continue
            text = "".join(
                element.get("textRun", {}).get("content", "")
                for element in paragraph.get("elements", [])
            )
            if text.strip():
                paragraphs.append(text.strip())
        return "\n".join(paragraphs)

    def get_recent_calendar_rows(self) -> list[dict[str, str]]:
        """Read recent Content Calendar rows as dictionaries."""
        if not self.can_connect:
            return []
        try:
            result = (
                self._get_sheets_service()
                .spreadsheets()
                .values()
                .get(
                    spreadsheetId=self.settings.sheet_id,
                    range=f"{self.settings.sheet_tab}!A1:Z200",
                )
                .execute()
            )
        except Exception:
            return []

        values = result.get("values", [])
        if len(values) < 2:
            return []
        headers = values[0]
        return [
            {headers[index]: value for index, value in enumerate(row)}
            for row in values[1:]
        ]

    def append_content_calendar_row(self, row: dict[str, str]) -> None:
        """Append one generated package to the Content Calendar tab."""
        values = [[row.get(header, "") for header in CONTENT_CALENDAR_HEADERS]]
        self._get_sheets_service().spreadsheets().values().append(
            spreadsheetId=self.settings.sheet_id,
            range=f"{self.settings.sheet_tab}!A:Z",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute()
