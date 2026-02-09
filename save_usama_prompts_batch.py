#!/usr/bin/env python3
"""
Batch save Usama Akram prompts using prompt_db_manager.py
"""

import csv
import subprocess
import sys

def main():
    csv_file = "/root/.openclaw/media/inbound/file_14---65a32e0c-3935-4d9a-860d-a002fe482140.csv"
    
    prompts = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Author'] == 'Usama Akram' and 'Step' in row['Content']:
                prompts.append(row)
    
    print(f"Processing {len(prompts)} prompts...")
    
    for i, prompt in enumerate(prompts):
        content = prompt['Content']
        lines = content.split('\n')
        title = lines[0].strip() if lines else f"Step {i+1}"
        
        # Clean title for command line
        clean_title = title.replace('"', '\\"').replace("'", "\\'")
        clean_content = content.replace('"', '\\"').replace("'", "\\'")
        
        # Build command
        cmd = f'python3 /root/.openclaw/scripts/prompt_db_manager.py save "{clean_title}" "{clean_content}"'
        
        print(f"\nSaving prompt {i+1}: {title[:50]}...")
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Success: {result.stdout.strip()}")
            else:
                print(f"❌ Error: {result.stderr}")
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    print(f"\n🎉 Processed {len(prompts)} prompts")

if __name__ == "__main__":
    main()