#!/usr/bin/env bash
# Scrape 蝦皮 posts from all target boards (200 index pages each).
# Run from the repo root: bash ptt/script/scrape_all_boards.sh

set -euo pipefail

KEYWORD="蝦皮"
PAGES=200
WORKERS=8

BOARDS=(
  Gossiping
  C_Chat
  Stock
  HatePolitics
  Lifeismoney
  KoreaStar
  Steam
  PlayStation
  NSwitch
  miHoYo
  Valorant
  Hearthstone
  PokemonGO
  mobile-game
  C_BOO
  Marginalman
  WomenTalk
  Boy-Girl
  marriage
  BabyMother
  cookclub
  BeautySalon
  FITNESS
  MuscleBeach
  Salary
  e-shopping
  PC_Shopping
  MobileComm
  creditcard
  Brand
  hypermall
  watch
  MakeUp
  shoes
  iOS
  Android
  MAC
  HardwareSale
  Headphone
  DSLR
  Audiophile
)

total=${#BOARDS[@]}
done=0
failed=()

for board in "${BOARDS[@]}"; do
  done=$((done + 1))
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "[$done/$total]  board: $board"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  if uv run python ptt/index_scraper.py "$KEYWORD" "$board" "$PAGES" "$WORKERS"; then
    echo "  ✓ $board done"
  else
    echo "  ✗ $board FAILED (exit $?)"
    failed+=("$board")
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "All boards processed: $total total"

if [ ${#failed[@]} -gt 0 ]; then
  echo "Failed boards (${#failed[@]}):"
  for b in "${failed[@]}"; do
    echo "  - $b"
  done
  exit 1
else
  echo "All succeeded."
fi
