import os
import time
import sys
import pandas as pd
import smtplib
from email.message import EmailMessage
# Optional imports to prevent crashes if install failed
try:
    import google.generativeai as genai
except ImportError:
    genai = None
    
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import pypdf

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
except ImportError:
    print("[WARNING] reportlab not installed. PDF generation in Smart Mode will fail.")

# Load environment variables
load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RESUME_PATH = os.getenv("RESUME_PATH", "resume.pdf")

def configure_keys():
    """Reloads keys from env in case they were just updated."""
    global GEMINI_API_KEY, GITHUB_TOKEN, EMAIL_ADDRESS, EMAIL_PASSWORD, RESUME_PATH
    load_dotenv()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    
    if GEMINI_API_KEY and genai:
        try:
            genai.configure(api_key=GEMINI_API_KEY)
        except Exception as e:
            print(f"Warning: Failed to configure Gemini: {e}")

def call_github_api(prompt, model="gpt-4o"):
    """Calls GitHub Models API."""
    if not GITHUB_TOKEN:
        return None
        
    # Standardize model names if needed
    if "deepseek" in model.lower() and "/" not in model:
         # Best guess mapping if user just passed "deepseek"
         model = "deepseek/DeepSeek-V3-0324"
         
    url = "https://models.github.ai/inference/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GITHUB_TOKEN}"
    }
    
    payload = {
        "messages": [
             {"role": "system", "content": "You are a professional recruiting expert and career coach."},
             {"role": "user", "content": prompt}
        ],
        "model": model,
        "temperature": 0.7,
        "max_tokens": 2000,
        "top_p": 1.0
    }
    
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            elif response.status_code == 429:
                print(f"   GitHub Model {model} rate limited. Retrying in 5s...")
                time.sleep(5)
            else:
                print(f"   GitHub Model {model} error: {response.text}")
                return None
        except requests.exceptions.ConnectionError:
            print(f"   Let's retry... ({attempt+1}/3) Connection Error to {model}.")
            time.sleep(3)
        except Exception as e:
            if "NameResolutionError" in str(e) or "getaddrinfo failed" in str(e):
                 print(f"   Let's retry... ({attempt+1}/3) DNS Error to {model}.")
                 time.sleep(3)
            else:
                 print(f"Error calling GitHub API: {e}")
                 return None
    
    print(f"❌ GitHub Connection Error: Unable to reach {model} after 3 attempts.")
    return None


def test_models():
    """Tests connectivity to all configured AI models."""
    configure_keys()
    print("\n--- AI CONNECTIVITY TEST ---")
    
    # 1. GitHub Models
    if GITHUB_TOKEN:
        print("\n[GitHub Models]")
        models = ["deepseek/DeepSeek-V3-0324", "gpt-4o", "meta/Llama-4-Scout-17B-16E-Instruct"]
        for m in models:
            print(f"   Testing {m}...", end=" ", flush=True)
            try:
                # Test with a simple ping
                res = call_github_api("Hello", model=m)
                if res:
                    print("✅ OK")
                else:
                    print("❌ Failed (No response)")
            except Exception as e:
                print(f"❌ Error: {e}")
    else:
        print("\n[GitHub Models] Skipped (No Token)")

    # 2. Gemini Models
    if GEMINI_API_KEY and genai:
        print("\n[Google Gemini]")
        models = ['gemini-flash-latest']
        for m in models:
            print(f"   Testing {m}...", end=" ", flush=True)
            try:
                model = genai.GenerativeModel(m)
                res = model.generate_content("Hello", request_options={'timeout': 10})
                if res and res.text:
                    print("✅ OK")
                else:
                    print("❌ Failed (Empty)")
            except Exception as e:
                if "404" in str(e) or "not found" in str(e).lower():
                     print("❌ Not Available")
                else:
                     print(f"❌ Error: {e}")
    else:
         print("\n[Google Gemini] Skipped (No Key or Library)")

    print("\n---------------------------")

def chat_with_ai():
    configure_keys()
    print("\n--- Chat avec Assistant (GitHub/Gemini) ---")
    print("👉 Tapez 'exit', 'quit' ou 'q' pour revenir au menu principal.")
    print("👉 Ctrl+C pour quitter immediatement.\n")
    
    history = []
    
    while True:
        try:
            print("Vous: ", end="", flush=True)
            user_input = sys.stdin.readline().strip() 
            if not user_input:
                user_input = input("")

            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\nRetour au menu...")
                break
                
            print("...")
            response_text = None
            
            # 1. Try GitHub Models (User Preferred or Default)
            if GITHUB_TOKEN:
                # Try DeepSeek first if possible, otherwise gpt-4o
                response_text = call_github_api(user_input, model="deepseek/DeepSeek-V3-0324")
                if not response_text:
                     response_text = call_github_api(user_input, model="gpt-4o")
                
            # 2. Key/Network Check (Optimization: if GitHub failed due to network, Gemini likely will too, but let's try)
            
            # 3. Try Gemini Models (Fallback Loop)
            if not response_text and GEMINI_API_KEY and genai:
                 model_names = ['gemini-flash-latest']
                 for m_name in model_names:
                     try:
                        # Chat history management could be complex with fallbacks, 
                        # for now we treat each turn as fresh or use simple generation to succeed.
                        model = genai.GenerativeModel(m_name)
                        # We use generate_content for simplicity in fallback, 
                        # or maintain a separate chat session if we want history. 
                        # Given the crash, let's stick to generate_content for robustness or start_chat per model.
                        chat = model.start_chat(history=[]) # History is empty for now to avoid complexity in fallbacks
                        response = chat.send_message(user_input)
                        response_text = response.text
                        break # Success
                     except Exception as e:
                        if "429" in str(e) or "Quota" in str(e):
                            continue # Try next
                        elif "not found" in str(e).lower() or "404" in str(e):
                            continue # Try next
                        elif "NameResolutionError" in str(e) or "getaddrinfo failed" in str(e):
                             print("❌ Gemini Connection Error: Offline.")
                             break # Stop iterating if offline
            
            if response_text:
                print(f"AI: {response_text}\n")
            else:
                print("⚠️  Pas de réponse (Problème de connexion ou Clés API invalides).")
                print("    Vérifiez votre connexion internet ou vos clés dans .env")

        except (KeyboardInterrupt, EOFError):
            print("\n\nSortie du chat...")
            break
        except Exception as e:
            print(f"\nErreur inattendue: {e}")
            break
    if DDGS is None:
        return ""
        
def get_company_info(company_name):
    """Searches for company information using DuckDuckGo."""
    if DDGS is None:
        return ""
    print(f"Searching information for: {company_name}...")
    try:
        results = DDGS().text(f"{company_name} Maroc activité secteur", max_results=3)
        if results:
            info = "\n".join([r['body'] for r in results])
            return info
    except Exception as e:
        print(f"Search failed for {company_name}: {e}")
    return "Information non disponible."

def scrape_website(url):
    """Scrapes text content from the company's website."""
    print(f"Scraping website: {url}...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        if not url.startswith('http'):
            url = 'https://' + url
            
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text_elements = soup.find_all(['p', 'h1', 'h2', 'h3'])
            text = " ".join([t.get_text() for t in text_elements])
            return text[:2000]
    except Exception as e:
        print(f"Scraping failed for {url}: {e}")
    return None

def extract_text_from_pdf(pdf_path):
    print(f"Analyzing CV: {pdf_path}...")
    try:
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None

def extract_name_from_url(url):
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain.split('.')[0].capitalize()
    except:
        return ""

def create_pdf_letter(text, filename):
    try:
    # Single Page Optimization: Reduced margins
        doc = SimpleDocTemplate(filename, pagesize=A4,
                                rightMargin=50, leftMargin=50,
                                topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Justify', parent=styles['Normal'], alignment=TA_JUSTIFY, spaceAfter=12))
        
        Story = []
        replacements = {
            "📞": "Tél : ",
            "📧": "Email : ",
            "✉️": "Email : ",
            "📄": ""
        }
        for emoji, text_repl in replacements.items():
            text = text.replace(emoji, text_repl)
            
        paragraphs = text.split('\n')
        for para in paragraphs:
            if para.strip():
                p = Paragraph(para.strip(), styles["Justify"])
                Story.append(p)
                Story.append(Spacer(1, 6)) # Reduced spacing from 12 to 6 for compactness
                
        doc.build(Story)
        return True
    except Exception as e:
        print(f"Error creating PDF: {e}")
        return False

def generate_cover_letter(company_name, company_info, user_cv_text, ai_client=None, ai_model=None):
    print(f"Generating cover letter for {company_name}...")
    
    prompt = f"""
    Tu es un expert en recrutement. Rédige une **Lettre de Motivation** pour un stage de 2 mois (Mai et Juin 2026).
    
    CANDIDAT:
    Nom: {os.getenv("USER_FULL_NAME", "Candidat")}
    Formation: Développeur Web Full Stack (YouCode)
    Tel: {os.getenv("USER_PHONE", "06 00 00 00 00")}
    Email: {os.getenv("USER_CONTACT_EMAIL", "email@example.com")}
    Adresse: {os.getenv("USER_ADDRESS", f"{os.getenv('USER_CITY', 'Ville')}, Maroc")}
    
    ENTREPRISE CIBLE: "{company_name}"
    INFO ENTREPRISE: "{company_info}"
    
    TACHE:
    Rédige le corps de la lettre de motivation en suivant STRICTEMENT le modèle ci-dessous.
    
    RÈGLES DE GÉNÉRATION:
    1. Remplace "{company_name}" par le nom de l'entreprise cible.
    2. Mets la date du jour à la place de "02/02/2026" (format: Ville, le Jour/Mois/Année).
    3. Garde le reste du texte EXACTEMENT comme dans le modèle (copier-coller).
    4. PAS DE FORMATTAGE MARKDOWN (pas de gras, pas d'italique). Texte brut uniquement.
    5. Utilise les informations de l'entreprise pour personnaliser légèrement le paragraphe de motivation sans changer la structure globale.
    
    MODELE:
    {os.getenv("USER_CITY", "Ville")}, le 02/02/2026
    Objet : Demande de stage – Période mai–juin 2026
    Madame, Monsieur,
    Actuellement étudiant en Développement Web Full Stack au sein de YouCode, je me permets de
    vous adresser ma candidature pour un stage d’une durée de deux mois, prévu sur la période mai et
    juin 2026.
    Ce stage s’inscrit dans le cadre de ma formation et représente pour moi une opportunité essentielle
    afin de mettre en pratique mes connaissances théoriques, développer mes compétences
    professionnelles et découvrir concrètement le monde de l’entreprise.
    Motivé, sérieux et doté d’un bon esprit d’équipe, je suis particulièrement intéressé par votre
    entreprise, {company_name}, en raison de son expertise reconnue dans le développement de solutions
    digitales innovantes et l'utilisation de technologies de pointe (notamment dans l'écosystème Full
    Stack moderne). Intégrer votre structure me permettrait d’enrichir mon parcours académique tout
    en apportant ma motivation et mon engagement aux missions qui me seront confiées.
    Je reste à votre disposition pour toute information complémentaire ou entretien éventuel.
    Veuillez trouver ci-joint mon CV ainsi que ma lettre de motivation.
    Je vous remercie par avance pour l’attention que vous porterez à ma candidature et vous prie
    d’agréer, Madame, Monsieur, l’expression de mes salutations distinguées.
    {os.getenv("USER_FULL_NAME", "Candidat")}
    
    Tél : {os.getenv("USER_PHONE", "06 00 00 00 00")}
    
    Email : {os.getenv("USER_CONTACT_EMAIL", "email@example.com")}
    {os.getenv("USER_ADDRESS", f"{os.getenv('USER_CITY', 'Ville')}, Maroc")}
    """
    
    try:
        # 1. Try Selected AI Client (SDK) 
        # MODIFICATION: Prefer REST API (call_github_api) if we have the TOKEN, to avoid SDK hangs/timeouts.
        if (ai_client and ai_model) or (GITHUB_TOKEN and ai_model):
            msg = f"   Attempting generation with {ai_model}..."
            print(msg)
            
            # Prefer using our own REST wrapper because it has 60s timeout handling
            if GITHUB_TOKEN:
                response_text = call_github_api(prompt, model=ai_model)
                if response_text:
                     return response_text
                else:
                     print(f"   ❌ {ai_model} (REST) failed or timed out.")
            else:
                # Fallback to SDK if for some reason we have client but no token var (unlikely)
                try:
                    messages = [{"role": "user", "content": prompt}]
                    response = ai_client.complete(messages=messages, model=ai_model, temperature=0.7)
                    return response.choices[0].message.content
                except Exception as e:
                    print(f"   ❌ Selected Model ({ai_model}) Failed: {e}")
            
            print("   Switching to fallback...")

        # 2. Try GitHub Models via REST (Fallback loop)
        if GITHUB_TOKEN:
            # List of models to try in order
            models_to_try = []
            if ai_model and "deepseek" in ai_model.lower(): # If user wanted deepseek but SDK failed
                 models_to_try.append("deepseek/DeepSeek-V3-0324")
            
            models_to_try.extend(["deepseek/DeepSeek-V3-0324", "gpt-4o"])
            
            # Deduplicate
            seen = set()
            unique_models = []
            for m in models_to_try:
                if m not in seen:
                    unique_models.append(m)
                    seen.add(m)

            for model_name in unique_models:
                print(f"   Attempting generation with GitHub Models ({model_name})...")
                content = call_github_api(prompt, model=model_name)
                if content: return content

        # 3. Try Gemini Models (Fallback)
        if GEMINI_API_KEY and genai:
            print("   Falling back to Gemini...")
            # Updated model list with 'latest' and flash
            model_names = ['gemini-flash-latest']
            for m_name in model_names:
                try:
                    model = genai.GenerativeModel(m_name)
                    # Set a timeout for the request to avoid hanging
                    response = model.generate_content(prompt, request_options={'timeout': 30})
                    return response.text
                except Exception as e:
                    if "429" in str(e) or "Quota" in str(e):
                        print(f"   Gemini Quota exceeded ({m_name}). Waiting 20s...")
                        time.sleep(20)
                        # Retry once after waiting
                        try:
                            response = model.generate_content(prompt, request_options={'timeout': 30})
                            return response.text
                        except:
                            print("   Gemini Quota still exceeded after waiting. Skipping.")
                            continue
                    elif "not found" in str(e).lower() or "404" in str(e):
                         print(f"   Gemini {m_name} not available. Trying next...")
                    elif "NameResolutionError" in str(e) or "getaddrinfo failed" in str(e):
                         print(f"   Gemini Connection Error: Offline.")
                         break # Offline, no need to try other gemini models
                    else:
                        print(f"   Error with Gemini {m_name}: {e}")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Network Error: Could not reach AI services.")
        print("   Please check your internet connection and try again.")
        return None
    except Exception as e:
        if "NameResolutionError" in str(e) or "getaddrinfo failed" in str(e):
             print("\n❌ DNS/Network Error: You seem to be offline.")
        else:
         print(f"❌ AI Generation Error: {e}")
    
    print("⚠️  AI models failed/skipped. Using Fallback Template.")
    # FALLBACK LOGIC
    # Construct a clean fallback letter using strict template
    current_date = time.strftime(f"{os.getenv('USER_CITY', 'Ville')}, le %d/%m/%Y")
    fallback_letter = f"""{current_date}
Objet : Demande de stage – Période mai–juin 2026

Madame, Monsieur,

Actuellement étudiant en Développement Web Full Stack au sein de YouCode, je me permets de
vous adresser ma candidature pour un stage d’une durée de deux mois, prévu sur la période mai et
juin 2026.

Ce stage s’inscrit dans le cadre de ma formation et représente pour moi une opportunité essentielle
afin de mettre en pratique mes connaissances théoriques, développer mes compétences
professionnelles et découvrir concrètement le monde de l’entreprise.

Motivé, sérieux et doté d’un bon esprit d’équipe, je suis particulièrement intéressé par votre
entreprise, {company_name}, en raison de son expertise reconnue dans le développement de solutions
digitales innovantes et l'utilisation de technologies de pointe (notamment dans l'écosystème Full
Stack moderne). Intégrer votre structure me permettrait d’enrichir mon parcours académique tout
en apportant ma motivation et mon engagement aux missions qui me seront confiées.

Je reste à votre disposition pour toute information complémentaire ou entretien éventuel.
Veuillez trouver ci-joint mon CV ainsi que ma lettre de motivation.

Je vous remercie par avance pour l’attention que vous porterez à ma candidature et vous prie
d’agréer, Madame, Monsieur, l’expression de mes salutations distinguées.

{os.getenv("USER_FULL_NAME", "Candidat")}

Tél : {os.getenv("USER_PHONE", "06 00 00 00 00")}
Email : {os.getenv("USER_CONTACT_EMAIL", "email@example.com")}
{os.getenv("USER_ADDRESS", f"{os.getenv('USER_CITY', 'Ville')}, Maroc")}"""

    return fallback_letter

def send_email(recipient_email, subject, html_content, resume_path, letter_pdf_path=None):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recipient_email
    
    if html_content:
        msg.set_content(html_content)
    else:
        msg.set_content("Veuillez trouver ci-joint mon CV et ma lettre de motivation.") 

    if os.path.exists(resume_path):
        with open(resume_path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=os.path.basename(resume_path))
    else:
        print(f"Warning: Resume file '{resume_path}' not found. Sending without attachment.")
        
    if letter_pdf_path and os.path.exists(letter_pdf_path):
        with open(letter_pdf_path, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=os.path.basename(letter_pdf_path))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"Email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")
        return False


def run_smart_apply(ai_client=None, ai_model=None):
    configure_keys()
    
    # 1. Select File
    print("\n--- SMART APPLICATION ---")
    files = [f for f in os.listdir('.') if (f.endswith('.xlsx') or f.endswith('.csv')) and 'validated' in f]
    if not files:
        files = [f for f in os.listdir('.') if (f.endswith('.xlsx') or f.endswith('.csv')) and f.startswith('leads')]
        
    if not files:
        print("No leads file found.")
        return

    print("Available Files:")
    for i, f in enumerate(files):
        print(f"{i+1}. {f}")
        
    try:
        choice = int(input("Choice: ")) - 1
        target_file = files[choice]
    except:
        return

    # 2. Load Resume
    resume_file = "CV.pdf"
    if not os.path.exists(resume_file):
        resume_file = RESUME_PATH if RESUME_PATH else "resume.pdf"
    
    if not os.path.exists(resume_file):
        print(f"Error: Could not find CV ({resume_file}). Please make sure CV.pdf exists.")
        return

    user_profile_text = extract_text_from_pdf(resume_file)
    if not user_profile_text:
        return
    
    print("CV Analyzed.")

    # 3. Process
    if target_file.endswith('.xlsx'):
        try:
            df = pd.read_excel(target_file)
        except:
             df = pd.read_csv(target_file.replace('.xlsx', '.csv'))
    else:
        df = pd.read_csv(target_file)

    print(f"Found {len(df)} companies.")
    
    for index, row in df.iterrows():
        # Handle case variations
        row_keys = {k.lower(): k for k in row.keys()}
        
        email = row.get(row_keys.get('email', 'email'))
        website = row.get(row_keys.get('website', 'website'))
        company_name = row.get(row_keys.get('name', 'name')) or row.get(row_keys.get('company name', 'Company Name'))
        
        if pd.isna(email) or "@" not in str(email):
            continue
            
        # Get Company Name from URL if missing
        if pd.isna(company_name) or str(company_name).strip() == "":
            if website:
                company_name = extract_name_from_url(str(website))
            else:
                company_name = "Entreprise"
        
        print(f"\nProcessing [{index+1}/{len(df)}]: {company_name} ({email})")
        
        info = ""
        if pd.notna(website) and str(website).strip() != "":
            scraped_info = scrape_website(str(website))
            if scraped_info:
                info += f"\nInfos du site web ({website}):\n{scraped_info}"
        
        search_info = get_company_info(company_name)
        if search_info:
             info += f"\nInfos de recherche:\n{search_info}"
        
        letter_text = generate_cover_letter(company_name, info, user_profile_text, ai_client, ai_model)
        
        if letter_text:
            pdf_filename = f"Lettre_Motivation_{str(company_name).replace(' ', '_')}.pdf"
            if create_pdf_letter(letter_text, pdf_filename):
                print(f"   PDF Created: {pdf_filename}")
                
                subject = "Objet : Demande de stage – Période mai–juin 2026"
                email_body = f"""Bonjour Madame, Monsieur,

Je vous contacte afin de soumettre ma candidature pour un poste de Stagiaire Développeur Web Full Stack au sein de votre agence, {company_name}.

Actuellement en formation à YouCode, je recherche activement un stage de fin d'année d'une durée de deux mois. Je suis disponible pour effectuer ce stage de Mai à Juin 2026.

Passionné par les technologies web et désireux d’appliquer mes compétences en environnement professionnel, je suis convaincu que cette expérience serait mutuellement bénéfique.

Vous trouverez mon Curriculum Vitae ainsi que ma Lettre de Motivation ci-joints. Je me tiens à votre disposition pour un entretien afin de vous présenter plus amplement mon profil et mes motivations.

Dans l'attente de votre retour, veuillez agréer, Madame, Monsieur, l'expression de mes salutations distinguées.

Cordialement,

Cordialement,

{os.getenv("USER_FULL_NAME", "Candidat")}"""
                
                success = send_email(email, subject, email_body, resume_file, pdf_filename)
                
                if success:
                    time.sleep(5) 
            else:
                print("   Failed to create PDF.")
        else:
            print("   Failed to generate letter text.")
