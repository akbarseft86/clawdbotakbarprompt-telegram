#!/usr/bin/env python3
"""Audit all prompts in Notion - check content quality."""
import asyncio, httpx, re, os

NOTION_TOKEN = "ntn_c90917954465cJcLWiJOj28p5lzyR5wEdG7tLqs56Ltb52"
NOTION_DB_ID = "30121de9-c9f6-80d1-955a-d15ca6c86eff"
HEADERS = {
    "Authorization": "Bearer " + NOTION_TOKEN,
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def extract_text(block):
    bt = block["type"]
    if bt in block and "rich_text" in block.get(bt, {}):
        rt = block[bt]["rich_text"]
        if rt:
            return "".join(r.get("text", {}).get("content", "") for r in rt)
    return ""

async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.notion.com/v1/databases/" + NOTION_DB_ID + "/query",
            headers=HEADERS, json={"page_size": 100}
        )
        pages = resp.json().get("results", [])
        print("Pages:", len(pages))
        print("=" * 110)

        for page in pages:
            pid = page["id"]
            # Get title
            raw_title = "?"
            for pn, pv in page["properties"].items():
                if pv.get("type") == "title":
                    tl = pv.get("title", [])
                    if tl:
                        raw_title = "".join(r.get("text", {}).get("content", "") for r in tl)
                    break

            # Get blocks
            bresp = await client.get(
                "https://api.notion.com/v1/blocks/" + pid + "/children",
                headers=HEADERS
            )
            blocks = bresp.json().get("results", [])

            # Parse content
            past_div = False
            content = ""
            for b in blocks:
                if b["type"] == "divider":
                    past_div = True
                    continue
                txt = extract_text(b)
                if past_div and txt:
                    content += txt + "\n"

            clen = len(content.strip())
            has_catatan = content.strip().endswith("Tidak ada catatan")
            short = clen < 100

            flag = ""
            if has_catatan:
                flag += " [CATATAN]"
            if short:
                flag += " [SHORT]"
            if not content.strip():
                flag += " [EMPTY]"

            print("%-60s | %4d chars%s" % (raw_title[:60], clen, flag))

asyncio.run(main())
