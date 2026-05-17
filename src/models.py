"""Data models used by the infographic content agent."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ContentPackage:
    """One complete content package for the Google Sheet."""

    post_id: str
    week_commencing: str
    post_date: str
    post_time: str
    platform: str
    format: str
    content_pillar: str
    topic: str
    objective: str
    cta_offer: str
    risk_level: str
    draft_text: str
    caption: str
    seo_keywords: str
    design_prompt: str
    image_asset_link: str
    source_notes: str
    clinical_qa: str
    food_pairing_qa: str
    brand_qa: str
    visual_qa: str
    human_review_needed: str
    ready_for_buffer: str
    buffer_channel_id: str
    buffer_status: str
    buffer_post_id: str

    def to_sheet_dict(self) -> dict[str, str]:
        """Return values keyed by the Content Calendar headers."""
        return {
            "Post ID": self.post_id,
            "Week Commencing": self.week_commencing,
            "Post Date": self.post_date,
            "Post Time": self.post_time,
            "Platform": self.platform,
            "Format": self.format,
            "Content Pillar": self.content_pillar,
            "Topic / Hook": self.topic,
            "Post Objective": self.objective,
            "CTA / Offer": self.cta_offer,
            "Risk Level": self.risk_level,
            "Draft Text": self.draft_text,
            "Caption": self.caption,
            "SEO Keywords": self.seo_keywords,
            "Design Prompt": self.design_prompt,
            "Image Asset Link": self.image_asset_link,
            "Source / Evidence Notes": self.source_notes,
            "Clinical QA": self.clinical_qa,
            "Food Pairing QA": self.food_pairing_qa,
            "Brand QA": self.brand_qa,
            "Visual QA": self.visual_qa,
            "Human Review Needed": self.human_review_needed,
            "Ready for Buffer": self.ready_for_buffer,
            "Buffer Channel ID": self.buffer_channel_id,
            "Buffer Status": self.buffer_status,
            "Buffer Post ID": self.buffer_post_id,
        }
