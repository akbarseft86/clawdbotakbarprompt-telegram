#!/usr/bin/env python3
"""
Migration script: Convert P-XXX format to V2 slug-based format
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime

# Import V2 functions
import sys
sys.path.insert(0, str(Path.home() / ".openclaw" / "scripts"))
from prompt_db_v2 import save_prompt, ensure_structure

OLD_PROMPTS_DIR = Path.home() / ".openclaw" / "workspace" / "prompts"

# Category mapping: old -> hint for new
CATEGORY_MAP = {
    "PE": "marketing-ads",
    "DM": "marketing-ads", 
    "CC": "content-social",
    "DEV": "coding-automation",
    "BIZ": "business-offer",
    "OPS": "coding-automation"
}

def parse_old_entries(content):
    """Parse old P-XXX format entries"""
    entries = []
    
    # Split by --- separator
    blocks = re.split(r'^---\s*$', content, flags=re.MULTILINE)
    
    for block in blocks:
        if not block.strip():
            continue
        
        entry = {}
        lines = block.strip().split('\n')
        
        for line in lines:
            # Skip headers
            if line.startswith('#'):
                continue
            
            # Parse key: value
            match = re.match(r'^(\w+):\s*(.*)$', line)
            if match:
                key = match.group(1)
                val = match.group(2).strip()
                entry[key] = val
            elif 'isi_prompt' in entry and line.strip():
                # Multi-line prompt continuation
                entry['isi_prompt'] = entry.get('isi_prompt', '') + '\n' + line.strip()
        
        if entry.get('id') and entry.get('id').startswith('P-'):
            entries.append(entry)
    
    return entries

def migrate():
    """Run migration"""
    ensure_structure()
    
    stats = {"total": 0, "migrated": 0, "by_category": {}}
    
    for old_file in OLD_PROMPTS_DIR.glob("*.md"):
        if old_file.name in ["INDEX.md", "COUNTER.txt"]:
            continue
        
        old_category = old_file.stem  # PE, DM, CC, etc
        content = old_file.read_text()
        entries = parse_old_entries(content)
        
        for entry in entries:
            old_id = entry.get("id", "")
            title = entry.get("title", f"Prompt {old_id}")
            prompt_text = entry.get("isi_prompt", "")
            
            if not prompt_text:
                continue
            
            # Use category hint for mapping
            hint = CATEGORY_MAP.get(old_category)
            
            try:
                result = save_prompt(title, prompt_text, hint)
                stats["migrated"] += 1
                
                cat = result.get("category", "Unknown")
                stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
                
                print(f"✅ {old_id} -> {result['slug']} ({cat})")
            except Exception as e:
                print(f"❌ {old_id}: {e}")
            
            stats["total"] += 1
    
    print("\n" + "="*50)
    print("MIGRATION COMPLETE")
    print("="*50)
    print(f"Total entries: {stats['total']}")
    print(f"Migrated: {stats['migrated']}")
    print("\nBy category:")
    for cat, count in stats["by_category"].items():
        print(f"  - {cat}: {count}")
    
    return stats

if __name__ == "__main__":
    print("Starting migration from P-XXX to V2...")
    print("="*50)
    migrate()
