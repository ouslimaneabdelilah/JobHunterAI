# Automatic Application System

This tool automates the process of finding internship/job opportunities, filtering them using AI, and applying via email.

## Features

1.  **Scrape**: Finds companies on Google Maps (e.g., "Web Agency" in "Casablanca").
2.  **Filter**: Uses advanced AI (Meta Llama 4, DeepSeek V3, GPT-5) to verify if the company is a Tech/Development Agency.
3.  **Validate**: Checks existing Excel/CSV lists and cleans them using AI.
4.  **Apply**: Generates custom PDF cover letters and sends emails automatically.

## Prerequisites

### 1. GitHub Token (For AI Models)

This system uses **GitHub Models** (Free Usage).

1.  Go to [GitHub Marketplace Models](https://github.com/marketplace/models).
2.  Click "Get started for free" or "Get your token".
3.  Create a **Personal Access Token (classic)** or **Fine-grained token**.
    - Ensure it has `read:models` or general read permissions if asked.
    - Copy the token (starts with `ghp_` or `github_pat_`).

### 2. Email Password (Gmail)

To send emails securely:

1.  Go to your Google Account > Security.
2.  Enable **2-Step Verification**.
3.  Search for **App Passwords**.
4.  Create a new app password (name it "Scraper").
5.  Copy the 16-character code (e.g., `abcd efgh ijkl mnop`).

## Installation

1.  **Install Python** (3.10+ recommended).
2.  **Install Dependencies**:
    The system will automatically try to install libraries on first run. To do it manually:

    ```bash
    pip install -r requirements.txt
    ```

    (requires `install.py` logic or manual `pip install azure-ai-inference azure-core pandas selenium webdriver-manager beautifulsoup4 python-dotenv pypdf openpyxl`)

3.  **Setup Environment**:
    Create a `.env` file in this folder:

    ```env
    # AI Config
    GITHUB_TOKEN=your_github_token_here_ghp_xxxx

    # Email Config
    EMAIL_ADDRESS=your_email@gmail.com
    EMAIL_PASSWORD=your_app_password_here

    # Resume
    RESUME_PATH=resume.pdf
    ```

## Usage

Run the program:

```bash
python main.py
```

### AI Model Selection

When you start the app, you will be asked to choose an AI model:

- **1. Meta Llama 4** (`meta/Llama-4-Scout-17B-16E-Instruct`) - Balanced & Fast.
- **2. DeepSeek V3** (`deepseek/DeepSeek-V3-0324`) - High reasoning capability.
- **3. GPT-5** (`openai/gpt-5`) - Experimental/Preview.
- **4. Custom**: Enter any other model ID available on GitHub Models.

### Menu Options

1.  **Scrape & Filter**:
    - Enter City & Keyword.
    - Browser opens to scrape Google Maps.
    - **Press Ctrl+C** to stop scraping anytime.
    - AI filters results and finds emails on websites.
2.  **Validate External Excel/CSV**:
    - Select a file you already have.
    - AI validates each row and removes non-tech companies.
3.  **Apply**:
    - Select a filtered file.
    - Generates PDF letter + Sends Email with CV attached.

## Troubleshooting

- **Chrome Error**: Ensure Chrome is installed.
- **Email Fail**: Check `EMAIL_PASSWORD`. It must be an App Password, not your login password.
- **AI Error**: Check `GITHUB_TOKEN`. Ensure you have access to GitHub Models.
