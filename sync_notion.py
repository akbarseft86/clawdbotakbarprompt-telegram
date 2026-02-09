#!/usr/bin/env python3
import sys, os, re
from pathlib import Path
from notion_client import Client

NOTION_TOKEN = 'ntn_c90917954465cJcLWiJOj28p5lzyR5wEdG7tLqs56Ltb52'
PROMPTS_DIR = Path('~/.openclaw/workspace/prompts_v2').expanduser()
CONFIG_FILE = Path('~/.openclaw/workspace/notion_db_id.txt').expanduser()

def get_database_id():
    if not CONFIG_FILE.exists():
        return None
    return CONFIG_FILE.read_text().strip()

def set_database_id(db_id):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(db_id.strip())

def parse_prompts():
    prompts = []
    for md_file in PROMPTS_DIR.glob('*.md'):
        try:
            content = md_file.read_text(encoding='utf-8')
            for block in content.split('---'):
                if not block.strip():
                    continue
                
                lines = block.strip().split('\n')
                data = {}
                in_prompt = False
                prompt_lines = []
                
                for line in lines:
                    if line.strip().lower().startswith('prompt:'):
                        in_prompt = True
                        rest = line.split(':', 1)[1].strip()
                        if rest and rest != '|':
                            prompt_lines.append(rest)
                    elif in_prompt:
                        if any(line.strip().lower().startswith(k) for k in ['notes:', 'tags:', 'category:']):
                            in_prompt = False
                        else:
                            prompt_lines.append(line.strip().lstrip('| '))
                    elif ':' in line:
                        key, val = line.split(':', 1)
                        data[key.strip().lower()] = val.strip()
                
                data['prompt_text'] = '\n'.join(prompt_lines).strip()
                
                if data.get('title') and data.get('slug'):
                    prompts.append({
                        'title': data.get('title', 'Untitled'),
                        'slug': data.get('slug', 'unknown'),
                        'category': data.get('category', 'Uncategorized'),
                        'pack': data.get('pack_slug', 'none'),
                        'prompt': data.get('prompt_text', 'No content'),
                        'tags': [t.strip() for t in data.get('tags', '').split(',') if t.strip()]
                    })
        except Exception as e:
            print(f'Error parsing {md_file}: {e}')
            continue
    
    return prompts

def sync_to_notion(database_id):
    notion = Client(auth=NOTION_TOKEN)
    prompts = parse_prompts()
    
    if not prompts:
        return '❌ Tidak ada prompt ditemukan di ~/.openclaw/workspace/prompts_v2/'
    
    # Clear existing entries (archive them)
    try:
        results = notion.databases.query(database_id=database_id)
        for page in results.get('results', [])[:50]:
            notion.pages.update(page_id=page['id'], archived=True)
    except Exception:
        pass
    
    # Insert new entries - use lowercase 'title' for Notion's default property
    success_count = 0
    for p in prompts:
        try:
            # Create page with title only (Notion default property)
            page = notion.pages.create(
                parent={'database_id': database_id},
                properties={
                    'title': {'title': [{'text': {'content': f"{p['title'][:80]} [{p['slug'][:30]}]"}}]}
                },
                # Add prompt content as page body
                children=[
                    {
                        'object': 'block',
                        'type': 'heading_2',
                        'heading_2': {'rich_text': [{'type': 'text', 'text': {'content': f"Category: {p['category']}"}}]}
                    },
                    {
                        'object': 'block',
                        'type': 'paragraph',
                        'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': f"Pack: {p['pack']}"}}]}
                    },
                    {
                        'object': 'block',
                        'type': 'divider',
                        'divider': {}
                    },
                    {
                        'object': 'block',
                        'type': 'paragraph',
                        'paragraph': {'rich_text': [{'type': 'text', 'text': {'content': p['prompt'][:2000]}}]}
                    }
                ]
            )
            success_count += 1
        except Exception as e:
            print(f'Failed to sync {p["slug"]}: {e}')
    
    return f'✅ Synced {success_count}/{len(prompts)} prompts to Notion'

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: sync_notion.py [sync|set-db <id>|test]')
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == 'set-db':
        if len(sys.argv) < 3:
            print('Usage: sync_notion.py set-db <database_id>')
            sys.exit(1)
        db_id = sys.argv[2]
        set_database_id(db_id)
        print(f'✅ Database ID saved: {db_id}')
    
    elif cmd == 'sync':
        db_id = get_database_id()
        if not db_id:
            print('❌ Database ID belum diset. Gunakan: sync_notion.py set-db <id>')
            sys.exit(1)
        result = sync_to_notion(db_id)
        print(result)
    
    elif cmd == 'test':
        notion = Client(auth=NOTION_TOKEN)
        me = notion.users.me()
        print(f'✅ Connected as: {me.get("name", "Unknown")}')
    
    else:
        print(f'Unknown command: {cmd}')
        sys.exit(1)
