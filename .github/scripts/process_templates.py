import os
import re
import json
import zipfile
import shutil
from bs4 import BeautifulSoup

TEMPLATES_JSON = "templates.json"
IMPORT_DIR = "templates-to-import"
CATEGORIES = ["landing", "ecommerce", "corporate"]

def ensure_templates_json():
    if not os.path.exists(TEMPLATES_JSON):
        with open(TEMPLATES_JSON, "w") as f:
            json.dump({cat: {} for cat in CATEGORIES}, f, indent=2)

def detect_category_from_name(zip_name):
    name_lower = zip_name.lower()
    if any(k in name_low for k in ["landing", "lp", "one-page"]):
        return "landing"
    if any(k in name_low for k in ["ecom", "shop", "store"]):
        return "ecommerce"
    if any(k in name_low for k in ["corp", "corporate", "business"]):
        return "corporate"
    return "landing"  # default

def add_variables_to_html(html_content):
    # Replace common static texts with placeholders
    replacements = [
        (r"(\b|\W)(\+?[0-9\s\-\(\)]{8,20})(\b|\W)", r"\1{{phone}}\3"),
        (r"(\b|\W)([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(\b|\W)", r"\1{{email}}\3"),
        (r"(\b|\W)([A-Z][a-zA-Z\s]+(?:Inc|LLC|Ltd|Company|Studio)?)(?=\s*[\n<]|\s*$)", r"\1{{business_name}}\3", re.IGNORECASE),
        (r"(\d{1,5}\s+\w+.*?[,.]\s*\w+)", r"{{address}}"),
        (r"([A-Z][a-z]+(?:burg|grad|city|town|ville)?)(?=\s*[,.\n<])", r"{{city}}"),
    ]
    for pattern, repl, *flags in replacements:
        flags = flags[0] if flags else 0
        html_content = re.sub(pattern, repl, html_content, flags=flags)
    # Also add missing placeholders if not present
    required = ["{{business_name}}", "{{phone}}", "{{email}}", "{{address}}", "{{city}}"]
    for ph in required:
        if ph not in html_content:
            html_content += f"\n<!-- {ph} -->"
    return html_content

def process_zip(zip_path):
    folder_name = os.path.splitext(os.path.basename(zip_path))[0]
    extract_path = os.path.join("temp_extract", folder_name)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_path)
    # find index.html
    index_path = None
    for root, dirs, files in os.walk(extract_path):
        if "index.html" in files:
            index_path = os.path.join(root, "index.html")
            break
    if not index_path:
        shutil.rmtree(extract_path)
        return None
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()
    html = add_variables_to_html(html)
    # Determine category
    category = detect_category_from_name(folder_name)
    dest_dir = os.path.join(category, folder_name)
    os.makedirs(dest_dir, exist_ok=True)
    # copy all extracted files? For simplicity, only copy index.html
    shutil.copy(index_path, os.path.join(dest_dir, "index.html"))
    # update templates.json
    with open(TEMPLATES_JSON, "r") as f:
        data = json.load(f)
    data[category][folder_name] = f"https://raw.githubusercontent.com/UNIQUE-STUDIO/website-templates/main/{category}/{folder_name}/index.html"
    with open(TEMPLATES_JSON, "w") as f:
        json.dump(data, f, indent=2)
    # clean up
    shutil.rmtree(extract_path)
    return category

def main():
    ensure_templates_json()
    if not os.path.exists(IMPORT_DIR):
        os.makedirs(IMPORT_DIR, exist_ok=True)
        print("No zip files to process.")
        return
    for file in os.listdir(IMPORT_DIR):
        if file.endswith(".zip"):
            zip_path = os.path.join(IMPORT_DIR, file)
            print(f"Processing {zip_path}...")
            result = process_zip(zip_path)
            if result:
                os.remove(zip_path)
                print(f"✅ Processed {file} as {result}")
            else:
                print(f"❌ Failed to process {file}")

if __name__ == "__main__":
    main()
