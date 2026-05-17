# Digital Dietitian Infographic Agent

Autonomous low FODMAP infographic content agent for The Digital Dietitian.

This repository contains v1 of a simple Python agent that creates one
"Build your..." low FODMAP infographic content package for Instagram content ops.

v1 generates the content package, QA summary, image-generation prompt, caption,
SEO keywords and suggested schedule. It can print the package in dry-run mode or
append it to the Google Sheet after Google OAuth desktop authentication.

It does not schedule to Buffer and does not generate the final image.

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

## Usage

Preview the generated package without writing to Google Sheets:

```bash
python main.py --dry-run
```

Append the generated package to the Content Calendar tab:

```bash
python main.py
```

## Credentials

The agent uses Google OAuth desktop authentication. It does not use service
account JSON keys.

1. In Google Cloud Console, create or select a project.
2. Enable the Google Sheets API and Google Docs API.
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
never be committed.

## Status

v1 is intentionally small and deterministic. Future versions can add richer SOP
parsing, approved-example analysis, content variation, image generation and Buffer
scheduling.
