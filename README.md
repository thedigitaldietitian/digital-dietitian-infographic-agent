# Digital Dietitian Infographic Agent

Autonomous low FODMAP infographic content agent for The Digital Dietitian.

This repository contains v1 of a simple Python agent that creates one
"Build your..." low FODMAP infographic content package for Instagram content ops.

v1 generates the content package, QA summary, image-generation prompt, caption,
SEO keywords and suggested schedule. It can print the package in dry-run mode or
append it to the Google Sheet when Google credentials are configured.

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

Fill in `.env` with Google credentials. Do not commit `.env` or credential JSON
files.

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

The agent uses environment variables and Google Application Default Credentials.
For local use, set:

```bash
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
```

The credential file must not be committed to the repository.

## Status

v1 is intentionally small and deterministic. Future versions can add richer SOP
parsing, approved-example analysis, content variation, image generation and Buffer
scheduling.
