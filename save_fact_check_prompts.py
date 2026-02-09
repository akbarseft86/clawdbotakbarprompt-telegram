#!/usr/bin/env python3
"""
Script untuk menyimpan prompt fact-check dari file CSV Chris KE.
"""

import csv
import subprocess
import sys
import re

def clean_text(text):
    """Bersihkan teks untuk command line."""
    # Hapus emoji dan karakter khusus
    text = re.sub(r'[🔴🟢🟡🔵🟣🟠⚫⚪🟤🟥🟧🟨🟩🟦🟪🟫▪︎•]', '', text)
    # Escape quotes
    text = text.replace('"', '\\"').replace("'", "\\'")
    # Hapus multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def main():
    csv_file = "/root/.openclaw/media/inbound/file_16---a1559415-267b-4f0f-ae49-99b71d615a92.csv"
    
    prompts = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Filter hanya komentar dari Chris KE yang mengandung angka dan titik
            if row['Author'] == 'Chris KE' and re.match(r'^\d+️⃣', row['Content']):
                prompts.append(row)
    
    print(f"Found {len(prompts)} fact-check prompts from Chris KE")
    
    # Buat pack text
    pack_title = "Fact-Check & Research Prompts"
    pack_text = pack_title + "\n\n"
    
    for i, prompt in enumerate(prompts):
        content = prompt['Content']
        
        # Ekstrak judul (baris pertama sebelum line break)
        lines = content.split('\n')
        title_line = lines[0].strip()
        
        # Bersihkan judul
        title = clean_text(title_line)
        
        # Bersihkan konten
        clean_content = clean_text(content)
        
        # Tambahkan ke pack text
        pack_text += f"{i+1}) {title}\n{clean_content}\n\n"
    
    # Simpan sebagai pack
    cmd = f'python3 /root/.openclaw/scripts/prompt_db_v2.py save-pack "{pack_text}"'
    
    print(f"\nSaving fact-check pack with {len(prompts)} prompts...")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Success: {result.stdout}")
        else:
            print(f"❌ Error: {result.stderr}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print(f"\n🎉 Processed {len(prompts)} fact-check prompts as pack")

if __name__ == "__main__":
    main()