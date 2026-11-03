# 🚀 OpsInsight

**OpsInsight** is a supercharged, beginner-friendly Command Line Interface (CLI) that automatically runs your code and instantly acts as a friendly AI tutor if your program crashes. 

No more confusing compiler commands. No more copying and pasting stack traces into a browser window. OpsInsight does it all right from your terminal!

---

## ✨ Features

- **🪄 Zero-Config Execution**: Just type `ops <filename>`. Whether it's Python, C++, C, JavaScript, or Java, OpsInsight automatically handles compiling and running it across Linux, macOS, and Windows.
- **🤖 Multi-Provider AI Brain**: Powered by **LiteLLM**, OpsInsight supports **OpenAI**, **Anthropic**, **Groq**, **Ollama** (offline local models), **Google Gemini**, and custom **OpenAI-compatible** endpoints (LM Studio, vLLM, OpenRouter, etc.).
- **🛠️ Auto-Fix Capabilities**: OpsInsight's AI can inspect workspace files and ask for permission (`[y/N]`) to apply fixes directly to your code!
- **⚙️ Flexible Configuration**: Easily manage settings globally or per-project using dotenv-style `.ops.config` files with seamless per-key merging.
- **🔒 Built-In Security**: API keys are always masked in terminal outputs, global configuration files are secured with `600` permissions on Unix/macOS, and local project `.ops.config` files are automatically added to `.gitignore`.
- **⌨️ Fully Interactive**: Native terminal pass-through so scripts waiting for `input()` or `cin` work naturally without hanging.

---

## 🛠️ Prerequisites

- Python 3.8+ (Linux, macOS, or Windows)
- An API key or local model endpoint for your preferred provider:
  - **Google Gemini**: Get one from [Google AI Studio](https://aistudio.google.com/app/apikey)
  - **OpenAI**: [platform.openai.com](https://platform.openai.com)
  - **Anthropic**: [console.anthropic.com](https://console.anthropic.com)
  - **Groq**: [console.groq.com](https://console.groq.com)
  - **Ollama (Local)**: [ollama.ai](https://ollama.ai) (Free, offline, no API key required, runs via `ollama serve`)
  - **Ollama Cloud**: [docs.ollama.com/cloud](https://docs.ollama.com/cloud) (Hosted models via API key at `https://ollama.com/v1`)
  - **OpenAI-Compatible**: Any custom server (e.g. LocalAI, vLLM, LM Studio)

---

## 📦 Installation

To install OpsInsight globally on your computer so you can use the `ops` command anywhere:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/gaurav-sha56/opsinsight-v1.git
   cd opsinsight-v1
   ```

2. **Install the package:**
   ```bash
   pip install .
   ```

---

## ⚙️ Configuration & Commands

OpsInsight includes an interactive setup wizard and a full configuration management system.

### 1. `ops start` (Global Setup Wizard)
Run `ops start` anywhere on your computer for first-time global setup. The interactive wizard will prompt you for:
- Your preferred LLM provider (`gemini`, `openai`, `anthropic`, `groq`, `ollama`, `ollama-cloud`, or `openai-compatible`)
- Suggested model (or custom model name)
- API Key (secure hidden input)
- Base URL (for Ollama or OpenAI-compatible custom endpoints)

```bash
ops start
```
This saves your global configuration securely at `~/.opsinsight/.ops.config` with user-only read/write permissions (`600`).

---

### 2. `ops init` (Local Project Workspace Initialization)
Run `ops init` in your project folder:
```bash
ops init
```
- Prompts whether you want project-specific provider, model, or API key configurations in `.ops.config`.
- **Automatic Git Protection**: Automatically creates or updates your `.gitignore` to prevent committing `.ops.config` containing API keys.


---

### 3. `ops config` (Interactive Settings & Subcommands)

#### Interactive Arrow-Key Menu
Running `ops config` without arguments opens an interactive terminal menu:
```bash
ops config
```
```text
? What do you want to do?
> Change provider
  Change model
  Change API key
  Change API base URL (Ollama / custom endpoints)
  View current config
  Exit
```
For every change, you can choose whether to apply it **Globally (all projects)** or **Locally (this project only)**.

#### Scriptable Direct Subcommands
For scripting or non-interactive environments:

| Subcommand | Description |
|------------|-------------|
| `ops config list` | Displays all settings, active values, masked keys, and source tags (`(env)`, `(local)`, `(global)`) |
| `ops config get <KEY>` | Retrieves the active value for a configuration key (e.g., `ops config get OPS_MODEL`) |
| `ops config set <KEY> <VALUE> [--local]` | Sets a configuration value globally (or locally with `--local`) |
| `ops config set OPS_API_KEY [--local]` | Securely enters an API key via hidden prompt (never passed as plain CLI arguments) |
| `ops config path` | Displays absolute file paths for local and global configuration files |

---

## 📑 Configuration Resolution & Priority

OpsInsight resolves configuration values on a **per-key basis** using the following hierarchy:

$$\text{Environment Variable} > \text{Local } .ops.config \text{ (CWD)} > \text{Global Config } (\sim/.opsinsight/.ops.config)$$

### Per-Key Fallback Example
If your global configuration defines:
```dotenv
OPS_PROVIDER=gemini
OPS_MODEL=gemini-2.5-flash
OPS_API_KEY=AIzaSy...
```
And your current project directory has a local `.ops.config` containing only:
```dotenv
OPS_MODEL=gemini-1.5-pro
```
OpsInsight will use `OPS_MODEL=gemini-1.5-pro` (from local) while seamlessly falling back to `OPS_PROVIDER=gemini` and `OPS_API_KEY=AIzaSy...` (from global).

### Supported Configuration Keys
- `OPS_PROVIDER`: `gemini`, `openai`, `anthropic`, `groq`, `ollama`, `ollama-cloud`, or `openai-compatible`
- `OPS_MODEL`: Model identifier (e.g., `gemini-2.5-flash`, `gpt-4o-mini`, `claude-3-5-haiku-20241022`, `llama-3.3-70b-versatile`, `llama3.2`)
- `OPS_API_KEY`: Provider API key (automatically masked when displayed)
- `OPS_API_BASE`: API base URL for Ollama local (default `http://localhost:11434`), Ollama Cloud (default `https://ollama.com/v1`), or custom OpenAI-compatible endpoints

---

## 🔒 Security Best Practices

> [!WARNING]
> Never commit `.ops.config` or API keys to version control!
> `ops init` automatically adds `.ops.config` to your `.gitignore`. If you create `.ops.config` manually, ensure it is listed in your project's `.gitignore`.

- **Key Masking**: API keys are always masked (e.g., `sk-p****cdef`) when displayed on the console.
- **Hidden Input**: API keys are never accepted as raw command-line arguments to prevent exposing them in your shell history (`history` / `bash_history`).
- **File Permissions**: Global configuration files are restricted to `600` permissions on Linux and macOS.

---

## 🎮 How to Use

Replace your standard `python` or `g++` commands with `ops`:

```bash
ops main.cpp
ops script.py
ops app.js
```

- If your code runs successfully, stdout is displayed natively in real-time.
- If your code crashes with a compile error, runtime exception, or segmentation fault, OpsInsight's AI brain activates:
  1. Explains the root cause in simple, beginner-friendly terms.
  2. Inspects workspace files using tools.
  3. Prompts: `Allow this change? [y/N]` before applying any code fixes.
  4. Keeps the conversation open so you can ask follow-up questions!

---

## 🧪 Testing

OpsInsight includes an automated test suite verifying cross-platform config resolution, security masking, validation, and AI brain routing:

```bash
uv run pytest
```
Or with verbose output:
```bash
uv run pytest -v
```


---

Happy debugging with OpsInsight! 🍿
