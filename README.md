# 🚀 OpsInsight

**OpsInsight** is a supercharged, beginner-friendly Command Line Interface (CLI) that automatically runs your code and instantly acts as a friendly AI tutor if your program crashes. 

No more confusing compiler commands. No more copying and pasting stack traces into a browser window. OpsInsight does it all right from your terminal!

## ✨ Features

- **🪄 Zero-Config Execution**: Just type `ops <filename>`. Whether it's Python, C++, C, JavaScript, or Java, OpsInsight automatically handles compiling and running it.
- **🤖 Friendly AI Debugging**: If your script crashes, OpsInsight captures the error and feeds it to a Gemini-powered AI tutor that explains *why* it broke in simple, jargon-free English.
- **🛠️ Auto-Fix Capabilities**: OpsInsight's AI can actually see your project workspace. If you hit a tricky bug, the AI might even ask you for permission to apply the fix directly to your file!
- **⌨️ Fully Interactive**: OpsInsight behaves exactly like a native terminal. Your scripts that wait for `input()` or `cin` will work perfectly without hanging.

## 🛠️ Prerequisites

- Python 3.8+
- A Google Gemini API Key (you can get one for free from Google AI Studio).

## 📦 Installation

To install OpsInsight globally on your computer so you can use the `ops` command anywhere, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/gaurav-sha56/opsinsight-v1.git
   cd opsinsight-v1
   ```

2. **Install the package via pip:**
   ```bash
   pip install .
   ```
   *(This automatically installs all required dependencies like `google-genai`.)*

3. **Configure your API Key:**
   Run the following command anywhere on your computer. It will ask you for your Google Gemini API key and save it securely.
   ```bash
   ops start
   ```
   
4. **(Optional) Initialize a Workspace:**
   Navigate to your coding folder and run:
   ```bash
   ops init
   ```
   This scopes the directory as an OpsInsight workspace and drops a starter template file for you to test!

## 🎮 How to Use

To use OpsInsight, replace your standard `python` or `g++` commands with `ops`!

```bash
ops main.cpp
ops script.py
```

If it works perfectly, it runs exactly like normal.
If it crashes... grab some popcorn and let OpsInsight explain the traceback! 🍿

---

> **Note:** OpsInsight is designed specifically with beginners in mind to make learning to code a smoother, less frustrating experience. Happy coding!
