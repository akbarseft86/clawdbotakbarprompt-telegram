#!/usr/bin/env python3
"""
Script untuk membersihkan prompt duplikat dengan format JSON yang salah di kategori DEV.
"""

import os
import re

DEV_FILE = "/root/.openclaw/workspace/prompts/DEV.md"
PE_FILE = "/root/.openclaw/workspace/prompts/PE.md"
INDEX_FILE = "/root/.openclaw/workspace/prompts/INDEX.md"

def read_file_content(filepath):
    """Membaca konten file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def write_file_content(filepath, content):
    """Menulis konten ke file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def extract_prompt_sections(content):
    """Ekstrak semua section prompt dari konten file."""
    # Pattern untuk menemukan setiap prompt section
    pattern = r'---\s*\nid: (P-\d{3})\s*\n(.*?)\n---'
    sections = re.findall(pattern, content, re.DOTALL)
    
    prompts = {}
    for prompt_id, section_content in sections:
        prompts[prompt_id] = section_content
    
    return prompts

def is_json_format_prompt(content):
    """Cek apakah prompt dalam format JSON yang salah."""
    return '"title": "' in content and '"category": "' in content

def get_duplicate_prompt_ids(dev_prompts, pe_prompts):
    """Identifikasi prompt ID yang duplikat antara DEV dan PE."""
    duplicate_ids = []
    
    for prompt_id in dev_prompts:
        if prompt_id in ['P-010', 'P-011', 'P-012', 'P-013', 'P-014', 'P-015', 'P-016', 'P-017']:
            # Cek apakah ini format JSON
            content = dev_prompts[prompt_id]
            if is_json_format_prompt(content):
                duplicate_ids.append(prompt_id)
    
    return duplicate_ids

def remove_prompts_from_dev(dev_content, prompt_ids_to_remove):
    """Hapus prompt dari file DEV.md."""
    lines = dev_content.split('\n')
    new_lines = []
    i = 0
    skip_section = False
    current_prompt_id = None
    
    while i < len(lines):
        line = lines[i]
        
        # Cek jika ini awal section dengan ID yang harus dihapus
        if line.strip() == '---' and i + 1 < len(lines):
            next_line = lines[i + 1]
            if next_line.startswith('id: '):
                prompt_id = next_line.split(': ')[1].strip()
                if prompt_id in prompt_ids_to_remove:
                    skip_section = True
                    current_prompt_id = prompt_id
                    print(f"  Removing prompt {prompt_id}...")
        
        # Jika tidak dalam section yang di-skip, tambahkan ke new_lines
        if not skip_section:
            new_lines.append(line)
        
        # Cek jika ini akhir section
        if line.strip() == '---' and skip_section:
            skip_section = False
            current_prompt_id = None
        
        i += 1
    
    return '\n'.join(new_lines)

def update_index_file(prompt_ids_to_remove):
    """Update INDEX.md dengan menghapus entri untuk prompt yang dihapus."""
    index_content = read_file_content(INDEX_FILE)
    lines = index_content.split('\n')
    new_lines = []
    
    for line in lines:
        # Cek jika line mengandung prompt ID yang harus dihapus
        should_keep = True
        for prompt_id in prompt_ids_to_remove:
            if prompt_id in line:
                should_keep = False
                print(f"  Removing index entry for {prompt_id}")
                break
        
        if should_keep:
            new_lines.append(line)
    
    write_file_content(INDEX_FILE, '\n'.join(new_lines))

def main():
    print("🔍 Scanning for duplicate JSON-formatted prompts in DEV category...")
    
    # Baca konten file
    dev_content = read_file_content(DEV_FILE)
    pe_content = read_file_content(PE_FILE)
    
    # Ekstrak prompt sections
    dev_prompts = extract_prompt_sections(dev_content)
    pe_prompts = extract_prompt_sections(pe_content)
    
    print(f"Found {len(dev_prompts)} prompts in DEV category")
    print(f"Found {len(pe_prompts)} prompts in PE category")
    
    # Identifikasi duplikat
    duplicate_ids = get_duplicate_prompt_ids(dev_prompts, pe_prompts)
    
    if not duplicate_ids:
        print("✅ No duplicate JSON-formatted prompts found.")
        return
    
    print(f"\n🚨 Found {len(duplicate_ids)} duplicate JSON-formatted prompts:")
    for pid in duplicate_ids:
        print(f"  - {pid}")
    
    print("\n🧹 Cleaning up duplicates...")
    
    # Hapus dari DEV.md
    cleaned_dev_content = remove_prompts_from_dev(dev_content, duplicate_ids)
    write_file_content(DEV_FILE, cleaned_dev_content)
    
    # Update INDEX.md
    update_index_file(duplicate_ids)
    
    print(f"\n✅ Successfully removed {len(duplicate_ids)} duplicate prompts:")
    for pid in duplicate_ids:
        print(f"  - {pid}")
    
    # Hitung ulang prompt di DEV
    new_dev_content = read_file_content(DEV_FILE)
    new_dev_prompts = extract_prompt_sections(new_dev_content)
    print(f"\n📊 DEV category now has {len(new_dev_prompts)} prompts (was {len(dev_prompts)})")

if __name__ == "__main__":
    main()