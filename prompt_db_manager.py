#!/usr/bin/env python3
"""
Prompt Database Manager - Real File-Based Storage
NO HALLUCINATION - All data from actual .md files
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path

# Constants
PROMPTS_DIR = Path.home() / ".openclaw" / "workspace" / "prompts"
COUNTER_FILE = PROMPTS_DIR / "COUNTER.txt"
INDEX_FILE = PROMPTS_DIR / "INDEX.md"

# Category keywords for auto-classification
CATEGORY_KEYWORDS = {
    "PE": ["system prompt", "persona", "role", "framework", "chain of thought", "few-shot", "template", "optimize", "ai system"],
    "DM": ["ads", "iklan", "seo", "keyword", "email marketing", "funnel", "landing page", "campaign", "conversion", "digital marketing"],
    "CC": ["caption", "konten", "copywriting", "headline", "artikel", "blog", "script", "hook", "storytelling", "content"],
    "DEV": ["code", "debug", "api", "database", "deploy", "server", "python", "javascript", "react", "backend", "frontend", "coding"],
    "BIZ": ["freelance", "client", "pricing", "proposal", "bisnis", "produk", "offer", "pitch", "invoice", "business"],
    "OPS": ["automasi", "workflow", "setup", "tools", "productivity", "sop", "spreadsheet", "automation"]
}

def load_counter() -> int:
    """Load current counter value"""
    try:
        with open(COUNTER_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 0

def save_counter(n: int) -> None:
    """Save counter value"""
    with open(COUNTER_FILE, "w") as f:
        f.write(str(n))

def classify_prompt(text: str) -> str:
    """Auto-classify prompt into category based on keywords"""
    text_lower = text.lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[cat] = score
    
    # Return category with highest score, default to PE
    best_cat = max(scores, key=scores.get)
    return best_cat if scores[best_cat] > 0 else "PE"

def generate_title(text: str) -> str:
    """Generate short title from prompt text"""
    # Take first 50 chars, clean up
    title = text[:50].replace("\n", " ").strip()
    if len(text) > 50:
        title += "..."
    return title

def append_prompt(category: str, title: str, prompt_text: str, 
                  level: str = "⭐ Starter", sub_tag: str = "",
                  model: str = "gpt-4.1-nano", temp: float = 0.3,
                  bahasa: str = "id", komersial: str = "🟢 Public",
                  tags: str = "", catatan: str = "") -> dict:
    """Append new prompt to category file and return entry info"""
    
    # Get next ID
    counter = load_counter() + 1
    prompt_id = f"P-{counter:03d}"
    
    # Get current date
    tanggal = datetime.now().strftime("%Y-%m-%d")
    
    # Build entry
    entry = f"""---
id: {prompt_id}
title: {title}
category: {category}
level: {level}
sub_tag: {sub_tag or category.lower()}
model: {model}
temp: {temp}
bahasa: {bahasa}
komersial: {komersial}
tags: {tags}
tanggal: {tanggal}

isi_prompt: |
  {prompt_text.replace(chr(10), chr(10) + "  ")}

catatan: |
  {catatan or "Tidak ada catatan"}
---

"""
    
    # Append to category file
    cat_file = PROMPTS_DIR / f"{category}.md"
    with open(cat_file, "a", encoding="utf-8") as f:
        f.write(entry)
    
    # Update INDEX.md
    with open(INDEX_FILE, "a", encoding="utf-8") as f:
        f.write(f"| {prompt_id} | {title[:30]} | {category} | {level} | {tanggal} |\n")
    
    # Update counter
    save_counter(counter)
    
    return {
        "id": prompt_id,
        "title": title,
        "category": category,
        "level": level,
        "tanggal": tanggal
    }

def parse_entries(content: str) -> list:
    """Parse all entries from a .md file content"""
    entries = []
    # Split by --- markers
    blocks = re.split(r"^---\s*$", content, flags=re.MULTILINE)
    
    for block in blocks:
        if not block.strip():
            continue
        
        entry = {}
        # Parse key-value pairs
        lines = block.strip().split("\n")
        current_key = None
        current_value = []
        
        for line in lines:
            # Check for key: value pattern
            match = re.match(r"^(\w+):\s*(.*)$", line)
            if match and not line.startswith("  "):
                # Save previous key if exists
                if current_key:
                    entry[current_key] = "\n".join(current_value).strip()
                current_key = match.group(1)
                current_value = [match.group(2)] if match.group(2) and match.group(2) != "|" else []
            elif current_key and (line.startswith("  ") or line.strip() == ""):
                current_value.append(line.strip())
        
        # Save last key
        if current_key:
            entry[current_key] = "\n".join(current_value).strip()
        
        if entry.get("id"):
            entries.append(entry)
    
    return entries

def get_prompt_by_id(prompt_id: str) -> dict:
    """Find and return prompt by ID"""
    prompt_id = prompt_id.upper()
    
    for cat in ["PE", "DM", "CC", "DEV", "BIZ", "OPS"]:
        cat_file = PROMPTS_DIR / f"{cat}.md"
        if cat_file.exists():
            with open(cat_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            entries = parse_entries(content)
            for entry in entries:
                if entry.get("id", "").upper() == prompt_id:
                    return entry
    
    return None

def list_prompts(category: str = None) -> dict:
    """List all prompts, optionally filtered by category"""
    result = {"total": 0, "by_category": {}}
    
    categories = [category.upper()] if category else ["PE", "DM", "CC", "DEV", "BIZ", "OPS"]
    
    for cat in categories:
        cat_file = PROMPTS_DIR / f"{cat}.md"
        if cat_file.exists():
            with open(cat_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            entries = parse_entries(content)
            result["by_category"][cat] = [
                {"id": e.get("id"), "title": e.get("title", ""), "level": e.get("level", "")}
                for e in entries
            ]
            result["total"] += len(entries)
    
    return result

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: prompt_db_manager.py <command> [args]"}))
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        if command == "save":
            # Save new prompt: save <prompt_text>
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Missing prompt text"}))
                sys.exit(1)
            
            prompt_text = " ".join(sys.argv[2:])
            category = classify_prompt(prompt_text)
            title = generate_title(prompt_text)
            
            result = append_prompt(category, title, prompt_text)
            print(json.dumps({"success": True, **result}))
        
        elif command == "get":
            # Get prompt by ID: get P-001
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Missing prompt ID"}))
                sys.exit(1)
            
            prompt_id = sys.argv[2]
            entry = get_prompt_by_id(prompt_id)
            
            if entry:
                print(json.dumps({"success": True, "entry": entry}))
            else:
                print(json.dumps({"success": False, "error": f"Prompt {prompt_id} tidak ditemukan"}))
        
        elif command == "list":
            # List prompts: list [category]
            category = sys.argv[2] if len(sys.argv) > 2 else None
            result = list_prompts(category)
            print(json.dumps({"success": True, **result}))
        
        elif command == "counter":
            # Get current counter
            print(json.dumps({"counter": load_counter()}))
        
        else:
            print(json.dumps({"error": f"Unknown command: {command}"}))
            sys.exit(1)
    
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
