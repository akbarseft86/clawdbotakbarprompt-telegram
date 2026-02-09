#!/usr/bin/env bash
set -e

RAW_MSG="$1"
msg_lower=$(echo "$RAW_MSG" | tr "A-Z" "a-z")

# prompt [topik]
if [[ "$msg_lower" == prompt\ * ]]; then
  TOPIC="${RAW_MSG#prompt }"
  TOPIC=$(echo "$TOPIC" | sed "s/^ *//;s/ *$//")
  [ -z "$TOPIC" ] && TOPIC="landing page"
  python3 "$HOME/.openclaw/scripts/prompt_db_v2.py" search-packs "$TOPIC"
  exit 0
fi

# lihat paket: [slug]
if [[ "$msg_lower" == lihat\ paket:* ]]; then
  SLUG="${RAW_MSG#*:}"
  SLUG=$(echo "$SLUG" | sed "s/^ *//;s/ *$//")
  python3 "$HOME/.openclaw/scripts/prompt_db_v2.py" list-pack "$SLUG"
  exit 0
fi

# pakai: [slug]
if [[ "$msg_lower" == pakai:* ]]; then
  SLUG="${RAW_MSG#*:}"
  SLUG=$(echo "$SLUG" | sed "s/^ *//;s/ *$//")
  python3 "$HOME/.openclaw/scripts/prompt_db_v2.py" get "$SLUG"
  exit 0
fi

echo "(no match)"
