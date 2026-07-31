import requests
from bs4 import BeautifulSoup


def fetch_website_content(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract relevant text
        title = soup.title.string if soup.title else ""
        meta_desc = ""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            meta_content = meta.get("content", "")
            meta_desc = meta_content if isinstance(meta_content, str) else ""

        # Get main content text (h1, h2, p)
        content_parts = []
        if title:
            content_parts.append(f"Title: {title}")
        if meta_desc:
            content_parts.append(f"Current Description: {meta_desc}")

        for tag in soup.find_all(["h1", "h2", "p"]):
            text = tag.get_text(strip=True)
            if len(text) > 20:  # Filter out short snippets
                content_parts.append(text)

        # Limit content length to avoid token limits (approx 10k chars)
        full_text = "\n".join(content_parts)
        return full_text[:10000]

    except Exception as exc:
        raise Exception(f"サイトの読み込みに失敗しました: {exc}") from exc
