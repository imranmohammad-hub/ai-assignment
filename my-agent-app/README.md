# Project Setup Running `main.py`

This document explains how to set up and run the conversational AI agent defined in `main.py` (the file you provided). It intentionally **does not use a virtual environment** — all instructions use the system or user-level `pip` installation. Follow the sections below to configure logging (Logfire), Google "flash"/Gemini model access, and optional Context7 MCP server access.

---

## 1. Overview

`main.py` is a simple console-based agent runner that:

* Instantiates a `pydantic_ai.Agent` with a system prompt.
* Registers a handful of helper tools using `@agent.tool_plain`.
* Uses `logfire` to instrument/tracing/logging.
* Optionally talks to a Context7 MCP server (if configured).
* Uses a model identifier `google-gla:gemini-2.5-flash` in the code; to call Google generative models you must correctly configure Google Cloud credentials.

This setup guide shows how to install dependencies without a virtual environment and how to configure the environment variables the script expects.

---

## 2. Prerequisites

Before you begin, ensure the following are installed on your machine:

* Python 3.10 or newer (verify with `python --version`)
* `pip` (Python package manager)
* Access/permissions to install packages with `pip --user` or system-wide
* A terminal/console for running commands

---

## 3. Install Python dependencies (no virtual environment)

Run the following commands to install required packages using `pip` without creating a virtual environment.

```bash
# Recommended: use pip with --user to avoid needing sudo
python -m pip install --user pydantic-ai logfire python-dotenv requests pytz

# If you prefer system-wide installation (requires privileges):
# python -m pip install pydantic-ai logfire python-dotenv requests pytz
```

> Notes:
>
> * `pydantic-ai` is the agent library used in the example.
> * `logfire` is used for instrumentation. If you already have a logging/instrumentation service you can adapt the calls in `main.py`.
> * `python-dotenv` is used to load environment variables from a `.env` file.

---

## 4. Environment configuration

`main.py` loads a simple `.env` file using `python-dotenv`.
You only need the following keys:

```
CONTEXT7_API_KEY=xyz12345apikey
CONTEXT7_MCP_URL=http://localhost:3000
GOOGLE_API_KEY=AIzaSyCEHZsmWmQO8iXcBXDscXr3XIfCqyxoyf0
```

No additional environment variables are required.

### Logfire Setup (Command Line Only)

If you want Logfire active, set it directly in your terminal before running the script:

**Linux / macOS:**

```bash
export LOGFIRE_API_KEY=your_logfire_key_here
```

**Windows (PowerShell):**

```powershell
$env:LOGFIRE_API_KEY="your_logfire_key_here"
```

---

## 5. Logfire setup

`main.py` calls `logfire.configure()` and `logfire.instrument_pydantic_ai()` early during startup. To make logging useful you should:

1. Install and configure `logfire` (already installed via `pip`).
2. Provide an API key or DSN if your Logfire instance requires authentication. The code expects `logfire.configure()` to work without arguments; if your deployment needs a key, set it via environment variable (e.g. `LOGFIRE_API_KEY`) and change the `main.py` call to pass it into `logfire.configure()` if required.

Example minimal `.env` keys for Logfire:

```
LOGFIRE_API_KEY=your_logfire_key_here
```

If you are not using a hosted Logfire service, `logfire.configure()` will still initialize the client locally; check the library docs for running it in offline or local modes.

---

## 6. Google Flash / Gemini model setup

The code uses `model = "google-gla:gemini-2.5-flash"`. To successfully call Google generative models you generally need to do the following steps (high-level):

1. **Create a Google Cloud project** and enable the Vertex AI (or Generative AI) API for that project.
2. **Create a service account** with the required IAM roles (for Vertex AI or the generative models API).
3. **Create and download the service account key** (JSON file).
4. **Set `GOOGLE_APPLICATION_CREDENTIALS`** to the path of the downloaded JSON key (this is how Google SDKs authenticate).

Example of setting the environment variable on Linux/macOS:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/your-service-account.json"
```

Windows (PowerShell):

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\your-service-account.json"
```

Additional hints:

* Make sure the service account has permissions to call Vertex AI / the generative API.
* If you choose a different approach (for example using a hosted API key or a separate SDK), adapt `main.py` so the agent's underlying client library picks up whatever auth method you prefer.
* If you are using a third-party wrapper (or `pydantic-ai` expects other environment variables), consult that library's docs to ensure the runtime looks for the same variables.

---

## 7. Optional: Context7 MCP server

`main.py` includes a `context7_fetch_docs` tool that POSTs to `CONTEXT7_MCP_URL` (default `http://localhost:3000`). If you want this tool to work:

* Run or install your Context7 MCP server and set `CONTEXT7_MCP_URL` in `.env` to the server base URL.
* If the server requires a bearer token, set `CONTEXT7_API_KEY` in `.env`.

If you do not have Context7 running you can leave these blank — the tool will simply return a connection error if invoked.

---

## 8. Run the agent (console)

Once dependencies and environment variables are configured, run the agent like this from the project directory:

```bash
python main.py
```

Expected behaviour:

* The script will print a prompt `You: ` in the console.
* Type messages and press Enter; the agent will respond.
* Type `exit`, `quit`, or `bye` to stop the loop and end the program.

---

## 9. Troubleshooting

**Common issues and fixes**

* `ModuleNotFoundError` for a package: Make sure you installed packages with the same Python you use to run the script. Example:

  ```bash
  python -m pip install --user pydantic-ai
  python main.py
  ```

* Google auth errors (e.g., `DefaultCredentialsError`): Ensure `GOOGLE_APPLICATION_CREDENTIALS` points to a valid JSON service account key and that the key has proper permissions.

* `requests` connection errors to Context7: Check `CONTEXT7_MCP_URL` and the server's status; try `curl` or `http` to confirm the endpoint is reachable.

* `logfire.configure()` no-op or missing configuration: If your `logfire` installation expects configuration parameters, supply them either via environment variables or by updating `main.py` to call `logfire.configure(api_key=...)`.

---

## 10. Security & Best Practices

* Never commit `.env` or service-account JSON files to version control.
* Limit the service account permissions to only what is needed to call the generative APIs.
* Rotate keys regularly and store secrets in a secrets manager for production systems.

---

## 11. Example minimal `.env` (recap)

```
CONTEXT7_MCP_URL=http://localhost:3000
CONTEXT7_API_KEY=
LOGFIRE_API_KEY=
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
```
