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
    "Local Image Path",
    "Google Drive Image Link",
    "Image Generation Status",
    "Next Action",
]


class GoogleWorkspaceClient:
    """Reads context from Google Workspace and appends rows to Sheets."""

    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/documents.readonly",
    ]
    DRIVE_SCOPES = SCOPES + ["https://www.googleapis.com/auth/drive.file"]

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._sheets = None
        self._docs = None
        self._drive = None
        self.can_connect = self._credentials_available()

    def _credentials_available(self) -> bool:
        """Check whether OAuth files are available for a real Google run."""
        return os.path.exists(self.settings.google_oauth_client_file) or os.path.exists(
            self.settings.google_token_file
        )

    def _get_credentials(self, scopes: list[str] | None = None):
        """Load, refresh, or create desktop OAuth credentials."""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        scopes = scopes or self.SCOPES
        credentials = None
        token_file = self.settings.google_token_file
        client_file = self.settings.google_oauth_client_file

        if os.path.exists(token_file):
            credentials = Credentials.from_authorized_user_file(
                token_file,
                scopes,
            )

        if credentials and not credentials.has_scopes(scopes):
            credentials = None

        if credentials and credentials.valid:
            return credentials

        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not os.path.exists(client_file):
                raise FileNotFoundError(
                    "Google OAuth client file not found. Expected "
                    f"{client_file}. Create a desktop OAuth client in Google "
                    "Cloud Console and save the downloaded JSON there."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                client_file,
                scopes,
            )
            credentials = flow.run_local_server(port=0)

        token_dir = os.path.dirname(token_file)
        if token_dir:
            os.makedirs(token_dir, exist_ok=True)

        with open(token_file, "w", encoding="utf-8") as token:
            token.write(credentials.to_json())

        return credentials

    def _get_sheets_service(self):
        """Create the Google Sheets API client lazily."""
        from googleapiclient.discovery import build

        if self._sheets is None:
            credentials = self._get_credentials()
            self._sheets = build("sheets", "v4", credentials=credentials)
        return self._sheets

    def _get_docs_service(self):
        """Create the Google Docs API client lazily."""
        from googleapiclient.discovery import build

        if self._docs is None:
            credentials = self._get_credentials()
            self._docs = build("docs", "v1", credentials=credentials)
        return self._docs

    def _get_drive_service(self):
        """Create the Google Drive API client lazily."""
        from googleapiclient.discovery import build

        if self._drive is None:
            credentials = self._get_credentials(self.DRIVE_SCOPES)
            self._drive = build("drive", "v3", credentials=credentials)
        return self._drive

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
                    range=f"{self.settings.sheet_tab}!A1:AD500",
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

    def get_content_calendar_rows_with_numbers(self) -> tuple[list[str], list[dict[str, str]]]:
        """Read Content Calendar rows and include their 1-based Sheet row number."""
        if not self.can_connect:
            return [], []

        result = (
            self._get_sheets_service()
            .spreadsheets()
            .values()
            .get(
                spreadsheetId=self.settings.sheet_id,
                range=f"{self.settings.sheet_tab}!A1:AD500",
            )
            .execute()
        )
        values = result.get("values", [])
        if not values:
            return [], []

        headers = values[0]
        rows = []
        for sheet_row_number, row in enumerate(values[1:], start=2):
            mapped_row = {
                headers[index]: value
                for index, value in enumerate(row)
                if index < len(headers)
            }
            mapped_row["_sheet_row_number"] = str(sheet_row_number)
            rows.append(mapped_row)
        return headers, rows

    def append_content_calendar_row(self, row: dict[str, str]) -> None:
        """Append one generated package to the Content Calendar tab."""
        values = [[row.get(header, "") for header in CONTENT_CALENDAR_HEADERS]]
        self._get_sheets_service().spreadsheets().values().append(
            spreadsheetId=self.settings.sheet_id,
            range=f"{self.settings.sheet_tab}!A:AD",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute()

    def ensure_content_calendar_headers(self, required_headers: list[str]) -> list[str]:
        """Append missing Content Calendar headers and return the full header row."""
        service = self._get_sheets_service()
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=self.settings.sheet_id,
                range=f"{self.settings.sheet_tab}!A1:AD1",
            )
            .execute()
        )
        headers = result.get("values", [[]])[0]
        missing_headers = [header for header in required_headers if header not in headers]
        if not missing_headers:
            return headers

        updated_headers = headers + missing_headers
        service.spreadsheets().values().update(
            spreadsheetId=self.settings.sheet_id,
            range=f"{self.settings.sheet_tab}!A1",
            valueInputOption="USER_ENTERED",
            body={"values": [updated_headers]},
        ).execute()
        return updated_headers

    def update_content_calendar_row(
        self,
        row_number: int,
        updates: dict[str, str],
    ) -> None:
        """Update selected Content Calendar cells by header name."""
        headers = self.ensure_content_calendar_headers(list(updates.keys()))

        data = []
        for header, value in updates.items():
            column = column_number_to_letters(headers.index(header) + 1)
            data.append(
                {
                    "range": f"{self.settings.sheet_tab}!{column}{row_number}",
                    "values": [[value]],
                }
            )

        self._get_sheets_service().spreadsheets().values().batchUpdate(
            spreadsheetId=self.settings.sheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": data},
        ).execute()

    def upload_image_to_drive(self, image_path: str, file_name: str) -> str:
        """Upload an image to Google Drive and return a shareable link."""
        from googleapiclient.http import MediaFileUpload

        metadata = {"name": file_name}
        if self.settings.drive_upload_folder_id:
            metadata["parents"] = [self.settings.drive_upload_folder_id]

        media = MediaFileUpload(image_path, mimetype="image/png", resumable=False)
        file = (
            self._get_drive_service()
            .files()
            .create(
                body=metadata,
                media_body=media,
                fields="id, webViewLink",
            )
            .execute()
        )
        return file.get("webViewLink", "")


def column_number_to_letters(column_number: int) -> str:
    """Convert a 1-based column number to A1 notation letters."""
    letters = ""
    while column_number:
        column_number, remainder = divmod(column_number - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters
