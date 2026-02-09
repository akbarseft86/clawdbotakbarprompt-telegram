#!/usr/bin/env python3
import sys, os, json
from notion_client import Client
from pathlib import Path

NOTION_TOKEN = 'ntn_c90917954465cJcLWiJOj28p5lzyR5wEdG7tLqs56Ltb52'
CONFIG_FILE = Path('~/.openclaw/workspace/notion_db_id.txt').expanduser()

def get_db_id():
    if not CONFIG_FILE.exists():
        return None
    return CONFIG_FILE.read_text().strip()

def extract_text(prop, prop_type):
    """Extract text from Notion property."""
    if not prop:
        return ''
    if prop_type == 'title':
        items = prop.get('title', [])
        return items[0].get('text', {}).get('content', '') if items else ''
    elif prop_type == 'rich_text':
        items = prop.get('rich_text', [])
        return items[0].get('text', {}).get('content', '') if items else ''
    elif prop_type == 'select':
        sel = prop.get('select')
        return sel.get('name', '') if sel else ''
    return ''

def search_prompts(query):
    db_id = get_db_id()
    if not db_id:
        return [], "❌ Database ID belum diset. Ketik: set notion db: [ID]"
    
    notion = Client(auth=NOTION_TOKEN)
    query_lower = query.lower()
    
    # Use search API to find pages containing query
    try:
        results = notion.search(
            filter={'property': 'object', 'value': 'page'},
            query=query
        )
    except Exception as e:
        return [], f"❌ Error: {e}"
    
    prompts = []
    for page in results.get('results', []):
        # Only include pages from our database
        parent = page.get('parent', {})
        # Handle both database_id and data_source_id parent types
        parent_db_id = parent.get('database_id', '')
        if not parent_db_id:
            continue
        if parent_db_id.replace('-', '') != db_id.replace('-', ''):
            continue
            
        props = page.get('properties', {})
        
        # Extract title from 'title' property (might be named differently)
        title = '?'
        for prop_name, prop_val in props.items():
            if prop_val.get('type') == 'title':
                titles = prop_val.get('title', [])
                if titles:
                    title = titles[0].get('plain_text', '?')
                break
        
        prompts.append({
            'id': page['id'],
            'title': title[:60]
        })
    
    return prompts, None

def get_prompt_by_id(page_id):
    """Get full prompt content by page ID."""
    notion = Client(auth=NOTION_TOKEN)
    
    try:
        page = notion.pages.retrieve(page_id=page_id)
        props = page.get('properties', {})
        title = extract_text(props.get('title'), 'title')
        
        # Get page content (children blocks)
        blocks = notion.blocks.children.list(block_id=page_id)
        content_lines = []
        
        for block in blocks.get('results', []):
            block_type = block.get('type')
            if block_type == 'paragraph':
                texts = block.get('paragraph', {}).get('rich_text', [])
                for t in texts:
                    content_lines.append(t.get('text', {}).get('content', ''))
            elif block_type == 'heading_2':
                texts = block.get('heading_2', {}).get('rich_text', [])
                for t in texts:
                    content_lines.append(t.get('text', {}).get('content', ''))
        
        return {
            'title': title,
            'prompt': '\n'.join(content_lines)
        }
    except Exception as e:
        return None

def format_results(query, prompts):
    if not prompts:
        return f"❌ Tidak ada prompt untuk '{query}'.", []
    
    lines = [f"🎯 Prompt: {query}", f"📝 {len(prompts)} hasil", "─" * 25, ""]
    
    ids = []
    for i, p in enumerate(prompts[:15], 1):
        lines.append(f"{i}. {p['title']}")
        ids.append(p['id'])
    
    lines.append("")
    lines.append("─" * 25)
    lines.append("💡 Balas dengan nomor untuk lihat isi")
    
    return '\n'.join(lines), ids

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: notion_prompt_manager.py [search|get] ...')
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == 'search':
        query = sys.argv[2] if len(sys.argv) > 2 else 'landing'
        prompts, error = search_prompts(query)
        if error:
            print(error)
            sys.exit(1)
        
        text, ids = format_results(query, prompts)
        print(text)
        print('---IDS---')
        for pid in ids:
            print(pid)
    
    elif cmd == 'get':
        page_id = sys.argv[2] if len(sys.argv) > 2 else ''
        prompt = get_prompt_by_id(page_id)
        if not prompt:
            print(f"❌ Prompt tidak ditemukan.")
            sys.exit(1)
        
        print(f"📝 {prompt['title']}")
        print("─" * 40)
        print(prompt['prompt'])
    
    else:
        print(f'Unknown command: {cmd}')
        sys.exit(1)
