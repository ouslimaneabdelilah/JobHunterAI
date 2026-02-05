try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

import os
import time

try:
    import google.generativeai as genai
except ImportError:
    genai = None

def generate_cover_letter_text(company_name, company_info, cv_text, client, model_name, user_name, user_email):
    prompt = f"""
    You are writing a professional cover letter for {user_name} from {os.getenv('USER_CITY', 'Ville')}.
    
    My CV Content:
    {cv_text}
    
    Target Company: {company_name}
    Company Details: {company_info}
    My Contact Email: {user_email}
    My Phone: {os.getenv("USER_PHONE", "")}
    
    INSTRUCTIONS:
    1. Write a professional cover letter tailored to the company.
    2. STRICTLY USE FACTS FROM THE CV ONLY. Do NOT invent skills, experiences, or project names that are not in the CV.
    3. If the company requires a skill I don't have in my CV, do not claim I have it. Instead, express willingness to learn.
    4. Sign the letter with my name: {user_name}.
    5. Keep it concise (max 300 words).
    6. Return ONLY the body of the letter. No markdown formatting, no preambles.
    """
    
    # 1. Try Primary Client (GitHub/Azure)
    if client and model_name:
        try:
            messages = [
                {"role": "user", "content": prompt}
            ]
            response = client.complete(
                messages=messages,
                model=model_name,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"   [Primary AI Failed: {e}] Switching to fallback...")

    # 2. Try Fallback (Gemini)
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if not gemini_key:
         print("   [Fallback Skip] GEMINI_API_KEY not found in .env")
    if not genai:
         print("   [Fallback Skip] google.generativeai not installed/imported.")

    if gemini_key and genai:
        print("   [Fallback] Attempting Gemini...")
        try:
            genai.configure(api_key=gemini_key)
            # Try a robust list of models (Prioritizing Flash as requested)
            models_to_try = ['gemini-flash-latest']
            for m in models_to_try:
                try:
                    model = genai.GenerativeModel(m)
                    response = model.generate_content(prompt)
                    return response.text
                except Exception as inner_e:
                    print(f"      - Gemini {m} failed: {inner_e}")
                    continue
        except Exception as e:
            print(f"   [Fallback AI Error: {e}]")
            
    
    # FALLBACK TEMPLATE (If all AI failed)
    print("   ⚠️  AI models failed. Using Fallback Template.")
    current_date = time.strftime(f"{os.getenv('USER_CITY', 'Ville')}, le %d/%m/%Y")
    fallback_text = f"""{current_date}
Objet : Candidature

Madame, Monsieur,

Actuellement étudiant en Développement Web Full Stack, je souhaite postuler au sein de votre entreprise {company_name}.
Doté de compétences solides acquises lors de ma formation, je suis motivé pour contribuer à vos projets.

Je reste à votre disposition pour un entretien.
Veuillez trouver ci-joint mon CV.

Cordialement,

{user_name}
Tél: {os.getenv('USER_PHONE', '')}
Email: {user_email}
"""
    return fallback_text

def create_pdf(text, filename):
    if not text:
        return False
        
    if FPDF is None:
        print("ERROR: 'fpdf' library not installed. Cannot create PDF.")
        return False
        
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # simple cleanup for utf-8
        try:
            text = text.encode('latin-1', 'replace').decode('latin-1')
        except:
            pass
        
        pdf.multi_cell(0, 10, text)
        pdf.output(filename)
        return True
    except Exception as e:
        print(f"PDF Error: {e}")
        return False

def generate_search_keywords(domain, client, model_name):
    """
    Generates a list of Google Maps search keywords based on a user's professional domain.
    """
    prompt = f"""
    I need to find companies and agencies in the directory for Google Maps in the field of: "{domain}".
    
    Please generate a python list of 5 to 10 specific search terms (keywords) that I should type into Google Maps to find these companies.
    Focus on terms that would appear in the business name or category.
    
    Example input: "Web Development"
    Example output: ["Web Design Agency", "Software Company", "Digital Marketing Agency", "Website Developer", "IT Consultant"]
    
    RETURN ONLY THE PYTHON LIST. NO MARKDOWN. NO EXPLANATION.
    """
    
    text_response = ""
    
    # 1. Try Primary Client (GitHub/Azure)
    if client and model_name:
        try:
            messages = [
                {"role": "user", "content": prompt}
            ]
            response = client.complete(
                messages=messages,
                model=model_name,
                temperature=0.7
            )
            text_response = response.choices[0].message.content
        except Exception as e:
            print(f"   [Primary AI Failed: {e}] Switching to fallback...")

    # 2. Try Fallback (Gemini)
    if not text_response:
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                if not genai:
                    import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                # Try a robust list of models (Prioritizing Flash)
                models_to_try = ['gemini-flash-latest', 'gemini-1.5-flash', 'gemini-1.5-pro']
                for m in models_to_try:
                    try:
                        model = genai.GenerativeModel(m)
                        response = model.generate_content(prompt)
                        text_response = response.text
                        break
                    except: continue
            except: pass

    # Parse the response into a list
    if text_response:
        import ast
        try:
            # Clean up potential markdown formatting like ```python ... ```
            clean_text = text_response.replace("```python", "").replace("```", "").strip()
            keywords = ast.literal_eval(clean_text)
            if isinstance(keywords, list):
                return keywords
        except:
            # Fallback parsing: split by newlines if it's not a valid list
            return [line.strip("- *") for line in text_response.splitlines() if line.strip()]

    # Default fallback if AI fails completely
    return [f"{domain} agency", f"{domain} company", f"{domain} services"]
