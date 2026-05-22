# Digital Dietitian Infographic Agent

Python agent for creating image-ready "Build your..." low FODMAP infographic
packages for The Digital Dietitian / `@ibs.gutdietitian`.

The current production workflow is:

1. Use this agent to create a clinically checked, image-ready content package.
2. Use the generated image prompt from that package to create the final artwork
   separately in ChatGPT.
3. Add the final approved image link back to the Google Sheet.
4. Keep `Ready for Buffer` as `No` until final visual review and QA are complete.

This agent should not be treated as the final visual designer at this stage. The
Python renderer and OpenAI full-image generation paths are useful experiments,
but they are not final artwork unless Aleks visually approves the output.

Buffer scheduling is not implemented yet.

## Current Workflow

The agent creates one image-ready "Build your..." low FODMAP infographic package
and can append it to the Google Sheet.

The package includes:

- post metadata
- 4 column names
- 5 row labels
- a 4 x 5 ingredient matrix
- caption
- SEO keywords
- source/evidence notes
- clinical, food pairing and brand QA notes
- a detailed prompt for ChatGPT image generation
- `Ready for Buffer = No`

The final infographic image should then be generated separately in ChatGPT using
the `Design Prompt` / image-generation prompt from the Sheet row.

Do not mark `Ready for Buffer = Yes` until:

- the final image has been generated separately in ChatGPT
- Aleks has visually checked the final image
- the final image link has been added to the Google Sheet
- caption and QA are complete

## Why the Workflow Changed

Early v2 experiments tried two local visual approaches:

- full-image OpenAI generation from Python
- deterministic Pillow template rendering

These were useful for testing, but the generated visuals still need human visual
judgment. Full-image generation can distort text or crop the layout. The Python
renderer can create readable structured drafts, but it is still not the approved
final visual design system.

For now, the safest production split is:

- Codex/Python creates the image-ready package and prompt.
- ChatGPT image generation creates the final image.
- Aleks visually approves the image before Buffer readiness.

## Main Usage: Generate an Image-Ready Package

Preview the generated package without writing to Google Sheets:

```bash
python main.py --dry-run
```

Append the generated package to the Content Calendar tab:

```bash
python main.py
```

The normal package-generation run does not generate a final image and does not
schedule to Buffer.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

The default `.env.example` contains the Google Sheet, SOP Doc and Drive folder
IDs used by the agent. Adjust these only if the workspace changes.

Keep these files and folders out of git:

- `.env`
- `token.json`
- `credentials/`
- `outputs/`
- generated PNGs
- generated food assets in `assets/food/`

## Project Structure

```text
.
├── main.py
├── requirements.txt
├── .env.example
├── assets/
│   └── food_asset_map.json
├── prompts/
│   └── build_your_infographic.md
└── src/
    ├── agent.py
    ├── config.py
    ├── food_assets.py
    ├── google_workspace.py
    ├── image_generation.py
    ├── template_renderer.py
    └── models.py
```

## Template Modes: choice_row and column_combo

The image-ready package can describe two "Build your..." structures:

- `choice_row`: each row is a category and each row contains 4 options. This is
  best for bowl-style posts, snack plates and row-based choice matrices.
- `column_combo`: each column is a complete meal combination. This is best for
  sandwich, wrap, lunchbox or meal-combo posts.

These modes are primarily content/planning structures. The final visual should
still be generated separately in ChatGPT and checked by Aleks.

## Prompt for ChatGPT Image Generation Requirements

Use the package's image-generation prompt as the starting point in ChatGPT.

The final image prompt should preserve:

- 4:5 Instagram ratio, ideally 1080 x 1350
- exactly 4 column names
- exactly 5 row labels
- exactly 4 x 5 ingredient matrix
- low FODMAP logic and portion notes
- `BUILD YOUR`
- `BLOAT-FREE`
- `SAVE IT FOR LATER`
- `@ibs.gutdietitian`
- Aleks Jagiello BSc (Hons), MSc, RD / The Digital Dietitian brand context
- Open Sans-style typography
- only these brand colours:
  - `#1d3b2a`
  - `#ff9cb7`
  - `#ffe78b`
  - `#fff8d9`
  - `#f9fff3`
  - `#e2efcc`
  - `#fff3f6`

The final ChatGPT image should be checked manually for:

- readable text
- no misspellings
- no cropped headings or footer
- correct matrix structure
- realistic food visuals
- no off-brand colours
- no unsupported health claims

## QA Rules

The agent can generate package-level QA notes, but human review is still
required before publishing.

Keep `Ready for Buffer = No` until all of the following are true:

- final artwork has been generated separately in ChatGPT
- final artwork has been visually checked by Aleks
- final image link has been added to the Google Sheet
- caption is complete
- clinical QA is complete
- food pairing QA is complete
- brand QA is complete
- visual QA is complete

If the image is still only a local Python render, OpenAI full-image experiment,
or unreviewed ChatGPT output, keep:

```text
Human Review Needed = Yes
Ready for Buffer = No
Buffer Status = Not scheduled
```

## Optional/Experimental Image Generation

These commands are kept for testing and comparison. They are not the production
final-artwork workflow unless Aleks explicitly approves the resulting image.

Preview the latest eligible Sheet row for v2 without generating an image or
writing back to the Sheet:

```bash
python main.py --generate-image --dry-run
```

Generate a full image from Python with the OpenAI image API:

```bash
python main.py --generate-image
```

Generate and save locally without uploading to Drive:

```bash
python main.py --generate-image --skip-drive-upload
```

Render a deterministic local template draft:

```bash
python main.py --render-template --row-id INFO-2026-004
```

Choose a deterministic template layout mode:

```bash
python main.py --render-template --row-id INFO-2026-004 --layout-mode choice_row
python main.py --render-template --row-id INFO-2026-004 --layout-mode column_combo
```

Preview a template render without creating an image or writing to the Sheet:

```bash
python main.py --render-template --row-id INFO-2026-004 --dry-run
```

Generate missing reusable food cutout assets for the experimental renderer:

```bash
python main.py --render-template --row-id INFO-2026-004 --generate-missing-assets
```

Generated local files are saved under `outputs/` and `assets/food/`, both of
which are ignored by git.

### Experimental Food Assets

The optional deterministic renderer can use reusable local food assets:

```text
assets/food/
```

The mapping file is version-controlled:

```text
assets/food_asset_map.json
```

Generated food assets should not be committed unless the project later decides
to version-control a curated approved asset library.

## Credentials

The agent uses Google OAuth desktop authentication. It does not use service
account JSON keys.

1. In Google Cloud Console, create or select a project.
2. Enable the Google Sheets API and Google Docs API.
3. If testing Drive upload experiments, also enable the Google Drive API.
4. Configure the OAuth consent screen for your Google account.
5. Create an OAuth client ID with application type `Desktop app`.
6. Download the client JSON file.
7. Create a local credentials folder:

```bash
mkdir -p credentials
```

8. Save the downloaded OAuth client JSON as:

```text
credentials/oauth_client.json
```

9. Confirm `.env` contains:

```text
GOOGLE_OAUTH_CLIENT_FILE=credentials/oauth_client.json
GOOGLE_TOKEN_FILE=token.json
```

10. Run the agent:

```bash
python main.py
```

On the first run, a browser window opens for Google login and consent. After
consent, the local OAuth token is stored in `token.json` so future runs can
reuse or refresh it.

Both `credentials/oauth_client.json` and `token.json` are ignored by git and must
never be committed.

## Status

Production-ready today:

- image-ready package generation
- Google Sheet append
- package-level caption, prompt and QA fields

Experimental only:

- Python OpenAI full-image generation
- deterministic Pillow renderer
- generated local food assets
- Drive upload from local render/image experiments

Not implemented:

- Buffer scheduling
- automatic final visual approval
- automatic `Ready for Buffer = Yes`

The intended production workflow is package first, final artwork second, human
review before Buffer readiness.
