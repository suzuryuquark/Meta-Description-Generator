import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json

def fetch_website_content(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract relevant text
        title = soup.title.string if soup.title else ""
        meta_desc = ""
        meta = soup.find('meta', attrs={'name': 'description'})
        if meta:
            meta_desc = meta.get('content', '')
        
        # Get main content text (h1, h2, p)
        content_parts = []
        if title: content_parts.append(f"Title: {title}")
        if meta_desc: content_parts.append(f"Current Description: {meta_desc}")
        
        for tag in soup.find_all(['h1', 'h2', 'p']):
            text = tag.get_text(strip=True)
            if len(text) > 20: # Filter out short snippets
                content_parts.append(text)
        
        # Limit content length to avoid token limits (approx 10k chars)
        full_text = "\n".join(content_parts)
        return full_text[:10000]
        
    except Exception as e:
        raise Exception(f"サイトの読み込みに失敗しました: {str(e)}")

def generate_descriptions(api_key, website_text, global_instruction, target_keywords):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    あなたはSEOの専門家です。以下のWebサイトのテキストコンテンツを分析し、検索エンジンの結果ページ（SERP）でクリック率を高めるための魅力的なmeta descriptionを3つ提案してください。
    
    要件:
    - 日本語で出力すること
    - タイトルタグは30文字前後、Meta Descriptionは100文字〜120文字程度
    - それぞれ異なる訴求ポイント（例：メリット強調、疑問形、要約型など）を持つこと
    - 指定された必須キーワードを可能な限り自然に含めること
    - 出力は以下のJSON形式のみにしてください。余計なmarkdown装飾は不要です。
    
    JSON形式:
    [
        {{"title": "パターン1の特徴", "title_tag": "生成されたタイトルタグ", "description": "生成された説明文"}},
        {{"title": "パターン2の特徴", "title_tag": "生成されたタイトルタグ", "description": "生成された説明文"}},
        {{"title": "パターン3の特徴", "title_tag": "生成されたタイトルタグ", "description": "生成された説明文"}}
    ]

    Webサイトのコンテンツ:
    {website_text}

    サイト共通の指示:
    {global_instruction}

    必須キーワード:
    {target_keywords}
    """

    response = model.generate_content(prompt)
    
    # Parse JSON response
    text_response = response.text.strip()
    # Remove markdown code blocks if present
    if text_response.startswith("```json"):
        text_response = text_response[7:-3]
    elif text_response.startswith("```"):
        text_response = text_response[3:-3]
        
    return json.loads(text_response)

def refine_description(api_key, website_text, original_desc, global_instruction, target_keywords, refine_instruction):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    あなたはSEOの専門家です。
    以下のWebサイトのコンテンツと、現在提案されているmeta descriptionを元に、
    ユーザーの指示に従ってdescriptionを書き直してください。

    Webサイトのコンテンツ:
    {website_text}

    現在のdescription:
    {original_desc}

    サイト共通の指示:
    {global_instruction}

    必須キーワード:
    {target_keywords}

    ユーザーの修正指示:
    {refine_instruction}

    要件:
    - 日本語で出力すること
    - 文字数は100文字〜120文字程度
    - 出力は修正後のdescriptionのテキストのみ（JSON不要）
    """

    response = model.generate_content(prompt)
    return response.text.strip()
