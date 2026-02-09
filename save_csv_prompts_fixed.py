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

def save_prompt_directly(prompt_data, index):
    """Simpan prompt langsung ke file kategori"""
    title = prompt_data['title']
    prompt_text = prompt_data['prompt']
    category = classify_prompt(prompt_text)
    
    # Baca counter
    counter_file = '/root/.openclaw/workspace/prompts/COUNTER.txt'
    with open(counter_file, 'r') as f:
        counter = int(f.read().strip())
    
    # Generate ID
    prompt_id = f"P-{counter + index:03d}"
    
    # Format metadata
    metadata = f"""---
id: {prompt_id}
title: {title}
category: {category}
level: ⭐ Starter
sub_tag: {category.lower()}
model: gpt-4.1-nano
temp: "0.3"
bahasa: id
komersial: 🟢 Public
tags: learning,education,skill-development
tanggal: {datetime.now().strftime('%Y-%m-%d')}
---

{prompt_text}

---
catatan: From CSV file, author: {prompt_data['author']}, reactions: {prompt_data['reactions']}
"""
    
    # Simpan ke file kategori
    category_file = f'/root/.openclaw/workspace/prompts/{category}.md'
    
    # Baca file jika ada, tambahkan prompt baru
    if os.path.exists(category_file):
        with open(category_file, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = f"# {category} - Category\n\n"
    
    # Tambahkan prompt baru
    with open(category_file, 'w', encoding='utf-8') as f:
        f.write(content + '\n\n' + metadata)
    
    # Update INDEX.md
    index_file = '/root/.openclaw/workspace/prompts/INDEX.md'
    index_entry = f"- **{prompt_id}** | {title} | {category} | ⭐ Starter | {datetime.now().strftime('%Y-%m-%d')}\n"
    
    with open(index_file, 'a', encoding='utf-8') as f:
        f.write(index_entry)
    
    return prompt_id

def main():
    if len(sys.argv) < 2:
        print("Usage: python save_csv_prompts_fixed.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    
    if not os.path.exists(csv_file):
        print(f"❌ File not found: {csv_file}")
        sys.exit(1)
    
    print(f"📖 Processing CSV file: {csv_file}")
    prompts = extract_prompts_from_csv(csv_file)
    
    print(f"📊 Found {len(prompts)} prompts")
    
    saved_ids = []
    for i, prompt in enumerate(prompts, 1):
        print(f"\n--- Prompt {i}: {prompt['title']} ---")
        print(f"Category: {classify_prompt(prompt['prompt'])}")
        print(f"Preview: {prompt['prompt'][:100]}...")
        
        prompt_id = save_prompt_directly(prompt, i)
        saved_ids.append(prompt_id)
        print(f"✅ Saved as: {prompt_id}")
    
    # Update counter
    counter_file = '/root/.openclaw/workspace/prompts/COUNTER.txt'
    with open(counter_file, 'r') as f:
        current_counter = int(f.read().strip())
    
    new_counter = current_counter + len(prompts)
    with open(counter_file, 'w') as f:
        f.write(str(new_counter))
    
    print(f"\n🎯 Summary: {len(prompts)} prompts saved successfully")
    print(f"📈 New counter: {new_counter}")
    print(f"📋 Saved IDs: {', '.join(saved_ids)}")

if __name__ == '__main__':
    main()