#!/usr/bin/env python3
"""
Final cleanup untuk menghapus sisa prompt JSON di kategori DEV.
"""

import os
import re

DEV_FILE = "/root/.openclaw/workspace/prompts/DEV.md"
INDEX_FILE = "/root/.openclaw/workspace/prompts/INDEX.md"

def read_file_content(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def write_file_content(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def remove_json_prompts_from_dev():
    """Hapus prompt dengan format JSON dari DEV.md."""
    dev_content = read_file_content(DEV_FILE)
    
    # Pattern untuk menemukan prompt dengan format JSON
    pattern = r'---\s*\nid: (P-01[0-3])\s*\n.*?"title": ".*?"\s*\n.*?\n---'
    
    # Cari semua prompt JSON
    json_prompts = re.findall(pattern, dev_content, re.DOTALL)
    
    if not json_prompts:
        print("No JSON-formatted prompts found in DEV.md")
        return []
    
    print(f"Found {len(json_prompts)} JSON-formatted prompts: {json_prompts}")
    
    # Hapus setiap prompt JSON
    for prompt_id in json_prompts:
        # Pattern spesifik untuk prompt ini
        prompt_pattern = rf'---\s*\nid: {prompt_id}\s*\n.*?\n---'
        dev_content = re.sub(prompt_pattern, '', dev_content, flags=re.DOTALL)
        print(f"  Removed {prompt_id}")
    
    # Bersihkan spasi berlebih
    dev_content = re.sub(r'\n{3,}', '\n\n', dev_content)
    
    write_file_content(DEV_FILE, dev_content)
    return json_prompts

def update_index_file(prompt_ids):
    """Update INDEX.md dengan menghapus entri untuk prompt yang dihapus."""
    index_content = read_file_content(INDEX_FILE)
    lines = index_content.split('\n')
    new_lines = []
    
    removed_count = 0
    for line in lines:
        should_keep = True
        for prompt_id in prompt_ids:
            if prompt_id in line:
                should_keep = False
                removed_count += 1
                print(f"  Removed index entry for {prompt_id}")
                break
        
        if should_keep:
            new_lines.append(line)
    
    write_file_content(INDEX_FILE, '\n'.join(new_lines))
    return removed_count

def recount_prompts():
    """Hitung ulang total prompt dan update counter."""
    prompts_dir = "/root/.openclaw/workspace/prompts"
    categories = ["PE", "DM", "CC", "DEV", "BIZ", "OPS"]
    
    total_prompts = 0
    for category in categories:
        filepath = os.path.join(prompts_dir, f"{category}.md")
        if os.path.exists(filepath):
            content = read_file_content(filepath)
            # Hitung jumlah prompt berdasarkan pattern 'id: P-'
            count = len(re.findall(r'id: P-\d{3}', content))
            total_prompts += count
            print(f"  {category}: {count} prompts")
    
    # Update counter
    counter_file = os.path.join(prompts_dir, "COUNTER.txt")
    write_file_content(counter_file, str(total_prompts))
    
    return total_prompts

def main():
    print("🧹 Final cleanup of JSON-formatted prompts...")
    
    # Hapus prompt JSON dari DEV.md
    removed_prompt_ids = remove_json_prompts_from_dev()
    
    if not removed_prompt_ids:
        print("✅ No cleanup needed.")
        return
    
    # Update INDEX.md
    print("\n📋 Updating index file...")
    removed_index_count = update_index_file(removed_prompt_ids)
    
    # Hitung ulang dan update counter
    print("\n🔢 Recounting prompts...")
    total_prompts = recount_prompts()
    
    print(f"\n✅ Cleanup completed:")
    print(f"   Removed {len(removed_prompt_ids)} prompts from DEV.md")
    print(f"   Removed {removed_index_count} entries from INDEX.md")
    print(f"   Total prompts in database: {total_prompts}")

if __name__ == "__main__":
    main()