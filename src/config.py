"""Configuration helpers for the infographic content agent."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    brand_name: str
    topic_focus: str
    instagram_handle: str
    sheet_id: str
    sheet_tab: str
    sop_document_id: str
    approved_examples_folder_id: str
    google_oauth_client_file: str
    google_token_file: str
    drive_upload_folder_id: str
    openai_image_model: str
    output_dir: str
    image_generation_size: str

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables with safe defaults."""
        return cls(
            brand_name=os.getenv("CONTENT_BRAND_NAME", "The Digital Dietitian"),
            topic_focus=os.getenv("CONTENT_TOPIC_FOCUS", "low FODMAP"),
            instagram_handle=os.getenv("INSTAGRAM_HANDLE", "@ibs.gutdietitian"),
            sheet_id=os.getenv(
                "GOOGLE_SHEET_ID",
                "1rArY65W7eapwNfNGNjGVQEZ01H78xJT2NJGkTMWpVl8",
            ),
            sheet_tab=os.getenv("GOOGLE_SHEET_TAB", "Content Calendar"),
            sop_document_id=os.getenv(
                "SOP_DOCUMENT_ID",
                "159HfNLG36jZgCbEFzr0EI2jy6_Sxovp9ahAE2e93ow0",
            ),
            approved_examples_folder_id=os.getenv(
                "APPROVED_EXAMPLES_FOLDER_ID",
                "1c8VeMvbiOrXtDzGGNlVWKlc4cknv1KpV",
            ),
            google_oauth_client_file=os.getenv(
                "GOOGLE_OAUTH_CLIENT_FILE",
                "credentials/oauth_client.json",
            ),
            google_token_file=os.getenv("GOOGLE_TOKEN_FILE", "token.json"),
            drive_upload_folder_id=os.getenv(
                "DRIVE_UPLOAD_FOLDER_ID",
                os.getenv("APPROVED_EXAMPLES_FOLDER_ID", ""),
            ),
            openai_image_model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1"),
            output_dir=os.getenv("OUTPUT_DIR", "outputs"),
            image_generation_size=os.getenv("IMAGE_GENERATION_SIZE", "1024x1536"),
        )
