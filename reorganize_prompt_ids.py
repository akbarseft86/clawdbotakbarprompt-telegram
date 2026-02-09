#!/usr/bin/env python3
"""
Script untuk merapikan ID prompt setelah penghapusan duplikat.
"""

import os
import re
import glob

PROMPTS_DIR = "/root/.openclaw/workspace/prompts"
CATEGORIES = ["PE", "DM", "CC", "DEV", "BIZ", "OPS"]

def read_file_content(filepath):
    """Membaca konten file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def write_file_content(filepath, content):
    """Menulis konten ke file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def get_all_prompts():
    """Mendapatkan semua prompt dari semua kategori."""
    all_prompts = []
    
    for category in CATEGORIES:
        filepath = os.path.join(PROMPTS_DIR, f"{category}.md")
        if os.path.exists(filepath):
            content = read_file_content(filepath)
            
            # Pattern untuk menemukan setiap prompt section
            pattern = r'---\s*\nid: (P-\d{3})\s*\n(.*?)\n---'
            sections = re.findall(pattern, content, re.DOTALL)
            
            for prompt_id, section_content in sections:
                # Ekstrak title dari section
                title_match = re.search(r'title: (.*?)\s*\n', section_content)
                title = title_match.group(1) if title_match else "Unknown"
                
                all_prompts.append({
                    'id': prompt_id,
                    'category': category,
                    'content': section_content,
                    'full_section': f"---\nid: {prompt_id}\n{section_content}\n---",
                    'title': title
                })
    
    # Urutkan berdasarkan ID
    all_prompts.sort(key=lambda x: int(x['id'].split('-')[1]))
    
    return all_prompts

def update_prompt_ids(prompts):
    """Update ID prompt agar berurutan."""
    new_prompts = []
    
    for i, prompt in enumerate(prompts, 1):
        old_id = prompt['id']
        new_id = f"P-{str(i).zfill(3)}"
        
        if old_id != new_id:
            print(f"  Renaming: {old_id} -> {new_id}")
            
            # Update ID dalam content
            new_content = prompt['content'].replace(f"id: {old_id}", f"id: {new_id}")
            
            new_prompts.append({
                'id': new_id,
                'category': prompt['category'],
                'content': new_content,
                'full_section': f"---\nid: {new_id}\n{new_content}\n---",
                'title': prompt['title']
            })
        else:
            new_prompts.append(prompt)
    
    return new_prompts

def rewrite_category_files(prompts):
    """Tulis ulang file kategori dengan prompt yang sudah di-update."""
    # Kelompokkan prompt berdasarkan kategori
    prompts_by_category = {cat: [] for cat in CATEGORIES}
    
    for prompt in prompts:
        prompts_by_category[prompt['category']].append(prompt)
    
    # Tulis ulang setiap file kategori
    for category in CATEGORIES:
        filepath = os.path.join(PROMPTS_DIR, f"{category}.md")
        
        if prompts_by_category[category]:
            # Buat header
            content = f"# {category} Prompts\n\n"
            
            # Tambahkan setiap prompt
            for prompt in prompts_by_category[category]:
                content += prompt['full_section'] + "\n\n"
            
            write_file_content(filepath, content)
            print(f"  Updated {category}.md with {len(prompts_by_category[category])} prompts")
        else:
            # File kosong
            write_file_content(filepath, f"# {category} Prompts\n\n")
            print(f"  Created empty {category}.md")

def update_index_file(prompts):
    """Update INDEX.md dengan ID baru."""
    index_lines = ["# INDEX Prompt\n\n"]
    
    for prompt in prompts:
        index_line = f"- **{prompt['id']}** | {prompt['title'][:50]}... | `{prompt['category']}` | 2026-02-08\n"
        index_lines.append(index_line)
    
    index_file = os.path.join(PROMPTS_DIR, "INDEX.md")
    write_file_content(index_file, ''.join(index_lines))
    print(f"  Updated INDEX.md with {len(prompts)} entries")

def update_counter_file(prompts):
    """Update COUNTER.txt dengan jumlah total prompt."""
    counter_file = os.path.join(PROMPTS_DIR, "COUNTER.txt")
    write_file_content(counter_file, str(len(prompts)))
    print(f"  Updated COUNTER.txt to {len(prompts)}")

def main():
    print("🔢 Reorganizing prompt IDs after cleanup...")
    
    # Dapatkan semua prompt
    prompts = get_all_prompts()
    print(f"Found {len(prompts)} total prompts")
    
    # Tampilkan distribusi kategori
    category_counts = {}
    for prompt in prompts:
        cat = prompt['category']
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    print("\n📊 Current distribution:")
    for cat in CATEGORIES:
        count = category_counts.get(cat, 0)
        print(f"  {cat}: {count} prompts")
    
    # Update ID prompt
    print("\n🔄 Updating prompt IDs...")
    updated_prompts = update_prompt_ids(prompts)
    
    # Tulis ulang file
    print("\n📝 Rewriting category files...")
    rewrite_category_files(updated_prompts)
    
    # Update index dan counter
    print("\n📋 Updating index and counter...")
    update_index_file(updated_prompts)
    update_counter_file(updated_prompts)
    
    print(f"\n✅ Successfully reorganized {len(updated_prompts)} prompts")
    print(f"   New ID range: P-001 to P-{str(len(updated_prompts)).zfill(3)}")

if __name__ == "__main__":
    main()