#!/usr/bin/env python3
"""
Script untuk mencari prompt berdasarkan slug.
"""

import yaml
import re
from pathlib import Path

PROMPTS_V2_DIR = Path.home() / ".openclaw" / "workspace" / "prompts_v2"

def get_prompt_by_slug(slug: str):
    """Find prompt by slug"""
    slug = slug.lower()
    
    for filepath in PROMPTS_V2_DIR.glob("*.md"):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Split by YAML delimiters
        blocks = re.split(r'^---\s*$', content, flags=re.MULTILINE)
        
        for block in blocks:
            if not block.strip() or block.strip().startswith("#"):
                continue
            
            try:
                data = yaml.safe_load(block)
                if data and isinstance(data, dict):
                    if data.get("slug", "").lower() == slug:
                        return data
            except:
                continue
    
    return None

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("❌ Missing slug argument")
        sys.exit(1)
    
    slug = sys.argv[1]
    prompt = get_prompt_by_slug(slug)
    
    if prompt:
        print(f"✅ Prompt ditemukan: {prompt.get('title', '')}")
        print(f"📝 Slug: {prompt.get('slug', '')}")
        print(f"📂 Kategori: {prompt.get('category', '')}")
        print(f"📦 Pack: {prompt.get('pack_slug', '')}")
        print(f"\n🎯 PROMPT:\n{prompt.get('prompt', '')}")
        
        if prompt.get("notes"):
            print(f"\n📝 Catatan:\n{prompt.get('notes', '')}")
    else:
        print(f"❌ Prompt dengan slug '{slug}' tidak ditemukan")

if __name__ == "__main__":
    main()