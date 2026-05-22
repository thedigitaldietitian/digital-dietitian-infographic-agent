# Digital Dietitian Infographic Agent

Autonomous low FODMAP infographic content agent for The Digital Dietitian.

This repository contains a simple Python agent for "Build your..." low FODMAP
infographic content ops.

v1 generates the content package, QA summary, image-generation prompt, caption,
SEO keywords and suggested schedule. It can print the package in dry-run mode or
append it to the Google Sheet after Google OAuth desktop authentication.

v2 reads one completed infographic content package from the Google Sheet,
generates the final image with the OpenAI API, saves it locally in `outputs/`,
optionally uploads it to Google Drive, and writes image/status fields back to the
Sheet.

It does not schedule to Buffer.

## Project Structure

```text
.
├── main.py
├── requirements.txt
├── .env.example
├── prompts/
│   └── build_your_infographic.md
└── src/
    ├── agent.py
    ├── config.py
    ├── google_workspace.py
    ├── image_generation.py
    └── models.py
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

The default `.env.example` already contains the Google Sheet, SOP Doc and Drive
folder IDs used by the agent.

Add your OpenAI API key to `.env` before running v2 image generation:

```text
OPENAI_API_KEY=your_key_here
```

Keep `.env`, `token.json`, `credentials/` and generated images out of git.

## Usage

Preview the generated package without writing to Google Sheets:

```bash
python main.py --dry-run
```

Append the generated package to the Content Calendar tab:

```bash
python main.py
```

Preview the latest eligible Sheet row for v2 without generating an image or
writing back to the Sheet:

```bash
python main.py --generate-image --dry-run
```

Generate the image, save it in `outputs/`, upload it to Google Drive if
configured, and write the result back to the Sheet:

```bash
python main.py --generate-image
```

Generate and save the image locally without uploading to Drive:

```bash
python main.py --generate-image --skip-drive-upload
```

## v2 Image Generation Behaviour

v2 reads the latest eligible row in the Content Calendar tab where:

- `Format` contains `Infographic`
- `Draft Text` and `Design Prompt` are present
- `Image Asset Link`, `Local Image Path` and `Google Drive Image Link` are empty

The image prompt is built from the existing content package in the Sheet. It
preserves the 4 column names, 5 row labels and 4 x 5 ingredient matrix generated
by v1.

Generated images are saved to:

```text
outputs/{POST_ID}.png
```

The final local file is resized/cropped to 1080 x 1350 px. The OpenAI generation
size defaults to `1024x1536` because the final exact 4:5 sizing is handled after
generation by Pillow.

If Drive upload succeeds, the agent writes the Drive link back to the Sheet. If
Drive upload is skipped, it writes the local image path.

v2 updates these fields:

- `Image Asset Link`
- `Local Image Path`
- `Google Drive Image Link`
- `Image Generation Status`
- `Visual QA`
- `Human Review Needed`
- `Next Action`
- `Ready for Buffer`
- `Buffer Status`

If those v2-specific columns do not exist yet, the agent adds them to the header
row.

## Approved Visual Style

The v2 image prompt enforces the approved "Build your..." template direction for
Aleks Jagiello BSc (Hons), MSc, RD, The Digital Dietitian /
`@ibs.gutdietitian`:

- 4:5 ratio, final output 1080 x 1350 px
- exactly 4 columns
- exactly 5 rows
- soft blush background
- Open Sans-style typography
- only these brand colours: `#1d3b2a`, `#ff9cb7`, `#ffe78b`, `#fff8d9`,
  `#f9fff3`, `#e2efcc`, `#fff3f6`
- required text: `BUILD YOUR`, `BLOAT-FREE`, `SAVE IT FOR LATER`,
  `@ibs.gutdietitian`
- matrix format only
- realistic food visuals in each cell
- no Buffer scheduling

## Visual QA

v2 performs a basic deterministic QA check on the content package before writing
the final status:

- 4 columns present
- 5 rows present
- 4 x 5 ingredient matrix present
- handle present in the prompt
- save badge present in the prompt
- `BLOAT-FREE` headline present in the prompt
- approved matrix style requested

Because image OCR/layout verification is not implemented yet, successful v2
runs are marked `PASS WITH HUMAN REVIEW` and `Human Review Needed` remains
`Yes`. A person should confirm the generated image visually matches the approved
template before any later Buffer scheduling workflow.

## Credentials

The agent uses Google OAuth desktop authentication. It does not use service
account JSON keys.

1. In Google Cloud Console, create or select a project.
2. Enable the Google Sheets API, Google Docs API and Google Drive API.
3. Configure the OAuth consent screen for your Google account.
4. Create an OAuth client ID with application type `Desktop app`.
5. Download the client JSON file.
6. Create a local credentials folder:

```bash
mkdir -p credentials
```

7. Save the downloaded OAuth client JSON as:

```text
credentials/oauth_client.json
```

8. Confirm `.env` contains:

```text
GOOGLE_OAUTH_CLIENT_FILE=credentials/oauth_client.json
GOOGLE_TOKEN_FILE=token.json
```

9. Run the agent:

```bash
python main.py
```

On the first run, a browser window opens for Google login and consent. After
consent, the local OAuth token is stored in `token.json` so future runs can
reuse or refresh it.

Both `credentials/oauth_client.json` and `token.json` are ignored by git and must
never be committed. If you previously authenticated v1 before Drive upload was
added, you may need to delete `token.json` locally and rerun the agent so Google
can ask for the new Drive upload permission.

## Status

v1 remains intentionally small and deterministic. v2 adds image generation and
Drive/Sheet write-back. Buffer scheduling is intentionally not implemented yet.
