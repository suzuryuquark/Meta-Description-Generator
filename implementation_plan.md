# Implementation Plan - Meta Description Generator

## Goal Description
Create a Windows application that accepts a website URL, analyzes its content, and suggests 3 variations of meta descriptions. The user can select and copy their preferred option.

## User Review Required
> [!NOTE]
> **Gemini API Selected**: We will use `gemini-2.5-flash` as requested.
> **API Key**: The app will require a Google Gemini API Key. I will add a UI field to input this, or load it from a `.env` file for convenience.

## Proposed Tech Stack
- **Language**: Python
- **GUI Framework**: Flet
- **AI Model**: Google Gemini API (`gemini-2.5-flash`)
- **Scraping**: `requests`, `beautifulsoup4`

## Proposed Changes

### Core Application
#### [NEW] `main.py`
- **UI Components (Japanese)**:
    - `TextField`: "URLを入力してください"
    - `TextField`: "Gemini APIキー" (Password field)
    - `ElevatedButton`: "生成する" (Generate)
    - `Column`: Display 3 cards with results.
    - `IconButton`: Copy icon.
- **Logic**:
    - `fetch_content(url)`: Extracts text from `<p>`, `<h1>`, `<h2>`, `meta description`.
    - `generate_descriptions(text, api_key)`:
        - Uses `google.generativeai` library.
        - Prompt: "You are an SEO expert. Analyze the following text and generate 3 distinct, high-quality meta descriptions (approx 120 chars) in Japanese. Output in JSON format."

#### [NEW] `requirements.txt`
- `flet`
- `google-generativeai`
- `beautifulsoup4`
- `requests`

## Verification Plan
### Manual Verification
- Run the app locally (`flet run`).
- Input a known URL (e.g., a blog post or news article).
- Verify that 3 distinct descriptions are generated.
- Click "Copy" and verify the clipboard content.
