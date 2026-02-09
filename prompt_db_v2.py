#!/usr/bin/env python3
import sys, re
from pathlib import Path

PROMPTS_DIR = Path.home() / ".openclaw" / "workspace" / "prompts"

# Category emoji mapping
CATEGORY_EMOJI = {
    "LP": "🏠", "MKT": "📢", "CNT": "✍️", "CC": "✍️",
    "EML": "📧", "DEV": "💻", "BIZ": "💼", "PE": "📚",
    "DM": "📱", "OPS": "⚙️"
}

def get_category_emoji(category):
    return CATEGORY_EMOJI.get(category.upper(), "📝")

def search_packs_by_topic(query):
    packs = {}
    query_lower = query.lower()
    
    for md_file in PROMPTS_DIR.glob("*.md"):
        category = md_file.stem.upper()
        try:
            content = md_file.read_text(encoding="utf-8")
            for block in content.split("---"):
                if not block.strip():
                    continue
                    
                lines = block.strip().split("\n")
                data = {}
                for line in lines:
                    if ":" in line:
                        key, val = line.split(":", 1)
                        data[key.strip().lower()] = val.strip()
                
                title = data.get("title", "")
                tags = data.get("tags", "")
                id_field = data.get("id", "")
                pack_slug = data.get("pack_slug", data.get("slug", ""))
                
                # Generate slug from title or id if not present
                if not pack_slug and title:
                    pack_slug = re.sub(r'[^a-z0-9]+', '-', title.lower())[:50].strip('-')
                if not pack_slug and id_field:
                    pack_slug = id_field.lower()
                
                if query_lower in title.lower() or query_lower in tags.lower() or query_lower in category.lower():
                    if pack_slug:
                        if pack_slug not in packs:
                            packs[pack_slug] = {
                                "pack_slug": pack_slug,
                                "pack_title": title[:50],
                                "category": category,
                                "count": 0
                            }
                        packs[pack_slug]["count"] += 1
        except Exception:
            continue
    
    return list(packs.values())

def format_prompt_packs(query, packs):
    if not packs:
        return f"❌ Tidak ada prompt untuk: {query}"
    
    lines = [f"🎯 Prompt: {query}", f"📦 {len(packs)} paket ditemukan", "─" * 25, ""]
    
    slugs = []
    for i, pack in enumerate(packs[:10], 1):
        slug = pack["pack_slug"]
        title = pack["pack_title"]
        count = pack["count"]
        category = pack.get("category", "")
        emoji = get_category_emoji(category)
        
        if count > 1:
            lines.append(f"{i}. {emoji} {title} ({count} prompt)")
        else:
            lines.append(f"{i}. {emoji} {title}")
        
        slugs.append(slug)
    
    lines.append("")
    lines.append("─" * 25)
    lines.append("💡 Balas dengan nomor untuk lihat isi")
    lines.append("")
    lines.append("---SLUGS---")
    lines.extend(slugs)
    
    return "\n".join(lines)

def list_pack(pack_slug):
    prompts = []
    category = ""
    
    for md_file in PROMPTS_DIR.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            for block in content.split("---"):
                if f"pack_slug: {pack_slug}" in block or f"slug: {pack_slug}" in block:
                    lines = block.strip().split("\n")
                    data = {}
                    for line in lines:
                        if ":" in line:
                            key, val = line.split(":", 1)
                            data[key.strip().lower()] = val.strip()
                    
                    if not category:
                        category = md_file.stem.upper()
                    
                    prompts.append({
                        "slug": data.get("slug", "unknown"),
                        "title": data.get("title", "Untitled")
                    })
        except Exception:
            continue
    
    return {"pack_slug": pack_slug, "prompts": prompts, "category": category}

def format_pack_detail(pack):
    pack_slug = pack["pack_slug"]
    prompts = pack["prompts"]
    category = pack.get("category", "")
    emoji = get_category_emoji(category)
    
    if not prompts:
        return f"❌ Tidak ada prompt di paket: {pack_slug}"
    
    lines = [f"📦 {emoji} {pack_slug}", f"📝 {len(prompts)} prompt tersedia", "─" * 25, ""]
    
    slugs = []
    for i, p in enumerate(prompts[:15], 1):
        slug = p["slug"]
        title = p["title"][:50]
        lines.append(f"{i}. {title}")
        slugs.append(slug)
    
    lines.append("")
    lines.append("─" * 25)
    lines.append("💡 Balas dengan nomor untuk pakai prompt")
    lines.append("")
    lines.append("---SLUGS---")
    lines.extend(slugs)
    
    return "\n".join(lines)

def get_prompt_by_slug(slug):
    """Return clean prompt content."""
    slug_lower = slug.lower().strip()
    
    for md_file in PROMPTS_DIR.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
            for block in content.split("---"):
                if f"slug: {slug_lower}" in block.lower() or f"id: {slug_lower}" in block.lower():
                    title_match = re.search(r"title:\s*(.+)", block, re.IGNORECASE)
                    title = title_match.group(1).strip() if title_match else slug
                    
                    # Try isi_prompt field first
                    isi_match = re.search(r"isi_prompt:\s*\|?\s*\n(.*?)(?=\n\w+:|$)", block, re.DOTALL | re.IGNORECASE)
                    if isi_match:
                        prompt_text = isi_match.group(1).strip()
                        # Clean up indentation
                        lines = [l.strip() for l in prompt_text.split("\n") if l.strip()]
                        prompt_text = "\n".join(lines)
                        if prompt_text and "tidak ada catatan" not in prompt_text.lower():
                            return {"title": title, "slug": slug, "prompt": prompt_text}
                    
                    # Fallback to prompt: field
                    in_prompt = False
                    prompt_lines = []
                    
                    for line in block.split("\n"):
                        line_stripped = line.strip()
                        line_lower = line_stripped.lower()
                        
                        if line_lower.startswith("prompt:"):
                            in_prompt = True
                            rest = line.split(":", 1)[1].strip()
                            if rest and rest != "|":
                                prompt_lines.append(rest)
                            continue
                        
                        if in_prompt:
                            if any(line_lower.startswith(x) for x in ["notes:", "tags:", "category:", "slug:", "title:", "pack_slug:", "catatan:"]):
                                break
                            if line_stripped == "---":
                                break
                            
                            cleaned = line_stripped.lstrip("|").strip()
                            if cleaned and "tidak ada catatan" not in cleaned.lower():
                                prompt_lines.append(cleaned)
                    
                    prompt_text = "\n".join(prompt_lines).strip()
                    
                    if prompt_text:
                        return {"title": title, "slug": slug, "prompt": prompt_text}
        except Exception:
            continue
    return None

def list_all_categories():
    """List all categories with prompt counts."""
    categories = {}
    
    for md_file in PROMPTS_DIR.glob("*.md"):
        if md_file.stem in ["INDEX", "COUNTER"]:
            continue
        category = md_file.stem.upper()
        try:
            content = md_file.read_text(encoding="utf-8")
            count = content.count("---") // 2
            if count > 0:
                categories[category] = count
        except Exception:
            continue
    
    if not categories:
        return "❌ Tidak ada kategori"
    
    lines = ["📂 Semua Kategori", "─" * 25, ""]
    
    for cat, count in sorted(categories.items()):
        emoji = get_category_emoji(cat)
        lines.append(f"{emoji} {cat}: {count} prompt")
    
    lines.append("")
    lines.append("─" * 25)
    lines.append("💡 Ketik: list [kategori] untuk lihat isi")
    
    return "\n".join(lines)

def list_category(category):
    """List all prompts in a category."""
    category_upper = category.upper()
    md_file = PROMPTS_DIR / f"{category_upper}.md"
    
    if not md_file.exists():
        return f"❌ Kategori tidak ditemukan: {category}"
    
    prompts = []
    try:
        content = md_file.read_text(encoding="utf-8")
        for block in content.split("---"):
            if not block.strip():
                continue
            
            lines = block.strip().split("\n")
            data = {}
            for line in lines:
                if ":" in line:
                    key, val = line.split(":", 1)
                    data[key.strip().lower()] = val.strip()
            
            if data.get("title"):
                prompts.append({
                    "slug": data.get("slug", data.get("id", "unknown")),
                    "title": data.get("title", "Untitled")
                })
    except Exception as e:
        return f"❌ Error: {e}"
    
    if not prompts:
        return f"❌ Tidak ada prompt di kategori: {category}"
    
    emoji = get_category_emoji(category_upper)
    lines = [f"📂 {emoji} Kategori: {category_upper}", f"📝 {len(prompts)} prompt", "─" * 25, ""]
    
    slugs = []
    for i, p in enumerate(prompts[:15], 1):
        title = p["title"][:50]
        lines.append(f"{i}. {title}")
        slugs.append(p["slug"])
    
    if len(prompts) > 15:
        lines.append(f"... dan {len(prompts) - 15} lainnya")
    
    lines.append("")
    lines.append("─" * 25)
    lines.append("💡 Balas dengan nomor untuk pakai prompt")
    lines.append("")
    lines.append("---SLUGS---")
    lines.extend(slugs)
    
    return "\n".join(lines)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: prompt_db_v2.py [command] ...")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "search-packs":
        query = sys.argv[2] if len(sys.argv) > 2 else "landing"
        packs = search_packs_by_topic(query)
        print(format_prompt_packs(query, packs))
    
    elif cmd == "list-pack":
        pack_slug = sys.argv[2] if len(sys.argv) > 2 else ""
        pack = list_pack(pack_slug)
        print(format_pack_detail(pack))
    
    elif cmd == "get":
        slug = sys.argv[2] if len(sys.argv) > 2 else ""
        prompt = get_prompt_by_slug(slug)
        if not prompt:
            print(f"❌ Prompt tidak ditemukan: {slug}")
            sys.exit(1)
        title = prompt["title"]
        print(f"🎯 {title}")
        print("─" * 40)
        print(prompt["prompt"])
    
    elif cmd == "list-all":
        print(list_all_categories())
    
    elif cmd == "list-category":
        category = sys.argv[2] if len(sys.argv) > 2 else ""
        print(list_category(category))
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
