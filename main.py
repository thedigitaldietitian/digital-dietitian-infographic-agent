"""Command-line entry point for the infographic content agent."""

import argparse
import json
import os

from src.agent import build_content_package
from src.config import Settings
from src.google_workspace import GoogleWorkspaceClient
from src.image_generation import (
    OUTPUT_HEADERS,
    build_final_image_prompt,
    dry_run_summary,
    find_infographic_row_by_post_id,
    find_latest_eligible_infographic_row,
    generate_infographic_image,
    run_basic_visual_qa,
)
from src.template_renderer import render_infographic_template

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
        "--generate-image",
        action="store_true",
        help="Run v2: generate an image for the latest eligible infographic row.",
    )
    parser.add_argument(
        "--render-template",
        action="store_true",
        help="Run v2.1: render a deterministic template PNG from an existing row.",
    )
    parser.add_argument(
        "--row-id",
        help="Post ID to use with --render-template, for example INFO-2026-004.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview work without creating images or writing to Google Sheets.",
    )
    parser.add_argument(
        "--skip-drive-upload",
        action="store_true",
        help="Save the generated image locally but do not upload it to Google Drive.",
    )
    return parser.parse_args()


def main() -> None:
    """Generate the content package and optionally append it to Google Sheets."""
    load_dotenv()
    args = parse_args()
    settings = Settings.from_env()

    workspace = GoogleWorkspaceClient(settings)
    if args.generate_image:
        run_image_generation(settings, workspace, args)
        return
    if args.render_template:
        run_template_render(settings, workspace, args)
        return

    recent_rows = workspace.get_recent_calendar_rows() if workspace.can_connect else []
    package = build_content_package(settings=settings, recent_rows=recent_rows)

    if args.dry_run:
        print(json.dumps(package.to_sheet_dict(), indent=2, ensure_ascii=False))
        return

    workspace.append_content_calendar_row(package.to_sheet_dict())
    print(f"Added {package.post_id} to the Content Calendar.")


def run_image_generation(
    settings: Settings,
    workspace: GoogleWorkspaceClient,
    args: argparse.Namespace,
) -> None:
    """Generate the final image for the latest eligible completed package."""
    if not workspace.can_connect:
        raise RuntimeError(
            "Google credentials were not found. Add credentials/oauth_client.json "
            "or token.json before running --generate-image."
        )

    _, rows = workspace.get_content_calendar_rows_with_numbers()
    package = find_latest_eligible_infographic_row(rows)
    if package is None:
        print("No eligible infographic rows found without an image.")
        return

    prompt = build_final_image_prompt(settings, package)
    if args.dry_run:
        print(json.dumps(dry_run_summary(package, prompt), indent=2, ensure_ascii=False))
        return

    if not os.getenv("OPENAI_API_KEY"):
        workspace.update_content_calendar_row(
            package.row_number,
            {
                "Image Generation Status": "FAILED - missing OPENAI_API_KEY",
                "Visual QA": "NOT RUN - image generation did not start.",
                "Human Review Needed": "Yes",
                "Next Action": "Add OPENAI_API_KEY to the local environment and rerun v2.",
                "Ready for Buffer": "No",
                "Buffer Status": "Not scheduled",
            },
        )
        raise RuntimeError("OPENAI_API_KEY is required for image generation.")

    workspace.ensure_content_calendar_headers(OUTPUT_HEADERS)
    workspace.update_content_calendar_row(
        package.row_number,
        {
            "Image Generation Status": "IN PROGRESS",
            "Visual QA": "NOT RUN - image generation in progress.",
            "Human Review Needed": "Yes",
            "Next Action": "Generate image, upload if configured, then run visual QA.",
            "Ready for Buffer": "No",
            "Buffer Status": "Not scheduled",
        },
    )

    drive_link = ""
    try:
        local_image_path = generate_infographic_image(
            settings=settings,
            prompt=prompt,
            post_id=package.post_id,
        )

        if not args.skip_drive_upload:
            drive_link = workspace.upload_image_to_drive(
                image_path=local_image_path,
                file_name=f"{package.post_id}.png",
            )

        qa_result = run_basic_visual_qa(package)
        image_asset_link = drive_link or local_image_path
        workspace.update_content_calendar_row(
            package.row_number,
            {
                "Image Asset Link": image_asset_link,
                "Local Image Path": local_image_path,
                "Google Drive Image Link": drive_link,
                "Image Generation Status": "DONE",
                "Visual QA": qa_result.to_sheet_text(),
                "Human Review Needed": qa_result.human_review_needed,
                "Next Action": qa_result.next_action,
                "Ready for Buffer": "No",
                "Buffer Status": "Not scheduled",
            },
        )
        print(f"Generated image for {package.post_id}: {local_image_path}")
        if drive_link:
            print(f"Uploaded to Drive: {drive_link}")
        print("Buffer scheduling was not run.")
    except Exception as exc:
        workspace.update_content_calendar_row(
            package.row_number,
            {
                "Image Generation Status": "FAILED",
                "Visual QA": "NOT RUN - image generation or upload failed.",
                "Human Review Needed": "Yes",
                "Next Action": f"Fix v2 error and rerun image generation: {exc}",
                "Ready for Buffer": "No",
                "Buffer Status": "Not scheduled",
            },
        )
        raise


def run_template_render(
    settings: Settings,
    workspace: GoogleWorkspaceClient,
    args: argparse.Namespace,
) -> None:
    """Render a deterministic v2.1 template image from an existing Sheet row."""
    if not args.row_id:
        raise RuntimeError("--row-id is required with --render-template.")
    if not workspace.can_connect:
        raise RuntimeError(
            "Google credentials were not found. Add credentials/oauth_client.json "
            "or token.json before running --render-template."
        )

    workspace.ensure_content_calendar_headers(OUTPUT_HEADERS)
    _, rows = workspace.get_content_calendar_rows_with_numbers()
    package = find_infographic_row_by_post_id(rows, args.row_id)
    if package is None:
        raise RuntimeError(f"No Content Calendar row found for {args.row_id}.")

    if args.dry_run:
        print(
            json.dumps(
                {
                    "row_number": package.row_number,
                    "post_id": package.post_id,
                    "columns": package.columns,
                    "rows": package.rows,
                    "matrix": package.matrix,
                    "would_render": f"{settings.output_dir}/{package.post_id}-rendered.png",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    local_image_path = render_infographic_template(settings, package)
    drive_link = ""
    drive_note = ""
    if not args.skip_drive_upload:
        try:
            drive_link = workspace.upload_image_to_drive(
                image_path=local_image_path,
                file_name=f"{package.post_id}-rendered.png",
            )
        except Exception:
            drive_note = " Drive upload failed due insufficient OAuth scopes."

    image_asset_link = drive_link or local_image_path
    workspace.update_content_calendar_row(
        package.row_number,
        {
            "Image Asset Link": image_asset_link,
            "Local Image Path": local_image_path,
            "Google Drive Image Link": drive_link,
            "Image Generation Status": "DONE - rendered locally",
            "Visual QA": (
                "NEEDS HUMAN REVIEW - deterministic 1080x1350 template rendered "
                "from Sheet text with exact 4 columns and 5 rows. Placeholder food "
                f"tiles used until approved food assets are available.{drive_note}"
            ),
            "Human Review Needed": "Yes",
            "Next Action": (
                "Aleks to review the rendered template image for brand/layout fit "
                "before Buffer scheduling."
            ),
            "Ready for Buffer": "No",
            "Buffer Status": "Not scheduled",
        },
    )

    print(f"Rendered template for {package.post_id}: {local_image_path}")
    if drive_link:
        print(f"Uploaded to Drive: {drive_link}")
    elif drive_note:
        print("Drive upload failed; local path was written to the Sheet.")
    print("Buffer scheduling was not run.")


if __name__ == "__main__":
    main()
