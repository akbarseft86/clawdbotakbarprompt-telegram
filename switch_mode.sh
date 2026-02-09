#!/usr/bin/env bash
set -e

MODE_FILE="$HOME/.openclaw/mode.txt"

if [ "$#" -lt 1 ]; then
  echo "Usage: switch_mode.sh [fast|smart|show]"
  exit 1
fi

CMD="$1"
case "$CMD" in
  fast)
    NEW_MODEL="sumopod/gpt-4.1-nano"
    NEW_LABEL="fast (Sumopod – gpt-4.1-nano)"
    ;;
  smart)
    NEW_MODEL="deepseek/deepseek-chat"
    NEW_LABEL="smart (DeepSeek – deepseek-chat)"
    ;;
  show)
    if [ -f "$MODE_FILE" ]; then
      echo "Mode sekarang: $(cat "$MODE_FILE")"
    else
      echo "Mode sekarang: fast (default)"
    fi
    exit 0
    ;;
  *)
    echo "Usage: switch_mode.sh [fast|smart|show]"
    exit 1
    ;;
esac

# Simpan mode ke file
echo "$NEW_LABEL" > "$MODE_FILE"

# Switch model via OpenClaw
source "$HOME/.nvm/nvm.sh"
openclaw models set "$NEW_MODEL" 2>/dev/null

# Restart gateway
openclaw gateway restart 2>/dev/null

echo "✅ Mode diganti ke: $NEW_LABEL"
