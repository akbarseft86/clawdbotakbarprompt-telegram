#!/usr/bin/env python3
"""
Remove remaining JSON-formatted prompts from DEV.md
"""

import re

def main():
    with open('/root/.openclaw/workspace/prompts/DEV.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern untuk menemukan prompt dengan format JSON
    # Mencari section yang dimulai dengan --- dan mengandung {"title":
    pattern = r'---\s*\nid: P-01[0-3]\s*\n.*?{\\?"title\\?":.*?\n---'
    
    # Hapus semua prompt JSON
    new_content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # Bersihkan spasi berlebih
    new_content = re.sub(r'\n{3,}', '\n\n', new_content)
    
    with open('/root/.openclaw/workspace/prompts/DEV.md', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Removed remaining JSON-formatted prompts from DEV.md")

if __name__ == "__main__":
    main()