#!/usr/bin/env python3
"""
Telegram Bot for OpenClaw + Notion Prompt DB
─────────────────────────────────────────────
- prompt [topik]  → langsung tampilkan semua isi prompt dari Notion
- simpan: Judul\nIsi  → simpan prompt ke Notion
- /reload  → refresh cache Notion
- Chat biasa  → forward ke OpenClaw AI
"""
import os, re, json, subprocess, logging, asyncio, time
import requests, httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# === CONFIG ===================================================================
TELEGRAM_TOKEN = "8267317513:AAEJP_an1LSOq4N6oDn-YP9nnH0FpP5ol0M"
OPENCLAW_HOST  = "http://127.0.0.1:18789"
OPENCLAW_TOKEN = "6b833e046e3c2f36b9aae4c5134ee56bdf4a9a04dc1f054d"
SWITCH_MODE_SCRIPT = "/root/.openclaw/scripts/switch_mode.sh"
FIXED_PATH = "/root/.nvm/versions/node/v22.22.0/bin:/usr/local/bin:/usr/bin:/bin"

# === AI MODEL CONFIG (langsung ke DeepSeek, bukan lewat OpenClaw gateway) ===
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = "sk-72e5d53c4468437687d5f3afe383b3b0"
AI_MODEL = "deepseek-chat"  # DeepSeek V3 — jauh lebih pintar dari gpt-4.1-nano

NOTION_TOKEN = "ntn_c90917954465cJcLWiJOj28p5lzyR5wEdG7tLqs56Ltb52"
NOTION_DB_ID  = "30121de9-c9f6-80d1-955a-d15ca6c86eff"
NOTION_HEADERS = {
    "Authorization": "Bearer " + NOTION_TOKEN,
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO)
log = logging.getLogger("bot")

# === NOTION PROMPT CACHE =====================================================
notion_prompts_cache = []

# Per-user conversation history for contextual responses
# Format: {user_id: [{"role": "user"/"assistant", "content": "..."}]}
conversation_history = {}
MAX_HISTORY = 10  # Keep last 10 messages per user


def add_to_history(user_id, role, content):
    """Add a message to user's conversation history."""
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    conversation_history[user_id].append({"role": role, "content": content})
    # Keep only last MAX_HISTORY messages
    if len(conversation_history[user_id]) > MAX_HISTORY:
        conversation_history[user_id] = conversation_history[user_id][-MAX_HISTORY:]


def get_history(user_id):
    """Get user's conversation history."""
    return conversation_history.get(user_id, [])


async def load_notion_prompts():
    """Load all prompts from Notion DB into memory cache."""
    global notion_prompts_cache
    if not NOTION_TOKEN or not NOTION_DB_ID:
        log.warning("Notion credentials missing, skipping load.")
        return

    prompts = []
    has_more = True
    next_cursor = None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            log.info("Loading prompts from Notion DB: %s", NOTION_DB_ID)

            while has_more:
                payload = {"page_size": 100}
                if next_cursor:
                    payload["start_cursor"] = next_cursor

                resp = await client.post(
                    "https://api.notion.com/v1/databases/" + NOTION_DB_ID + "/query",
                    headers=NOTION_HEADERS, json=payload
                )
                if resp.status_code != 200:
                    log.error("Notion query failed: %s", resp.text)
                    break

                data = resp.json()
                pages = data.get("results", [])
                has_more = data.get("has_more", False)
                next_cursor = data.get("next_cursor")

                for page in pages:
                    prompt = await _parse_notion_page(client, page)
                    if prompt:
                        prompts.append(prompt)

            # De-duplicate by slug: keep the one with longest content
            seen = {}
            for p in prompts:
                s = p["slug"]
                if s not in seen or len(p["content"]) > len(seen[s]["content"]):
                    seen[s] = p
            prompts = list(seen.values())

            notion_prompts_cache = prompts
            log.info("Loaded %d prompts from Notion.", len(prompts))
    except Exception as e:
        log.error("Error loading Notion prompts: %s", e)


async def _parse_notion_page(client, page):
    """Parse a single Notion page into a prompt dict."""
    page_id = page["id"]
    props = page["properties"]

    # Extract title from any title-type property
    raw_title = "Untitled"
    for pname, pval in props.items():
        if pval.get("type") == "title":
            t_list = pval.get("title", [])
            if t_list:
                raw_title = "".join(rt.get("text", {}).get("content", "") for rt in t_list)
            break

    # Extract [slug] from title
    slug_match = re.search(r'\[([^\]]+)\]', raw_title)
    if slug_match:
        slug = slug_match.group(1).strip()
        display_title = raw_title[:slug_match.start()].strip().rstrip('\u2013').rstrip('-').strip()
    else:
        slug = re.sub(r'[^a-z0-9]+', '-', raw_title.lower()).strip('-')
        display_title = raw_title

    # Get page blocks (content)
    try:
        content_resp = await client.get(
            "https://api.notion.com/v1/blocks/" + page_id + "/children",
            headers=NOTION_HEADERS
        )
    except Exception:
        return None

    category = ""
    pack = ""
    prompt_content = ""
    past_divider = False

    if content_resp.status_code == 200:
        blocks = content_resp.json().get("results", [])
        for block in blocks:
            b_type = block["type"]
            block_text = _extract_block_text(block)

            if b_type == "divider":
                past_divider = True
                continue

            if not past_divider:
                if block_text.startswith("Category:"):
                    category = block_text.replace("Category:", "").strip()
                elif block_text.startswith("Pack:"):
                    pack = block_text.replace("Pack:", "").strip()
            else:
                if block_text:
                    prompt_content += block_text + "\n"

    # Clean content
    prompt_content = prompt_content.strip()

    # Remove trailing "Tidak ada catatan"
    if prompt_content.endswith("Tidak ada catatan"):
        prompt_content = prompt_content[:-len("Tidak ada catatan")].strip()

    # Strip surrounding single/double quotes from content
    if len(prompt_content) >= 2:
        if (prompt_content[0] == "'" and prompt_content[-1] == "'") or \
           (prompt_content[0] == '"' and prompt_content[-1] == '"'):
            prompt_content = prompt_content[1:-1].strip()

    # Skip empty or too-short prompts (< 50 chars = dummy/test data)
    if len(prompt_content) < 50:
        return None

    # Limit display_title to max 80 chars
    if len(display_title) > 80:
        display_title = display_title[:77] + "..."

    return {
        "title": display_title,
        "content": prompt_content,
        "category": category,
        "slug": slug,
        "pack": pack,
        "source": "notion",
        "page_id": page_id
    }


def _extract_block_text(block):
    """Extract plain text from a Notion block."""
    b_type = block["type"]
    if b_type in block and "rich_text" in block.get(b_type, {}):
        rich_text = block[b_type]["rich_text"]
        if rich_text:
            return "".join(rt.get("text", {}).get("content", "") for rt in rich_text)
    return ""


# === SAVE TO NOTION ==========================================================

async def save_prompt_to_notion(title, content, category="", pack=""):
    """Save a new prompt to Notion DB and update local cache."""
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    page_title = title + " [" + slug + "]"

    body = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": page_title}}]
            }
        },
        "children": []
    }

    if category:
        body["children"].append({
            "object": "block", "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Category: " + category}}]}
        })
    if pack:
        body["children"].append({
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Pack: " + pack}}]}
        })

    body["children"].append({"object": "block", "type": "divider", "divider": {}})

    for chunk in _chunk_text(content, 2000):
        body["children"].append({
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}
        })

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.notion.com/v1/pages",
                headers=NOTION_HEADERS, json=body
            )
            if resp.status_code in (200, 201):
                page_data = resp.json()
                page_id = page_data["id"]
                log.info("Saved prompt to Notion: %s [%s]", title, slug)
                notion_prompts_cache.append({
                    "title": title, "content": content, "category": category,
                    "slug": slug, "pack": pack, "source": "notion", "page_id": page_id
                })
                return True, slug
            else:
                log.error("Notion save failed: %s", resp.text)
                return False, resp.text[:200]
    except Exception as e:
        log.error("Error saving to Notion: %s", e)
        return False, str(e)


def _chunk_text(text, max_len=2000):
    chunks = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line
    if current:
        chunks.append(current)
    return chunks if chunks else [text]


# === SEARCH ==================================================================

def search_notion_prompts(query):
    """Fuzzy search across Notion prompt cache.
    Searches: title, slug, category, and first 300 chars of content.
    Also normalizes spaces/dashes for fuzzy matching.
    """
    query_lower = query.lower().strip()
    query_norm = query_lower.replace(" ", "").replace("-", "")

    # Also split into individual words for multi-word matching
    query_words = [w for w in query_lower.split() if len(w) > 1]

    results = []
    for p in notion_prompts_cache:
        title_lower = p["title"].lower()
        title_norm = title_lower.replace(" ", "").replace("-", "")
        slug_lower = p["slug"].lower()
        slug_norm = slug_lower.replace(" ", "").replace("-", "")
        category_lower = p.get("category", "").lower()
        category_norm = category_lower.replace(" ", "").replace("-", "")
        content_preview = p["content"].lower()[:500]

        # Direct match
        if (query_lower in title_lower or
            query_lower in slug_lower or
            query_lower in category_lower or
            query_norm in title_norm or
            query_norm in slug_norm or
            query_norm in category_norm or
            query_lower in content_preview):
            results.append(p)
            continue

        # Multi-word: all words must match somewhere
        if query_words and len(query_words) > 1:
            all_text = title_lower + " " + slug_lower + " " + category_lower + " " + content_preview
            if all(w in all_text for w in query_words):
                results.append(p)

    return results


def get_notion_prompt_by_slug(slug):
    """Find a prompt in cache by exact slug match."""
    for p in notion_prompts_cache:
        if p["slug"] == slug:
            return p
    return None


# === AUTO-SAVE PROMPT DETECTION ==============================================

PROMPT_INDICATORS = [
    "kamu adalah", "you are", "act as", "bertindak sebagai",
    "buatkan", "generate", "create", "write", "buat",
    "langkah", "step", "instruksi", "instruction",
    "template", "prompt", "format output", "output format",
    "sebagai", "sebagai seorang", "as a", "role:",
    "task:", "tugas:", "objective:", "tujuan:",
]

PROMPT_CATEGORIES = [
    "Landing Page", "Copywriting", "Video AI", "Social Media",
    "Email Marketing", "SEO", "Coding", "Research", "Business",
    "Marketing", "Content Creation", "General"
]


def is_likely_prompt(text):
    """Detect if text is a prompt vs casual chat."""
    if len(text) < 100:
        return False
    
    text_lower = text.lower()
    
    # Check for prompt indicators
    indicator_count = sum(1 for ind in PROMPT_INDICATORS if ind in text_lower)
    
    # Has multiple lines (structured content)
    line_count = len(text.split('\n'))
    
    # Decision: at least 1 indicator OR long structured text
    return indicator_count >= 1 or (len(text) > 300 and line_count > 3)


def check_duplicate(text, threshold=0.7):
    """Check if similar prompt exists in cache using simple similarity."""
    from difflib import SequenceMatcher
    
    text_lower = text.lower()[:500]
    
    for p in notion_prompts_cache:
        existing = p["content"].lower()[:500]
        similarity = SequenceMatcher(None, text_lower, existing).ratio()
        
        if similarity > threshold:
            return True, p["title"]
    
    return False, None


def categorize_prompt_simple(text):
    """Simple keyword-based categorization."""
    text_lower = text.lower()
    
    category_keywords = {
        "Landing Page": ["landing page", "hero section", "cta", "above the fold", "conversion"],
        "Copywriting": ["copywriting", "headline", "hook", "persuasif", "sales copy", "copy"],
        "Video AI": ["video", "script video", "youtube", "tiktok", "reels", "shorts"],
        "Social Media": ["instagram", "facebook", "twitter", "linkedin", "social media", "posting"],
        "Email Marketing": ["email", "newsletter", "subject line", "autoresponder"],
        "SEO": ["seo", "keyword", "meta description", "backlink", "serp"],
        "Coding": ["code", "programming", "python", "javascript", "api", "function", "debug"],
        "Research": ["research", "analisis", "riset", "study", "data"],
        "Business": ["business", "bisnis", "strategi", "plan", "model"],
        "Marketing": ["marketing", "funnel", "ads", "iklan", "campaign"],
        "Content Creation": ["content", "artikel", "blog", "konten", "write"],
    }
    
    for category, keywords in category_keywords.items():
        if any(kw in text_lower for kw in keywords):
            return category
    
    return "General"


def extract_title_from_prompt(text):
    """Extract a reasonable title from prompt text."""
    # Get first line, clean it
    first_line = text.split('\n')[0].strip()
    
    # Remove common prefixes
    prefixes = ["kamu adalah", "you are", "act as", "bertindak sebagai", "buatkan", "buat"]
    for prefix in prefixes:
        if first_line.lower().startswith(prefix):
            first_line = first_line[len(prefix):].strip()
            break
    
    # Limit length
    if len(first_line) > 60:
        first_line = first_line[:57] + "..."
    
    return first_line if first_line else "Prompt " + str(int(time.time()))[-6:]


def detect_multi_prompts(text):
    """Detect and split numbered prompt blocks from text.
    Returns list of (title, content) tuples or None if not multi-prompt.
    """
    # Split by numbered patterns: "1. xxx", "2) xxx", etc.
    blocks = re.split(r'\n(?=\d+[\.\)]\s)', text.strip())
    
    if len(blocks) < 2:
        return None
    
    prompts = []
    for block in blocks:
        block = block.strip()
        if len(block) < 50:
            continue
        # Extract title from first line
        first_line = block.split('\n')[0].strip()[:80]
        prompts.append((first_line, block))
    
    return prompts if len(prompts) >= 2 else None


def generate_pack_name(filename_or_text):
    """Generate a clean pack name from filename or text."""
    name = filename_or_text
    # Remove file extensions
    for ext in [".csv", ".txt", ".md"]:
        name = name.replace(ext, "")
    # Clean up
    name = name.replace("_", " ").replace("-", " ").strip()
    # Limit length
    if len(name) > 60:
        name = name[:57] + "..."
    return name


# === COMMAND PATTERNS ========================================================

COMMAND_PATTERNS = [
    (re.compile(r"^/mode\s+(fast|smart)\s*$", re.I), "mode_switch"),
    (re.compile(r"^/mode\s*$", re.I), "mode_show"),
    (re.compile(r"^(?:prompt|buka|lihat|tampilkan|open|show)\s+(.+)$", re.I), "prompt_search"),
    (re.compile(r"^pakai:\s*(.+)$", re.I), "pakai_prompt"),
    (re.compile(r"^list\s*$", re.I), "list_all"),
    (re.compile(r"^list\s+(.+)$", re.I), "list_category"),
    (re.compile(r"^cari:\s*(.+)$", re.I), "cari_prompt"),
    (re.compile(r"^(?:s|simpan|save):\s*(.+)$", re.I | re.S), "save_prompt"),
    (re.compile(r"^/reload\s*$", re.I), "reload_notion"),
]

# Natural language patterns that map to commands
# These catch informal Indonesian/English requests
NATURAL_LIST_PATTERNS = [
    r"prompt\s*(apa|apa\s*aja|apa\s*saja|apa\s*yang\s*ada|yang\s*ada|gw|gue|saya|ku|punya|ada|list|daftar)",
    r"(apa|ada)\s*(aja|saja)?\s*prompt",
    r"daftar\s*prompt",
    r"semua\s*prompt",
    r"(punya|ada)\s*prompt\s*(apa|berapa)",
    r"(gw|gue|gua|saya|aku|w)\s*punya\s*prompt\s*(apa|apa\s*aja|apa\s*saja|berapa)?",
    r"(list|daftar)\s*(semua\s*)?(prompt)?",
    r"(kasih|tampil|tunjuk)\s*(lihat|in|kan)?\s*(semua|daftar|list)?\s*prompt",
    r"(what|my)\s*prompt",
    r"prompt\s*(saya|gw|gue|gua|w|aku|ku)\s*(apa|apa\s*aja)?",
]
_natural_list_re = re.compile(
    r"^(?:" + "|".join(NATURAL_LIST_PATTERNS) + r")\s*[\?\.\!]*$", re.I
)

NATURAL_SEARCH_PATTERNS = [
    r"(?:cari|cariin|carinya|tolong\s*cari)\s+(?:prompt\s+)?(.+)",
    r"(?:ada|punya)\s+(?:prompt\s+)?(?:tentang|soal|untuk|about)\s+(.+)",
]
_natural_search_re = [
    re.compile(r"^" + p + r"\s*[\?\.\!]*$", re.I) for p in NATURAL_SEARCH_PATTERNS
]


# Words that indicate a QUESTION (should go to AI, not command)
QUESTION_INDICATORS = [
    "apa", "kenapa", "mengapa", "gimana", "bagaimana", "kapan",
    "dimana", "siapa", "berapa", "apakah", "bisakah", "boleh",
    "tolong", "bantu", "jelaskan", "ceritakan", "kasih tau",
    "what", "why", "how", "when", "where", "who", "which",
    "can you", "could you", "please", "tell me",
    "barusan", "tadi", "sebelumnya", "yang tadi", "udah", "sudah",
]

def is_question_or_conversation(text):
    """Check if text is a conversational question, not a command."""
    text_lower = text.lower().strip()
    
    # Ends with question mark
    if text_lower.endswith("?"):
        return True
    
    # Contains question words (beyond just "apa" at start)
    words = text_lower.split()
    if len(words) > 2:  # More than 2 words = likely conversational
        for indicator in QUESTION_INDICATORS:
            if indicator in text_lower:
                return True
    
    return False


def match_command(text):
    text = text.strip()
    
    # FIRST: Skip command matching if this looks like a conversational question
    if is_question_or_conversation(text):
        return None, None

    # Check natural language patterns (before formal commands)
    # This catches "gw punya prompt apa aja", "prompt apa aja", etc.
    if _natural_list_re.match(text):
        return "list_all", None

    # Natural search: "cariin prompt video", "ada prompt tentang X"
    for pat in _natural_search_re:
        m = pat.match(text)
        if m:
            return "prompt_search", m

    # Then check formal command patterns
    for pattern, cmd_type in COMMAND_PATTERNS:
        m = pattern.match(text)
        if m:
            return cmd_type, m

    return None, None


# === SHELL / OPENCLAW HELPERS ================================================

def run_shell(cmd, timeout=30):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
            env=dict(os.environ, PATH=FIXED_PATH))
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr.strip():
            return output if output else "Error: " + result.stderr.strip()[:500]
        return output or "(tidak ada output)"
    except subprocess.TimeoutExpired:
        return "Timeout (>30 detik)"
    except FileNotFoundError as e:
        return "Script tidak ditemukan: " + str(e.filename)
    except Exception as e:
        return "Error: " + str(e)


def forward_to_openclaw(user_message, user_id):
    """Forward chat to OpenClaw Gateway with conversation history."""
    url = OPENCLAW_HOST + "/v1/chat/completions"
    headers = {
        "Authorization": "Bearer " + OPENCLAW_TOKEN,
        "Content-Type": "application/json",
        "x-openclaw-agent-id": "main"
    }
    
    # Build messages with conversation history
    system_msg = {
        "role": "system",
        "content": (
            "Kamu adalah AI assistant di Telegram bot bernama 'Chat Random Akbar'. "
            "Bot ini punya database prompt di Notion yang bisa dicari dan disimpan otomatis.\n\n"
            "KEMAMPUAN BOT:\n"
            "- Simpan prompt otomatis ke Notion (jika user kirim prompt)\n"
            "- OCR gambar (jika user kirim foto)\n"
            "- Cari prompt: ketik 'buka [keyword]'\n"
            "- List semua: ketik 'list'\n\n"
            "INSTRUKSI:\n"
            "- Jawab dalam bahasa yang sama dengan user (Indonesia/English)\n"
            "- Jawab ringkas dan to the point\n"
            "- Jika ada konteks dari percakapan sebelumnya, gunakan konteks itu\n"
            "- Kamu BISA melihat dan mengingat percakapan sebelumnya"
        )
    }
    
    history = get_history(user_id)
    messages = [system_msg] + history + [{"role": "user", "content": user_message}]
    
    payload = {
        "model": "openclaw",
        "messages": messages,
        "user": "telegram-" + str(user_id),
        "stream": False
    }
    try:
        log.info("Forwarding to OpenClaw Gateway (history: %d msgs)", len(history))
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        log.info("OpenClaw response status: %d", resp.status_code)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            return content if content else "(OpenClaw jawaban kosong)"
        return "(OpenClaw tidak mengembalikan jawaban)"
    except requests.exceptions.ConnectionError:
        log.error("OpenClaw gateway unreachable")
        return "OpenClaw gateway tidak bisa dihubungi. Coba lagi nanti."
    except requests.exceptions.Timeout:
        return "AI timeout (>120 detik). Coba lagi."
    except requests.exceptions.HTTPError as e:
        log.error("OpenClaw HTTP %d: %s", e.response.status_code, e.response.text[:300])
        return "OpenClaw error " + str(e.response.status_code)
    except Exception as e:
        log.error("Forward error: %s", str(e))
        return "Error: " + str(e)


# === MAIN MESSAGE HANDLER ====================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    user_id = str(update.effective_user.id)
    log.info("[%s] %s", user_id, text[:80])

    cmd_type, match = match_command(text)

    if not cmd_type:
        # Not a command -> forward to OpenClaw
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        if re.findall(url_pattern, text):
            response = (
                "Maaf, saya belum bisa membaca konten dari link eksternal.\n\n"
                "Mohon copy-paste isi teks dari link tersebut agar saya bisa membacanya."
            )
        else:
            # Check if this is a prompt that should be auto-saved
            save_context = ""
            
            # First: check for multi-prompt (numbered list)
            multi = detect_multi_prompts(text)
            if multi:
                log.info("Detected MULTI-PROMPT (%d prompts)", len(multi))
                pack_name = "Pack " + str(int(time.time()))[-6:]
                # Try to get pack name from first line or category
                category = categorize_prompt_simple(text)
                pack_name = category + " Pack"
                
                saved_count = 0
                skipped_count = 0
                for title, content in multi:
                    is_dup, _ = check_duplicate(content)
                    if is_dup:
                        skipped_count += 1
                        continue
                    success, result = await save_prompt_to_notion(title, content, category=category, pack=pack_name)
                    if success:
                        saved_count += 1
                    
                save_context = "[SISTEM: " + str(saved_count) + " prompt disimpan sebagai pack '" + pack_name + "'. " + str(skipped_count) + " duplikat dilewati.]"
                await update.message.reply_text(
                    "\u2705 " + str(saved_count) + " prompt disimpan sebagai pack!\n" +
                    "\u2500" * 25 + "\n" +
                    "\U0001f4c1 Pack: " + pack_name + "\n" +
                    "\U0001f4c1 Kategori: " + category + "\n" +
                    "\u23ed Dilewati: " + str(skipped_count) + " duplikat"
                )
                # Reload cache
                await load_notion_prompts()
                
            elif is_likely_prompt(text):
                log.info("Detected as PROMPT, checking duplicate...")
                is_dup, existing_title = check_duplicate(text)
                
                if is_dup:
                    log.info("Duplicate found: %s", existing_title)
                    save_context = "[SISTEM: Prompt serupa sudah ada di Notion: " + existing_title + ". Tidak disimpan lagi.]"
                    await update.message.reply_text(
                        "\u26a0\ufe0f Prompt serupa sudah ada di Notion:\n" +
                        "\U0001f4c4 " + existing_title + "\n\n" +
                        "Tidak disimpan lagi untuk menghindari duplikat."
                    )
                else:
                    # Categorize and save
                    category = categorize_prompt_simple(text)
                    title = extract_title_from_prompt(text)
                    
                    log.info("Auto-saving prompt: %s | Category: %s", title, category)
                    success, result = await save_prompt_to_notion(title, text, category=category)
                    
                    if success:
                        save_context = "[SISTEM: Prompt disimpan ke Notion. Judul: " + title + " | Kategori: " + category + " | Slug: " + result + "]"
                        await update.message.reply_text(
                            "\u2705 Prompt disimpan otomatis ke Notion!\n" +
                            "\u2500" * 25 + "\n" +
                            "\U0001f4c4 Judul: " + title + "\n" +
                            "\U0001f4c1 Kategori: " + category + "\n" +
                            "\U0001f3f7\ufe0f Slug: " + result
                        )
                    else:
                        log.error("Auto-save failed: %s", result)
            
            # Add user message to history
            add_to_history(user_id, "user", text)
            
            # Inject save context if prompt was saved
            if save_context:
                add_to_history(user_id, "assistant", save_context)
            
            # Forward to OpenClaw for response
            log.info("FORWARD to OpenClaw")
            response = forward_to_openclaw(text, user_id)
        if not response:
            response = "(tidak ada jawaban)"
        
        # Track AI response in history
        add_to_history(user_id, "assistant", response[:500])
        
        await _send_long_message(update, response)
        return

    log.info("COMMAND: %s", cmd_type)

    # === prompt [topik] — langsung tampilkan semua isi prompt ===
    if cmd_type == "prompt_search":
        # Get topic from match groups — try group(1) first, fallback to full match
        try:
            topic = match.group(1).strip()
        except (AttributeError, IndexError):
            topic = text.strip()
        results = search_notion_prompts(topic)

        if not results:
            await update.message.reply_text(
                "\u274c Tidak ada prompt untuk: " + topic + "\n\n"
                "Coba kata kunci lain, atau:\n"
                "\u2022 list \u2014 lihat semua kategori\n"
                "\u2022 simpan: Judul\\nIsi \u2014 simpan prompt baru"
            )
            return

        # Build 1 combined message with header + all content
        sep = "\u2500" * 40
        header = (
            "\U0001f50d Prompt: " + topic + "\n"
            "\U0001f4e6 " + str(len(results)) + " prompt ditemukan di Notion\n"
            + sep + "\n\n"
        )

        full_msg = header
        for i, p in enumerate(results[:10], 1):
            title = p["title"]
            cat = p.get("category", "")
            content = p["content"]

            full_msg += "\U0001f4c4 " + title
            if cat:
                full_msg += " (" + cat + ")"
            full_msg += "\n" + sep + "\n\n" + content + "\n\n"

        await _send_long_message(update, full_msg.strip())
        return

    # === pakai: [slug] ===
    if cmd_type == "pakai_prompt":
        slug = match.group(1).strip()
        notion_prompt = get_notion_prompt_by_slug(slug)
        if notion_prompt:
            sep = "\u2500" * 30
            response = (
                "\U0001f4c4 " + notion_prompt["title"] + "\n" +
                sep + "\n\n" + notion_prompt["content"]
            )
        else:
            response = "\u274c Prompt tidak ditemukan: " + slug
        await _send_long_message(update, response)
        return

    # === simpan: / save: / s: ===
    if cmd_type == "save_prompt":
        raw = match.group(1).strip()
        response = await _handle_save(raw)
        await _send_long_message(update, response)
        return

    # === /reload ===
    if cmd_type == "reload_notion":
        await update.message.reply_text("\U0001f504 Reloading Notion prompts...")
        await load_notion_prompts()
        await update.message.reply_text(
            "\u2705 Loaded " + str(len(notion_prompts_cache)) + " prompts dari Notion."
        )
        return

    # === /mode ===
    if cmd_type == "mode_switch":
        response = run_shell([SWITCH_MODE_SCRIPT, match.group(1).lower()], timeout=60)
        await update.message.reply_text(response)
        return
    if cmd_type == "mode_show":
        response = run_shell([SWITCH_MODE_SCRIPT, "show"])
        await update.message.reply_text(response)
        return

    # === list ===
    if cmd_type == "list_all":
        if not notion_prompts_cache:
            await update.message.reply_text("\u274c Belum ada prompt di Notion")
            return

        # Group prompts by category
        cats = {}
        for p in notion_prompts_cache:
            cat = p.get("category") or "Lainnya"
            if cat not in cats:
                cats[cat] = []
            cats[cat].append(p)

        sep = "\u2500" * 30
        lines = [
            "\U0001f4da Daftar Semua Prompt Kamu",
            sep, ""
        ]
        num = 0
        for cat in sorted(cats.keys()):
            prompts_in_cat = cats[cat]
            lines.append("\U0001f4c1 " + cat + " (" + str(len(prompts_in_cat)) + ")")
            for p in prompts_in_cat:
                num += 1
                lines.append("  " + str(num) + ". " + p["title"][:60])
            lines.append("")

        lines.append(sep)
        lines.append("Total: " + str(len(notion_prompts_cache)) + " prompt\n")
        lines.append("\U0001f4a1 Cara buka prompt:")
        lines.append("  \u2022 buka [kata kunci]")
        lines.append("  \u2022 prompt [kata kunci]")
        lines.append("  \u2022 Contoh: buka video script")
        await _send_long_message(update, "\n".join(lines))
        return

    # === list [kategori] ===
    if cmd_type == "list_category":
        cat = match.group(1).strip()
        cat_lower = cat.lower()
        notion_in_cat = [p for p in notion_prompts_cache if cat_lower in p.get("category", "").lower()]
        if notion_in_cat:
            sep = "\u2500" * 25
            lines = [
                "\U0001f4c1 Kategori: " + cat,
                "\U0001f4e6 " + str(len(notion_in_cat)) + " prompt",
                sep, ""
            ]
            for i, p in enumerate(notion_in_cat[:20], 1):
                lines.append(str(i) + ". " + p["title"][:60])
            lines.append("")
            lines.append(sep)
            lines.append("\U0001f4a1 Ketik: prompt [kata kunci] untuk lihat isi lengkap")
            await update.message.reply_text("\n".join(lines))
        else:
            await update.message.reply_text("\u274c Tidak ada prompt di kategori: " + cat)
        return

    # === cari: [topik] — sama seperti prompt search ===
    if cmd_type == "cari_prompt":
        try:
            topic = match.group(1).strip()
        except (AttributeError, IndexError):
            topic = text.strip()
        results = search_notion_prompts(topic)
        if not results:
            await update.message.reply_text("\u274c Tidak ada prompt untuk: " + topic)
            return

        sep = "\u2500" * 40
        full_msg = (
            "\U0001f50d Cari: " + topic + "\n"
            "\U0001f4e6 " + str(len(results)) + " prompt ditemukan\n"
            + sep + "\n\n"
        )
        for i, p in enumerate(results[:10], 1):
            full_msg += "\U0001f4c4 " + p["title"]
            if p.get("category"):
                full_msg += " (" + p["category"] + ")"
            full_msg += "\n" + sep + "\n\n" + p["content"] + "\n\n"
        await _send_long_message(update, full_msg.strip())
        return

    await update.message.reply_text("(command tidak dikenali)")


async def _handle_save(raw_text):
    """Handle save prompt: simpan: Judul | Kategori\\nIsi prompt..."""
    lines = raw_text.strip().split("\n", 1)
    first_line = lines[0].strip()
    content = lines[1].strip() if len(lines) > 1 else ""

    if not content:
        return (
            "\u26a0\ufe0f Format simpan:\n\n"
            "simpan: Judul Prompt\n"
            "Isi prompt di sini...\n\n"
            "Atau dengan kategori:\n"
            "simpan: Judul | Kategori\n"
            "Isi prompt..."
        )

    category = ""
    if "|" in first_line:
        parts = first_line.split("|", 1)
        title = parts[0].strip()
        category = parts[1].strip()
    else:
        title = first_line

    success, result = await save_prompt_to_notion(title, content, category=category)

    if success:
        sep = "\u2500" * 25
        return (
            "\u2705 Prompt disimpan ke Notion!\n" +
            sep + "\n"
            "\U0001f4c4 Judul: " + title + "\n"
            "\U0001f3f7\ufe0f Slug: " + result + "\n"
            "\U0001f4c1 Kategori: " + (category or "(tidak ada)") + "\n" +
            sep + "\n"
            "Panggil dengan: prompt " + title.split()[0].lower()
        )
    else:
        return "\u274c Gagal menyimpan: " + str(result)


async def _send_long_message(update, text):
    """Send a message, splitting at paragraph breaks near 4096 char limit."""
    if not text:
        return
    MAX = 4090
    while len(text) > MAX:
        # Try to split at a double newline near the limit
        split_at = text.rfind("\n\n", 0, MAX)
        if split_at < MAX // 2:
            # No good break point — split at single newline
            split_at = text.rfind("\n", 0, MAX)
        if split_at < MAX // 2:
            split_at = MAX
        await update.message.reply_text(text[:split_at])
        text = text[split_at:].lstrip("\n")
    if text.strip():
        await update.message.reply_text(text)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages - OCR and forward to OpenClaw."""
    if not update.message.photo:
        return
    
    photo = update.message.photo[-1]  # Highest resolution
    caption = update.message.caption or ""
    user_id = str(update.effective_user.id)
    
    await update.message.reply_text("\U0001f441 Membaca gambar dengan OCR...")
    
    # Download photo to temp file
    temp_path = "/tmp/telegram_photo_" + user_id + "_" + str(int(time.time())) + ".jpg"
    
    try:
        file = await photo.get_file()
        await file.download_to_drive(temp_path)
        log.info("Photo downloaded to %s", temp_path)
        
        # Run Tesseract OCR
        result = subprocess.run(
            ["tesseract", temp_path, "stdout", "-l", "eng+ind"],
            capture_output=True, text=True, timeout=30
        )
        ocr_text = result.stdout.strip()
        log.info("OCR result: %d chars", len(ocr_text))
        
    except subprocess.TimeoutExpired:
        await update.message.reply_text("\u23f1 OCR timeout. Gambar terlalu besar.")
        return
    except Exception as e:
        log.error("OCR error: %s", e)
        await update.message.reply_text("\u274c Error OCR: " + str(e))
        return
    finally:
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    if not ocr_text or len(ocr_text) < 5:
        await update.message.reply_text(
            "\u274c Tidak dapat membaca teks dari gambar.\n\n"
            "Tips: Pastikan gambar jelas dan ada teks yang bisa dibaca."
        )
        return
    
    # Check if OCR'd text is a prompt - auto-save if yes
    if is_likely_prompt(ocr_text):
        log.info("OCR detected as PROMPT, checking duplicate...")
        is_dup, existing_title = check_duplicate(ocr_text)
        
        if is_dup:
            log.info("Duplicate found: %s", existing_title)
            await update.message.reply_text(
                "\u26a0\ufe0f Prompt serupa sudah ada di Notion:\n" +
                "\U0001f4c4 " + existing_title + "\n\n" +
                "Tidak disimpan lagi untuk menghindari duplikat."
            )
        else:
            # Categorize and save
            category = categorize_prompt_simple(ocr_text)
            title = extract_title_from_prompt(ocr_text)
            
            log.info("Auto-saving OCR prompt: %s | Category: %s", title, category)
            success, result = await save_prompt_to_notion(title, ocr_text, category=category)
            
            if success:
                await update.message.reply_text(
                    "\u2705 Prompt dari gambar disimpan ke Notion!\n" +
                    "\u2500" * 25 + "\n" +
                    "\U0001f4c4 Judul: " + title + "\n" +
                    "\U0001f4c1 Kategori: " + category + "\n" +
                    "\U0001f3f7\ufe0f Slug: " + result
                )
            else:
                log.error("Auto-save OCR failed: %s", result)
    
    # Build combined message for OpenClaw
    combined = "Ini hasil OCR dari gambar yang dikirim user:\n\n" + ocr_text
    if caption:
        combined = combined + "\n\nCaption dari user: " + caption
    combined = combined + "\n\nTolong bantu analisis atau jawab berdasarkan konten ini."
    
    # Forward to OpenClaw
    response = forward_to_openclaw(combined, user_id)
    
    # Send response
    await _send_long_message(update, response)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file uploads (CSV, TXT) with caption 'simpan prompt'."""
    import csv, io

    doc = update.message.document
    caption = (update.message.caption or "").strip().lower()

    if not doc:
        return

    # Only process if caption mentions 'simpan' or 'save'
    if not any(kw in caption for kw in ["simpan", "save", "import"]):
        await update.message.reply_text(
            "\U0001f4ce File diterima: " + doc.file_name + "\n\n"
            "Untuk menyimpan isi file sebagai prompt, kirim file dengan caption:\n"
            "  simpan prompt"
        )
        return

    fname = doc.file_name or ""
    if not fname.lower().endswith((".csv", ".txt")):
        await update.message.reply_text(
            "\u26a0\ufe0f Format file tidak didukung: " + fname + "\n"
            "Kirim file .csv atau .txt"
        )
        return

    await update.message.reply_text("\u23f3 Memproses file " + fname + "...")

    try:
        tg_file = await doc.get_file()
        file_bytes = await tg_file.download_as_bytearray()
        file_text = file_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        log.error("File download error: %s", e)
        await update.message.reply_text("\u274c Gagal download file: " + str(e))
        return

    saved = 0
    failed = 0
    skipped = 0
    saved_titles = []

    if fname.lower().endswith(".csv"):
        reader = csv.reader(io.StringIO(file_text))
        header = None
        content_col = -1
        author_col = -1

        # First pass: collect all rows
        all_rows = []
        for row in reader:
            if header is None:
                header = [h.strip().lower() for h in row]
                for idx, h in enumerate(header):
                    if h == "content":
                        content_col = idx
                    elif h == "author":
                        author_col = idx
                if content_col < 0:
                    content_col = min(4, len(header) - 1) if len(header) > 4 else 1
                log.info("CSV header: %s, content_col=%d, author_col=%d", header, content_col, author_col)
                continue
            if row and len(row) > content_col:
                all_rows.append(row)

        # Detect main author (most frequent with long content)
        author_counts = {}
        for row in all_rows:
            content = row[content_col].strip()
            author = row[author_col].strip() if author_col >= 0 and len(row) > author_col else ""
            if len(content) > 100 and author:
                author_counts[author] = author_counts.get(author, 0) + 1
        
        main_author = max(author_counts, key=author_counts.get) if author_counts else ""
        log.info("Main author detected: %s (%d prompts)", main_author, author_counts.get(main_author, 0))

        # Generate pack name from filename
        pack_name = generate_pack_name(fname)
        log.info("Pack name: %s", pack_name)

        # Second pass: save only prompts from main author with >100 chars
        for row in all_rows:
            content = row[content_col].strip()
            author = row[author_col].strip() if author_col >= 0 and len(row) > author_col else ""

            # Filter: only main author, content > 100 chars
            if author != main_author or len(content) < 100:
                skipped += 1
                continue

            # Check duplicate
            is_dup, existing_title = check_duplicate(content)
            if is_dup:
                skipped += 1
                log.info("Duplicate skipped: %s", existing_title)
                continue

            # Extract title and categorize
            first_line = content.split("\n")[0].strip()
            title = first_line[:80] if first_line else "Prompt dari " + author
            category = categorize_prompt_simple(content)

            success, result = await save_prompt_to_notion(title, content, category=category, pack=pack_name)
            if success:
                saved += 1
                saved_titles.append(title[:50])
                log.info("Saved prompt: %s | Pack: %s", title[:40], pack_name)
            else:
                failed += 1
                log.error("Save failed for '%s': %s", title[:30], result)
    else:
        # TXT — check for multi-prompt
        multi = detect_multi_prompts(file_text)
        if multi:
            pack_name = generate_pack_name(fname)
            for title, content in multi:
                is_dup, _ = check_duplicate(content)
                if is_dup:
                    skipped += 1
                    continue
                category = categorize_prompt_simple(content)
                success, result = await save_prompt_to_notion(title, content, category=category, pack=pack_name)
                if success:
                    saved += 1
                    saved_titles.append(title[:50])
                else:
                    failed += 1
        else:
            # Single prompt
            lines = file_text.strip().split("\n", 1)
            title = lines[0].strip()[:80]
            content = file_text.strip()
            success, result = await save_prompt_to_notion(title, content, category="Imported from File")
            if success:
                saved = 1
                saved_titles.append(title[:50])
            else:
                failed = 1

    # Reload cache after saving
    await load_notion_prompts()

    sep = "\u2500" * 25
    pack_info = ""
    if 'pack_name' in dir() and pack_name:
        pack_info = "\U0001f4c1 Pack: " + pack_name + "\n"
    
    report = (
        "\u2705 Import selesai!\n" + sep + "\n" +
        pack_info +
        "\U0001f4be Disimpan: " + str(saved) + " prompt\n"
        "\u274c Gagal: " + str(failed) + "\n"
        "\u23ed Dilewati (duplikat/pendek): " + str(skipped) + "\n" + sep + "\n"
    )
    if saved_titles:
        report += "\nPrompt yang disimpan:\n"
        for i, t in enumerate(saved_titles, 1):
            report += str(i) + ". " + t + "\n"
        report += "\n" + sep + "\n"
    report += "Total prompt di Notion: " + str(len(notion_prompts_cache)) + "\n\n"
    report += (
        "\U0001f4a1 Cara buka prompt:\n"
        "  \u2022 buka video \u2014 tampilkan semua prompt video\n"
        "  \u2022 prompt hook \u2014 cari prompt \"hook\"\n"
        "  \u2022 buka [kata kunci] \u2014 cari & tampilkan\n"
        "  \u2022 list \u2014 lihat semua kategori"
    )
    await _send_long_message(update, report)


# === BOT COMMANDS =============================================================

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt_count = len(notion_prompts_cache)
    sep = "\u2500" * 25
    await update.message.reply_text(
        "\U0001f916 Chat Random Akbar Bot\n" +
        sep + "\n"
        "\U0001f4da " + str(prompt_count) + " prompt dari Notion\n\n"
        "\U0001f50d Buka & Cari Prompt:\n"
        "  prompt [kata kunci]\n"
        "  buka [kata kunci]\n"
        "  lihat [kata kunci]\n"
        "  list \u2014 semua kategori\n\n"
        "\U0001f4be Simpan Prompt:\n"
        "  simpan: Judul\n"
        "  Isi prompt...\n\n"
        "  Atau kirim file CSV/TXT\n"
        "  dengan caption: simpan prompt\n\n"
        "\u2699\ufe0f Lainnya:\n"
        "  /reload \u2014 refresh data Notion\n\n"
        "\U0001f4ac Chat biasa = AI (DeepSeek V3)"
    )


# === STARTUP ==================================================================

async def post_init(application: Application):
    await load_notion_prompts()
    log.info("Bot ready. %d Notion prompts loaded.", len(notion_prompts_cache))


def main():
    log.info("Telegram Proxy Bot Starting...")
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("start", cmd_help))
    app.add_handler(CommandHandler("mode", handle_message))
    app.add_handler(CommandHandler("reload", handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    log.info("Polling started")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
