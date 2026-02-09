#!/usr/bin/env python3
from notion_client import Client

NOTION_TOKEN = 'ntn_c90917954465cJcLWiJOj28p5lzyR5wEdG7tLqs56Ltb52'

try:
    notion = Client(auth=NOTION_TOKEN)
    me = notion.users.me()
    print(f'✅ Connected to Notion as: {me.get("name", "Unknown")}')
    print(f'User ID: {me.get("id")}')
except Exception as e:
    print(f'❌ Error: {e}')
