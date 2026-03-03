import os
import re
import fitz  # PyMuPDF
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

manual_cache = {}

def clean_thai_text(text):
    if not text: return ""
    text = re.sub(r'(?<=[\u0e00-\u0e7f])\s+(?=[\u0e00-\u0e7f])', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_manual_path(model):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(current_dir, "manuals")
    if not os.path.exists(base_dir): return None

    possible_filenames = [
        f"{model}_Manual.pdf",
        f"{model}_Manual.pdf.pdf",
        f"{model.upper()}.pdf",
        f"{model.lower()}.pdf"
    ]

    for filename in possible_filenames:
        full_path = os.path.join(base_dir, filename)
        if os.path.exists(full_path):
            return full_path
    return None

def preload_manuals():
    global manual_cache
    models = ["G6", "X9"]
    for model in models:
        path = get_manual_path(model)
        if path:
            try:
                doc = fitz.open(path)
                pages_data = []
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    text = page.get_text()
                    pages_data.append({
                        "page": page_num + 1,
                        "text": clean_thai_text(text)
                    })
                manual_cache[model] = pages_data
                print(f"✅ โหลด {model} สำเร็จ! ({len(pages_data)} หน้า)")
            except Exception as e:
                print(f"❌ ไม่สามารถอ่านไฟล์ {model}: {e}")

# --- เพิ่มส่วนการเข้าถึงไฟล์ PDF ผ่านลิงก์ ---
@app.route('/view/<model>')
def view_pdf(model):
    path = get_manual_path(model)
    if not path:
        return "File not found", 404
    directory = os.path.dirname(path)
    filename = os.path.basename(path)
    return send_from_directory(directory, filename)

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    query = data.get('query', '').strip()
    model = data.get('model', 'G6')
    
    if not query: return jsonify([])

    content = manual_cache.get(model)
    if not content:
        return jsonify({"error": f"ไม่มีข้อมูลคู่มือรุ่น {model}"}), 404

    search_query_clean = query.replace(" ", "").lower()
    results = []
    
    for item in content:
        if search_query_clean in item['text'].replace(" ", "").lower():
            results.append({
                "page": item['page'],
                "text": item['text'],
                "model": model # ส่ง model กลับไปด้วยเพื่อสร้างลิงก์
            })
    
    return jsonify(results[:20])

if __name__ == '__main__':
    preload_manuals()
    print("🚀 Backend พร้อมทำงานที่ http://127.0.0.1:5000")
    app.run(debug=False, port=5000)