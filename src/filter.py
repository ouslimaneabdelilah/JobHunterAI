import os
import requests
from bs4 import BeautifulSoup

def get_site_content(url):
    try:
        if not url.startswith("http"):
            url = f"https://{url}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            return soup.get_text(separator=" ", strip=True)[:4000]
    except:
        pass
    return ""

def check_is_valid_company(name, website, snippet, client=None, model_name=None, domain="Web Development Agency"):
    content = ""
    if website:
        content = get_site_content(website)
    
    text_to_analyze = f"Name: {name}\nSnippet: {snippet}\nWebsite Content: {content}"
    
    prompt = f"""
    Analyze the following company data.
    
    1. Determine if it is likely a company operating in the field of: "{domain}".
    2. Extract any generic contact email address (e.g. contact@, info@, hello@) found in the content.
    
    Data:
    {text_to_analyze}
    
    Output Format (JSON strictly):
    {{
        "is_relevant": true/false,
        "email": "email_or_null"
    }}
    """

    if client and model_name:
        try:
            # Azure AI Inference Standard Call
            from azure.ai.inference.models import SystemMessage, UserMessage
            
            # Formulate messages depending on SDK expectation (dicts usually work)
            messages = [
                {"role": "system", "content": "You are a helpful assistant that analyzes companies."},
                {"role": "user", "content": prompt}
            ]
            
            response = client.complete(
                messages=messages,
                model=model_name,
                temperature=0.1
            )
            
            result = response.choices[0].message.content
            
            import json
            # clean potential markdown code blocks
            result = result.replace("```json", "").replace("```", "").strip()
            try:
                data = json.loads(result)
                return data.get("is_relevant", True), data.get("email")
            except:
                # If json parsing fails, fallback to simple string check
                return "OUI" in result.upper() or "YES" in result.upper(), None
                
        except Exception as e:
            print(f"AI Error: {e}")
            pass
            
    return True, None
