# AI Sales Qualification Agent

A prototype for the BarodaWeb AI Prompt Engineer assignment. This project uses Gemini to extract lead facts from a multi-turn conversation and uses deterministic Python rules to make the final qualification decision.

## Features in this milestone

- Streamlit chat interface for multi-turn lead intake
- Gemini structured output validated with Pydantic
- Lead details retained across turns when later extraction leaves fields blank
- Qualification settings adjustable in the sidebar: minimum budget and required fields
- Editable system-prompt settings: role, style, business criteria, and follow-up rules
- Deterministic statuses: `Qualified`, `Unqualified`, and `Needs More Information`
- Missing-information and contradiction display
- Structured JSON viewer and downloadable `lead_record.json`
- Safe, user-facing API error handling
- Automated tests for schemas, tool behavior, qualification rules, Gemini integration boundaries, and lead-state merging

## Requirements

- Python 3.11+
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/)

## Setup (Windows PowerShell)

Open this project folder in VS Code, then run:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell activation is blocked, use Command Prompt and run `.venv\Scripts\activate.bat`.

## Configure the Gemini API key

Create a file named `.env` in the same folder as `app.py` (the project root). Add:

```dotenv
GEMINI_API_KEY=your_actual_api_key_here
GEMINI_MODEL=gemini-3.8-flash
```

Replace the example key with your own key from Google AI Studio. Do not add quotes and do not share or commit your key. `.env` is excluded by `.gitignore`. If the configured model is unavailable to your account, choose a currently available Gemini model and update `GEMINI_MODEL`.

## Run the application

```powershell
streamlit run app.py
```

Streamlit should open the application in your browser. If it does not, open the local URL printed in the terminal. The chat input stays disabled until a Gemini API key is configured.

## Run tests

```powershell
python -m pytest -v
```

The test suite does not require a live Gemini API key. Unit tests use a fake client for provider calls; this does not prove that a live Gemini request will work with your API key, selected model, account quota, or network.

## Default business-rule settings

- Minimum budget: INR 50,000
- A contact method is required by default
- A timeline is required by default
- Project requirements are required by default
- Contradictions take precedence and require clarification
- Missing required details result in `Needs More Information`
- A tool failure never results in a fabricated eligibility claim

These are prototype defaults, not rules specified by BarodaWeb. They can be adjusted in the sidebar.

## Lead JSON fields

`customer_name`, `contact_details`, `requirements`, `budget`, `timeline`, `lead_status`, `missing_information`, `contradictions`, `reason`, and `tool_result`.

## Architecture

- `app.py`: Streamlit chat and lead summary UI
- `agent.py`: Gemini structured extraction and safe error handling
- `prompts.py`: system-prompt construction and prompt settings
- `schemas.py`: Pydantic models and validation
- `lead_state.py`: merges facts between conversation turns
- `qualification.py`: deterministic qualification rules
- `tools.py`: deterministic budget-eligibility tool
- `tests/`: automated tests

## Known limitations

- The budget eligibility tool is a local deterministic function, not an external CRM or sales service.
- Natural-language extraction and contradiction detection depend on the selected Gemini model; verify behavior with realistic test conversations before using this for real leads.
- This is a prototype. Do not treat its qualification result as a contractual or legally binding business decision.
