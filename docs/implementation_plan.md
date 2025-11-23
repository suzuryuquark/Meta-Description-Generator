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

### Feature: Refinement
#### [MODIFY] `main.py`
- **UI Changes**:
    - Add a "修正して再生成" (Refine) button to each result card.
    - **Refinement Dialog**:
        - Displays the selected description.
        - `TextField`: "修正の指示（例：もっと短く、問いかけ調で）"
        - `ElevatedButton`: "再生成"
- **Logic Changes**:
    - `refine_description(original_desc, user_instruction, website_text)`:
        - Prompt: "Based on the website content and the original description, rewrite the description following this instruction: {user_instruction}"
        - Updates the specific card or shows a new result.

### Feature: Persistence & Usability
#### [MODIFY] `main.py`
- **Persistence**:
    - Use `page.client_storage` to store:
        - `gemini_api_key`
        - `global_instruction`
    - On `main` start, load these values into their respective TextFields.
    - On "Generate" click, save the current values to storage.
- **Global Instructions**:
    - Add `TextField`: "サイト共通の指示（例：トーン＆マナーなど）" above URL input.
    - Append this text to the system prompt.
- **Manual Editing**:
    - Replace `ListTile.subtitle` (Text) with `TextField(read_only=True, border=None, multiline=True)`.
    - Add "手動修正" (Edit) button (Icon: `EDIT`).
    - **Toggle Logic**:
        - Click Edit: `read_only=False`, `border=OUTLINE`, Icon=`CHECK`.
        - Click Done: `read_only=True`, `border=NONE`, Icon=`EDIT`, Update char count & copy data.

### System: Shortcut
- Create a PowerShell script or run a command to generate a `.lnk` file on the User's Desktop pointing to `pythonw.exe` (no console) executing `main.py`.

### Feature: URL Split & Icon
#### [MODIFY] `main.py`
- **UI Changes**:
    - Remove `url_input`.
    - Add `domain_input` (TextField, width=300, label="ドメイン (https://...)").
    - Add `path_input` (TextField, width=300, label="パス (/page/...)").
    - Place them in a `Row`.
- **Logic Changes**:
    - `url = domain_input.value.rstrip('/') + '/' + path_input.value.lstrip('/')`
    - Save `domain_input.value` to `client_storage` ("last_domain").
    - Load "last_domain" on startup.

#### [NEW] `assets/icon.png`
- Generate a modern, SEO/AI-themed icon using `generate_image`.
- Update `create_shortcut.ps1` to point `IconLocation` to this file (converted to .ico if possible, or just try .png). *Note: Windows shortcuts strictly require .ico for the image to show up, but we can try.*
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

### Feature: Refinement
#### [MODIFY] `main.py`
- **UI Changes**:
    - Add a "修正して再生成" (Refine) button to each result card.
    - **Refinement Dialog**:
        - Displays the selected description.
        - `TextField`: "修正の指示（例：もっと短く、問いかけ調で）"
        - `ElevatedButton`: "再生成"
- **Logic Changes**:
    - `refine_description(original_desc, user_instruction, website_text)`:
        - Prompt: "Based on the website content and the original description, rewrite the description following this instruction: {user_instruction}"
        - Updates the specific card or shows a new result.

### Feature: Persistence & Usability
#### [MODIFY] `main.py`
- **Persistence**:
    - Use `page.client_storage` to store:
        - `gemini_api_key`
        - `global_instruction`
    - On `main` start, load these values into their respective TextFields.
    - On "Generate" click, save the current values to storage.
- **Global Instructions**:
    - Add `TextField`: "サイト共通の指示（例：トーン＆マナーなど）" above URL input.
    - Append this text to the system prompt.
- **Manual Editing**:
    - Replace `ListTile.subtitle` (Text) with `TextField(read_only=True, border=None, multiline=True)`.
    - Add "手動修正" (Edit) button (Icon: `EDIT`).
    - **Toggle Logic**:
        - Click Edit: `read_only=False`, `border=OUTLINE`, Icon=`CHECK`.
        - Click Done: `read_only=True`, `border=NONE`, Icon=`EDIT`, Update char count & copy data.

### System: Shortcut
- Create a PowerShell script or run a command to generate a `.lnk` file on the User's Desktop pointing to `pythonw.exe` (no console) executing `main.py`.

### Feature: URL Split & Icon
#### [MODIFY] `main.py`
- **UI Changes**:
    - Remove `url_input`.
    - Add `domain_input` (TextField, width=300, label="ドメイン (https://...)").
    - Add `path_input` (TextField, width=300, label="パス (/page/...)").
    - Place them in a `Row`.
- **Logic Changes**:
    - `url = domain_input.value.rstrip('/') + '/' + path_input.value.lstrip('/')`
    - Save `domain_input.value` to `client_storage` ("last_domain").
    - Load "last_domain" on startup.

#### [NEW] `assets/icon.png`
- Generate a modern, SEO/AI-themed icon using `generate_image`.
- Update `create_shortcut.ps1` to point `IconLocation` to this file (converted to .ico if possible, or just try .png). *Note: Windows shortcuts strictly require .ico for the image to show up, but we can try.*
- Actually, for the shortcut, we might need to convert it. I will generate a PNG and ask the user to use an online converter if they want it perfect, or I can try to use a simple python script to convert it if `Pillow` is available (it's not in requirements, but I can add it).
- **Decision**: Add `Pillow` to requirements to convert PNG to ICO.

#### [MODIFY] `requirements.txt`
- Add `Pillow`

### Distribution: Packaging
- **Tool**: `flet pack` (requires `pyinstaller`)
- **Command**: `flet pack main.py --name "MetaDescriptionGenerator" --icon "icon.ico"`
- **Output**: `dist/MetaDescriptionGenerator.exe`
- **Note**: This will bundle the Python interpreter and all dependencies into a single executable.

## Verification Plan
### Manual Verification
- Run the app locally (`flet run`).
- Verify all features (Generation, Refinement, Copy, Edit, Persistence).
- Verify the packaged `.exe` runs on the same machine (simulating end-user).
- Verify that 3 distinct descriptions are generated.
- Click "Copy" and verify the clipboard content.
