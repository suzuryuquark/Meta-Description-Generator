# Meta Description Generator v1.2.0 詳細実装計画

## 概要
v1.2.0 では、AI モデルを `gemini-3-flash-preview` にアップグレードし、以下の 2 つの主要機能を追加します。
1. **トーン＆スタイルのプリセット**: 生成時の雰囲気をボタン一つで指定可能にします。
2. **生成履歴の保存**: 過去に生成したディスクリプションをアプリ内に保存し、後で確認できるようにします。

---

## 変更内容

### 1. AI モデルのアップグレード
- 使用するモデルを `gemini-2.5-flash` から `gemini-3-flash-preview` に変更します。

#### [MODIFY] [core_logic.py](file:///c:/Users/suzur/source/Meta%20Description%20Generator/core_logic.py)
- `generate_descriptions` および `refine_description` 内のモデル識別子を更新。

---

### 2. トーン＆スタイルのプリセット機能
- ユーザーが「プロフェッショナル」「親しみやすい」「キャッチー」などのトーンを選択できる UI を追加します。

#### [MODIFY] [main.py](file:///c:/Users/suzur/source/Meta%20Description%20Generator/main.py)
- トーン選択用の `ft.Dropdown` を生成ボタンの上に追加。
- 選択されたトーンを `core_logic.generate_descriptions` に渡すよう変更。

#### [MODIFY] [core_logic.py](file:///c:/Users/suzur/source/Meta%20Description%20Generator/core_logic.py)
- `generate_descriptions` の引数に `tone` を追加し、プロンプトに組み込む。
- プリセット例:
    - デフォルト（SEO重視）
    - プロフェッショナル（信頼感、硬め）
    - 親しみやすい（カジュアル、柔らかめ）
    - キャッチー（クリック誘発、インパクト重視）
    - メリット強調（ベネフィットを前面に）

---

### 3. 生成履歴の保存機能
- `page.client_storage` を利用して、直近の生成結果を保存します。

#### [MODIFY] [main.py](file:///c:/Users/suzur/source/Meta%20Description%20Generator/main.py)
- メイン画面を「生成」タブと「履歴」タブに分割（`ft.Tabs`）。
- 生成完了時に結果をストレージに保存するロジックを追加。
- 「履歴」タブで保存された過去のデータをリスト表示し、再利用やコピーを可能にする。

#### [MODIFY] [ui_components.py](file:///c:/Users/suzur/source/Meta%20Description%20Generator/ui_components.py)
- 履歴表示用の簡略化されたカードコンポーネントを作成。

---

## 検証計画

### 1. 機能テスト
- **モデルアップグレード**: `test_model.py` を実行し、`gemini-3-flash-preview` で正常に応答が得られるか確認。
- **トーン指定**: 各トーンを選択した際、生成される文章のニュアンスが変化することを確認。
- **履歴保存**: アプリを再起動しても、過去の生成結果が「履歴」タブに表示されることを確認。

### 2. 回帰テスト
- 既存の URL 解析機能、ディスクリプションの修正機能、CSV エクスポート機能が正常に動作することを確認。
