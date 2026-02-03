import subprocess
import sys

def install_dependencies():
    print("\n--- DEPENDENCY CHECK ---")
    print("Do you want to check and install missing libraries? (y/n)")
    choice = input("Choice: ").strip().lower()

    if choice != 'y':
        print("Skipping dependency check.\n")
        return

    print("Checking and installing dependencies...")
    packages = [
        "pandas", "selenium", "webdriver-manager", "beautifulsoup4", 
        "requests", "python-dotenv", "pypdf", "openpyxl", 
        "azure-ai-inference", "azure-core", "fpdf",
        "reportlab", "duckduckgo-search"
    ]
    
    for package in packages:
        try:
            # Handle naming differences for import vs pip
            module_name = package
            if package == "python-dotenv": module_name = "dotenv"
            if package == "azure-ai-inference": module_name = "azure.ai.inference"
            if package == "azure-core": module_name = "azure.core"
            
            __import__(module_name)
        except ImportError:
            print(f"Installing {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            except:
                print(f"Failed to install {package}. Please install manually.")
            
    print("Dependency check complete.\n")

if __name__ == "__main__":
    install_dependencies()
