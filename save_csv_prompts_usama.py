#!/usr/bin/env python3
"""
Script untuk menyimpan prompt dari file CSV komentar Facebook Usama Akram.
File berisi 10 teknik prompt engineering.
"""

import csv
import os
import sys
import json
from datetime import datetime

# Path ke database prompt
PROMPTS_DIR = "/root/.openclaw/workspace/prompts"
INDEX_FILE = os.path.join(PROMPTS_DIR, "INDEX.md")
COUNTER_FILE = os.path.join(PROMPTS_DIR, "COUNTER.txt")

# Fungsi untuk membaca counter
def read_counter():
    try:
        with open(COUNTER_FILE, 'r') as f:
            return int(f.read().strip())
    except:
        return 0

# Fungsi untuk menulis counter
def write_counter(value):
    with open(COUNTER_FILE, 'w') as f:
        f.write(str(value))

# Fungsi untuk menentukan kategori berdasarkan konten
def determine_category(content):
    content_lower = content.lower()
    
    # Keyword mapping untuk kategori
    keywords = {
        "PE": ["learn", "study", "skill", "education", "teaching", "student", "practice"],
        "DM": ["marketing", "campaign", "growth", "viral", "twitter", "social", "audience"],
        "CC": ["write", "copy", "content", "creative", "story", "narrative"],
        "DEV": ["code", "programming", "api", "react", "node", "sql", "technical"],
        "BIZ": ["business", "strategy", "plan", "cto", "cm", "board", "stake"],
        "OPS": ["workflow", "process", "efficiency", "system", "automation"]
    }
    
    # Hitung skor untuk setiap kategori
    scores = {}
    for category, cat_keywords in keywords.items():
        score = 0
        for keyword in cat_keywords:
            if keyword in content_lower:
                score += 1
        scores[category] = score
    
    # Ambil kategori dengan skor tertinggi
    best_category = max(scores, key=scores.get)
    
    # Jika semua skor 0, default ke PE (Personal Education)
    if scores[best_category] == 0:
        return "PE"
    
    return best_category

# Fungsi untuk menyimpan prompt ke file kategori
def save_prompt_to_category(prompt_id, title, content, category, level="⭐ Starter"):
    category_file = os.path.join(PROMPTS_DIR, f"{category}.md")
    
    # Format metadata
    metadata = f"""## {prompt_id}: {title}

**Level:** {level}
**Category:** {category}
**Date:** {datetime.now().strftime('%Y-%m-%d')}
**Tags:** prompt-engineering, ai-techniques, usama-akram

---

{content}

---
"""
    
    # Tambahkan ke file kategori
    with open(category_file, 'a', encoding='utf-8') as f:
        f.write(metadata + "\n\n")
    
    return True

# Fungsi untuk update INDEX.md
def update_index(prompt_id, title, category):
    index_entry = f"- **{prompt_id}** | {title} | `{category}` | {datetime.now().strftime('%Y-%m-%d')}\n"
    
    with open(INDEX_FILE, 'a', encoding='utf-8') as f:
        f.write(index_entry)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 save_csv_prompts_usama.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    if not os.path.exists(csv_file):
        print(f"Error: File {csv_file} tidak ditemukan")
        sys.exit(1)
    
    # Baca file CSV
    prompts = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Filter hanya komentar dari Usama Akram yang mengandung "Step"
            if row['Author'] == 'Usama Akram' and 'Step' in row['Content']:
                prompts.append(row)
    
    print(f"Found {len(prompts)} prompts from Usama Akram")
    
    # Baca counter saat ini
    current_counter = read_counter()
    
    # Proses setiap prompt
    saved_count = 0
    for i, prompt in enumerate(prompts):
        content = prompt['Content']
        
        # Ekstrak judul dari konten (baris pertama)
        lines = content.split('\n')
        title = lines[0].strip() if lines else f"Prompt {i+1}"
        
        # Tentukan kategori
        category = determine_category(content)
        
        # Generate ID
        prompt_id = f"P-{str(current_counter + i + 1).zfill(3)}"
        
        # Simpan ke kategori
        save_prompt_to_category(prompt_id, title, content, category)
        
        # Update index
        update_index(prompt_id, title, category)
        
        print(f"✅ Saved: {prompt_id} | 📂 {category} | {title[:50]}...")
        saved_count += 1
    
    # Update counter
    if saved_count > 0:
        new_counter = current_counter + saved_count
        write_counter(new_counter)
        print(f"\n📊 Total prompts in database: {new_counter}")
    
    return saved_count

if __name__ == "__main__":
    saved = main()
    print(f"\n🎉 Successfully saved {saved} prompts to database")