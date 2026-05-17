"""Command-line entry point for the infographic content agent."""

import argparse
import json

from src.agent import build_content_package
from src.config import Settings
from src.google_workspace import GoogleWorkspaceClient

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> None:
        """Allow dry-run mode before dependencies are installed."""
        return None


def parse_args() -> argparse.Namespace:
    """Read simple command-line options for local testing."""
    parser = argparse.ArgumentParser(
        description="Generate one low FODMAP infographic content package."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated package without writing to Google Sheets.",
    )
    return parser.parse_args()


def main() -> None:
    """Generate the content package and optionally append it to Google Sheets."""
    load_dotenv()
    args = parse_args()
    settings = Settings.from_env()

    workspace = GoogleWorkspaceClient(settings)
    recent_rows = workspace.get_recent_calendar_rows() if workspace.can_connect else []
    package = build_content_package(settings=settings, recent_rows=recent_rows)

    if args.dry_run:
        print(json.dumps(package.to_sheet_dict(), indent=2, ensure_ascii=False))
        return

    workspace.append_content_calendar_row(package.to_sheet_dict())
    print(f"Added {package.post_id} to the Content Calendar.")


if __name__ == "__main__":
    main()
