import sys
import os
import time
from install import install_dependencies

# Always ask user about dependencies first
install_dependencies()

# Now import the rest
try:
    import pandas as pd
    from dotenv import load_dotenv
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.inference import ChatCompletionsClient
    import pypdf
    from src import scraper, filter, generator, mailer, smart_applier, google_scraper
except ImportError as e:
    print(f"\n[WARNING] Missing dependency: {e}")
    print("Some features might not work. Please try installing libraries again later or manually.")

# Load env variables
load_dotenv()

# Global variables
AI_CLIENT = None
AI_MODEL = None
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RESUME_PATH = os.getenv("RESUME_PATH", "resume.pdf")

def save_key_to_env(key, value):
    """Helper to save a key to .env file."""
    if not value: return
    
    env_content = ""
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            env_content = f.read()
    
    # Check if key exists to replace or append
    lines = env_content.splitlines()
    new_lines = []
    found = False
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
            
    if not found:
        new_lines.append(f"{key}={value}")
        
    with open(".env", "w") as f:
        f.write("\n".join(new_lines) + "\n")
    
    os.environ[key] = value

def setup_email():
    """Checks for Email credentials and prompts if missing."""
    print("\n--- 1. EMAIL SETUP ---")
    
    # Check if already loaded
    email = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")

    if email and password:
        print("✅ Email credentials found in .env")
        return

    if not email:
        email = input("Enter your Gmail Address (e.g. user@gmail.com): ").strip()
        save_key_to_env("EMAIL_ADDRESS", email)
        
    if not password:
        print("Note: You need a Gmail App Password (NOT your login password).")
        password = input("Enter your App Password (16 chars): ").strip()
        save_key_to_env("EMAIL_PASSWORD", password)

    print("✅ Email configured.")

def setup_user_info():
    """Prompts for User Name and Contact Email for customization."""
    print("\n--- 3. USER INFO SETUP ---")
    
    full_name = os.getenv("USER_FULL_NAME")
    contact_email = os.getenv("USER_CONTACT_EMAIL")
    
    if full_name and contact_email:
        print(f"✅ User Info found: {full_name} ({contact_email})")
        # Do not return here, continue to check City/Address
        
    if not full_name:
        full_name = input("Enter your Full Name (for signature): ").strip()
        save_key_to_env("USER_FULL_NAME", full_name)
        
    if not contact_email:
        contact_email = input("Enter your Contact Email (for letter/CV): ").strip()
        save_key_to_env("USER_CONTACT_EMAIL", contact_email)
    
    # Phone Setup
    phone = os.getenv("USER_PHONE")
    if not phone:
        phone = input("Enter your Phone Number: ").strip()
        save_key_to_env("USER_PHONE", phone)
        
    # City and Address Setup
    city = os.getenv("USER_CITY")
    address = os.getenv("USER_ADDRESS")
    
    if not city:
        city = input("Enter your City (e.g. Casablanca): ").strip()
        save_key_to_env("USER_CITY", city)
        
    if not address:
        address = input("Enter your Address (optional, press Enter to skip): ").strip()
        if not address: address = f"{city}, Maroc"
        save_key_to_env("USER_ADDRESS", address)
        
    print("✅ User Info saved.")
    return full_name, contact_email

def setup_ai_interactive():
    """Prompts for Model Provider preference and ensures keys exist."""
    global AI_CLIENT, AI_MODEL, GITHUB_TOKEN
    
    print("\n--- 2. AI MODEL SETUP ---")
    print("Which AI provider do you want to use?")
    print("1. GitHub Models (Free access to Llama 3, GPT-4o, DeepSeek)")
    print("2. Google Gemini (Gemini 1.5 Flash)")
    
    choice = input("Choice (1 or 2): ").strip()
    
    if choice == '2':
        # Gemini Setup
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("\nGemini API Key is missing.")
            api_key = input("Enter your GEMINI_API_KEY: ").strip()
            save_key_to_env("GEMINI_API_KEY", api_key)
        else:
             print("✅ GEMINI_API_KEY found.")
        
        print(f"Selected: Google Gemini")
        # We don't set AI_CLIENT here (it's for Azure), smart_applier handles Gemini via google.genai

    else:
        # GitHub/Azure Setup (Default)
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            print("\nGitHub Token is missing.")
            token = input("Enter your GITHUB_TOKEN: ").strip()
            save_key_to_env("GITHUB_TOKEN", token)
            GITHUB_TOKEN = token 
        else:
             print("✅ GITHUB_TOKEN found.")
        
        if not token:
            print("No token provided. AI features will fail.")
            return

        print("\nSelect Model:")
        print("1. Meta Llama 4 (meta/Llama-4-Scout-17B-16E-Instruct)")
        print("2. DeepSeek V3 (deepseek/DeepSeek-V3-0324)")
        print("3. GPT-4o (openai/gpt-4o)")
        
        m_choice = input("Choice (1-3): ").strip()
        if m_choice == '2': AI_MODEL = "deepseek/DeepSeek-V3-0324"
        elif m_choice == '3': AI_MODEL = "openai/gpt-4o"
        else: AI_MODEL = "meta/Llama-4-Scout-17B-16E-Instruct"
        
        try:
            AI_CLIENT = ChatCompletionsClient(
                endpoint="https://models.github.ai/inference",
                credential=AzureKeyCredential(token)
            )
            print(f"✅ Configured Client with {AI_MODEL}")
        except Exception as e:
            print(f"Error initializing client: {e}")

def extract_text_from_pdf(pdf_path):
    try:
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except:
        return ""

def save_data(data, filename):
    if not data:
        return
    df = pd.DataFrame(data)
    try:
        df = df.drop_duplicates(subset=['website'], keep='first')
        df = df.drop_duplicates(subset=['email'], keep='first')
    except: pass
    
    try:
        df.to_excel(filename, index=False)
        print(f"Saved to {filename}")
    except:
        csv_file = filename.replace(".xlsx", ".csv")
        df.to_csv(csv_file, index=False)
        print(f"Saved to {csv_file}")

def menu_scrape():
    print("GATHERING DATA")
    domain = input("Domain / Activity Field (e.g. Web Development, Civil Engineering): ")
    city = input("City: ")
    
    print(f"Generating search keywords for '{domain}' with AI...")
    keywords_list = generator.generate_search_keywords(domain, AI_CLIENT, AI_MODEL)
    print(f"AI suggests searching for: {keywords_list}")
    
    all_companies = []
    
    for keyword in keywords_list:
        print(f"\n>>> Scraping Keyword: {keyword} in {city}...")
        # Limiting results per keyword to avoid taking too long, since we have multiple keywords
        results = scraper.search_companies(city, keyword, max_results=30) 
        if results:
            all_companies.extend(results)
    
    if not all_companies:
        print("No companies found.")
        return

    df_raw = pd.DataFrame(all_companies)
    try:
        df_raw = df_raw.drop_duplicates(subset=['name', 'website'])
    except: pass
    
    raw_companies = df_raw.to_dict('records')

    print(f"Found {len(raw_companies)} total unique results.")
    
    # Use domain in filename instead of single keyword
    raw_filename = f"leads_{city}_{domain}_RAW.xlsx"
    raw_filename = "".join([c for c in raw_filename if c.isalpha() or c.isdigit() or c in ['_','.']]).rstrip()
    
    save_data(raw_companies, raw_filename)
    
    print("Filtering with AI...")
    
    valid_companies = []
    seen_websites = set()
    
    for company in raw_companies:
        name = company.get('name')
        website = company.get('website')
        email = company.get('email')
        snippet = company.get('snippet')
        
        if website in seen_websites and website is not None:
             continue
        if website:
            seen_websites.add(website)

        is_dev_agency, found_email = filter.check_is_valid_company(name, website, snippet, AI_CLIENT, AI_MODEL, domain=domain)
        
        if not is_dev_agency:
            print(f"[REJECTED] {name} - Not a relevant agency")
            continue
            
        if (not email or "@" not in str(email)) and found_email and "@" in str(found_email):
            email = found_email
            company['email'] = email
            print(f"   [AI FOUND EMAIL] {email}")

        if not name or not website or not email or "@" not in str(email):
            print(f"[REJECTED] {name} - Missing Name/Email/Website")
            continue
            
        print(f"[ACCEPTED] {name}")
        valid_companies.append(company)
        
    final_filename = f"leads_{city}_{domain}.xlsx"
    final_filename = "".join([c for c in final_filename if c.isalpha() or c.isdigit() or c in ['_','.']]).rstrip()
    
    if valid_companies:
        save_data(valid_companies, final_filename)
    else:
        print("No valid companies found.")

def menu_validate_excel():
    print("VALIDATE EXCEL FILE")
    files = [f for f in os.listdir('.') if (f.endswith('.xlsx') or f.endswith('.csv'))]
    if not files:
        print("No files found.")
        return
        
    for i, f in enumerate(files):
        print(f"{i+1}. {f}")
        
    try:
        choice = int(input("Choice: ")) - 1
        target_file = files[choice]
    except:
        return

    if target_file.endswith('.xlsx'):
        try:
            df = pd.read_excel(target_file)
        except:
             df = pd.read_csv(target_file.replace('.xlsx', '.csv'))
    else:
        df = pd.read_csv(target_file)
        
    print(f"Loaded {len(df)} rows. Starting validation...")
    
    valid_rows = []
    
    for index, row in df.iterrows():
        name = row.get('name', '')
        website = row.get('website', '')
        email = row.get('email', '')
        snippet = row.get('snippet', '')
        
        is_dev_agency, found_email = filter.check_is_valid_company(name, website, snippet, AI_CLIENT, AI_MODEL)
        
        if is_dev_agency:
            if (pd.isna(email) or not email or "@" not in str(email)) and found_email and "@" in str(found_email):
                row['email'] = found_email
                print(f"   [AI FOUND EMAIL] {found_email}")
            
            current_email = row.get('email')
            if name and website and current_email and "@" in str(current_email):
                print(f"[KEPT] {name}")
                valid_rows.append(row)
            else:
                 print(f"[DROPPED] {name} - Missing Info")
        else:
             print(f"[DROPPED] {name} - Not a dev agency")
             
    if valid_rows:
        new_filename = f"validated_{target_file}"
        save_data(valid_rows, new_filename)
    else:
        print("No valid rows remaining.")

def menu_apply():
    print("APPLICATION (BASIC)")
    files = [f for f in os.listdir('.') if (f.endswith('.xlsx') or f.endswith('.csv')) and 'validated' in f]
    if not files:
        files = [f for f in os.listdir('.') if (f.endswith('.xlsx') or f.endswith('.csv')) and f.startswith('leads') and 'RAW' not in f]
    
    if not files:
        print("No valid leads file found.")
        return
        
    for i, f in enumerate(files):
        print(f"{i+1}. {f}")
        
    try:
        choice = int(input("Choice: ")) - 1
        target_file = files[choice]
    except:
        return
    
    if target_file.endswith('.xlsx'):
        try:
            df = pd.read_excel(target_file)
        except:
             df = pd.read_csv(target_file.replace('.xlsx', '.csv'))
    else:
        df = pd.read_csv(target_file)

    # CV Path Logic
    resume_file = "CV.pdf"
    if not os.path.exists(resume_file):
        resume_file = RESUME_PATH if RESUME_PATH else "resume.pdf"
    
    if not os.path.exists(resume_file):
        print(f"Error: Could not find CV ({resume_file}). Please make sure CV.pdf exists.")
        return

    user_cv_text = extract_text_from_pdf(resume_file)
    
    for index, row in df.iterrows():
        company_name = row['name']
        email = row['email']
        website = row['website']
        snippet = row.get('snippet', '')
        
        if pd.isna(email) or not email or "@" not in str(email):
            continue
            
        print(f"Processing: {company_name}")
        
        letter_text = generator.generate_cover_letter_text(
            company_name, 
            f"Site: {website}, Info: {snippet}", 
            user_cv_text,
            AI_CLIENT, AI_MODEL,
            os.getenv("USER_FULL_NAME"),
            os.getenv("USER_CONTACT_EMAIL")
        )
        
        if not letter_text:
            print("   [SKIP] Failed to generate cover letter. Email NOT sent.")
            continue

        pdf_name = f"Lettre_{str(company_name).replace(' ', '_')}.pdf"
        if generator.create_pdf(letter_text, pdf_name):
            subject = f"Candidature Stage: Developpeur Full Stack - {os.getenv('USER_FULL_NAME')}"
            body = f"""Bonjour,

Je vous adresse ma candidature pour un stage de Développeur Web Full Stack au sein de {company_name}.

Vous trouverez ci-joint mon CV et ma lettre de motivation détaillant mon parcours et ma motivation.

Je reste à votre disposition pour un entretien.

Cordialement,

{os.getenv('USER_FULL_NAME')}"""
            sent = mailer.send_email_with_attachments(
                EMAIL_ADDRESS, EMAIL_PASSWORD,
                email, subject, body,
                resume_file, pdf_name
            )
            
            if sent:
                print("Email Sent")
                time.sleep(2)
            else:
                print("Email Error")

def menu_scrape_google():
    print("GOOGLE SEARCH SCRAPER")
    keyword = input("Keyword to search: ")
    try:
        count = int(input("Max results (default 10): ") or 10)
    except:
        count = 10
        
    print(f"Scraping Google for '{keyword}' ({count} results)...")
    results = google_scraper.scrape_google_search(keyword, num_results=count)
    
    if not results:
        print("No results found.")
        return

    filename = f"leads_google_{keyword}.xlsx"
    filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in ['_','.']]).rstrip()
    
    save_data(results, filename)

def menu_main():
    # 1. Setup Email (First, as requested)
    setup_email()
    
    # 2. Setup AI (Interactive)
    setup_ai_interactive()
    
    # Reload smart updater config
    smart_applier.configure_keys()
    
    # 3. Setup User Info
    setup_user_info()
    
    while True:
        print("\n=== AUTO-JOB APPLIER ===")
        print("1. [SCRAPE] Recuperer des entreprises depuis Google Maps (et filtrer)")
        print("2. [FILTER] Nettoyer un fichier Excel/CSV existant (Garder que les agences web)")
        print("3. [APPLY BASIC] Envoyer emails (Mode Simple)")
        print("4. [APPLY SMART] Envoyer emails (Analayse Site + Lettre Perso + Recherche Auto)")
        print("5. [CHAT] Discuter avec l'IA")
        print("6. [TEST] Verifier la connexion aux modeles IA")
        print("8. [SCRAPE] Recuperer depuis Google Search (Selenium)")
        print("7. Quitter")
        
        c = input("Votre choix: ")
        
        if c == '1':
            menu_scrape()
        elif c == '2':
            menu_validate_excel()
        elif c == '3':
            menu_apply()
        elif c == '4':
            smart_applier.run_smart_apply(AI_CLIENT, AI_MODEL)
        elif c == '5':
            smart_applier.chat_with_ai()
        elif c == '7':
            break
        elif c == '6':
            smart_applier.test_models()
        elif c == '8':
            menu_scrape_google()

if __name__ == "__main__":
    menu_main()
