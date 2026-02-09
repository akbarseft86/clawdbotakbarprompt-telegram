#!/usr/bin/env python3
import csv
import re
import json
import sys
import os
from datetime import datetime

def extract_prompts_from_csv(csv_file):
    prompts = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            content = row['Content']
            author = row['Author']
            
            # Cari pattern prompt (angka diikuti titik dan judul)
            if re.match(r'^\d+\.\s+[A-Za-z]', content):
                # Ekstrak judul dan prompt
                lines = content.split('\n')
                title_line = lines[0].strip()
                
                # Cari bagian "Prompt:" 
                prompt_text = ""
                in_prompt_section = False
                for line in lines:
                    if 'Prompt:' in line:
                        in_prompt_section = True
                        prompt_text = line.replace('Prompt:', '').strip()
                    elif in_prompt_section:
                        if line.strip().startswith('💎'):
                            break
                        prompt_text += '\n' + line.strip()
                
                if prompt_text:
                    # Bersihkan prompt dari emoji dan link promosi
                    prompt_text = re.sub(r'💎.*$', '', prompt_text, flags=re.DOTALL).strip()
                    
                    prompts.append({
                        'title': title_line,
                        'prompt': prompt_text,
                        'author': author,
                        'reactions': int(row['ReactionsCount']) if row['ReactionsCount'] else 0
                    })
    
    return prompts

def classify_prompt(prompt_text):
    """Klasifikasi prompt berdasarkan keyword"""
    prompt_lower = prompt_text.lower()
    
    # Keyword untuk kategori
    if any(keyword in prompt_lower for keyword in ['learn', 'roadmap', 'plan', 'beginner', 'starter', 'improve', 'practice', 'exercise', 'mistake', 'test', 'understanding', 'teach', 'explain']):
        return 'PE'  # Personal Education
    elif any(keyword in prompt_lower for keyword in ['copy', 'headline', 'writing', 'content', 'social', 'email']):
        return 'CC'  # Content Creation
    elif any(keyword in prompt_lower for keyword in ['code', 'html', 'css', 'tailwind', 'developer', 'frontend', 'api', 'script']):
        return 'DEV'  # Development
    elif any(keyword in prompt_lower for keyword in ['business', 'offer', 'pricing', 'proposal', 'saas', 'product']):
        return 'BIZ'  # Business
    elif any(keyword in prompt_lower for keyword in ['marketing', 'ads', 'landing', 'conversion', 'cta', 'hero']):
        return 'DM'  # Digital Marketing
    else:
        return 'OPS'  # Operations

def save_prompt_to_db(prompt_data, index):
    """Simpan prompt ke database menggunakan prompt_db_manager.py"""
    title = prompt_data['title']
    prompt_text = prompt_data['prompt']
    category = classify_prompt(prompt_text)
    
    # Buat slug dari judul
    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    
    # Metadata
    metadata = {
        'title': title[:100] + '...' if len(title) > 100 else title,
        'category': category,
        'level': '⭐ Starter',
        'sub_tag': category.lower(),
        'model': 'gpt-4.1-nano',
        'temp': '0.3',
        'bahasa': 'id',
        'komersial': '🟢 Public',
        'tags': 'learning,education,skill-development',
        'tanggal': datetime.now().strftime('%Y-%m-%d'),
        'isi_prompt': prompt_text,
        'catatan': f"From CSV file, author: {prompt_data['author']}, reactions: {prompt_data['reactions']}"
    }
    
    # Simpan menggunakan prompt_db_manager.py
    import subprocess
    cmd = [
        'python3', '/root/.openclaw/scripts/prompt_db_manager.py',
        'save',
        json.dumps(metadata, ensure_ascii=False)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Prompt {index} saved: {title}")
            return True
        else:
            print(f"❌ Failed to save prompt {index}: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error saving prompt {index}: {str(e)}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python process_csv_prompts.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    if not os.path.exists(csv_file):
        print(f"❌ File not found: {csv_file}")
        sys.exit(1)
    
    print(f"📖 Processing CSV file: {csv_file}")
    prompts = extract_prompts_from_csv(csv_file)
    
    print(f"📊 Found {len(prompts)} prompts")
    
    saved_count = 0
    for i, prompt in enumerate(prompts, 1):
        print(f"\n--- Prompt {i}: {prompt['title']} ---")
        print(f"Category: {classify_prompt(prompt['prompt'])}")
        print(f"Preview: {prompt['prompt'][:100]}...")
        
        if save_prompt_to_db(prompt, i):
            saved_count += 1
    
    print(f"\n🎯 Summary: {saved_count}/{len(prompts)} prompts saved successfully")

if __name__ == '__main__':
    main()