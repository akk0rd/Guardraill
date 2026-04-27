#!/usr/bin/env bash
# Download spaCy model wheels and their PyPI dependencies for offline Docker builds.
#
# Run this ONCE on a machine that has internet access, then copy the resulting
# spacy_models/ directory alongside the Dockerfile to the air-gapped machine.
#
# Usage:
#   bash scripts/download_models.sh
#
# ──────────────────────────────────────────────────────────────────────────────
# IMPORTANT: spaCy models are NOT on PyPI.
# "pip download uk-core-news-sm" hits a stub confusion-protection package and
# fails with a metadata error.  The real wheels are hosted on GitHub Releases
# and must be fetched with curl.
#
# The model wheels depend on pymorphy3, pymorphy3-dicts-uk, and pymorphy3-dicts-ru
# which ARE on PyPI and are fetched with pip download below.
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

DEST="spacy_models"
mkdir -p "$DEST"

# ── 1. spaCy model wheels (GitHub Releases, NOT PyPI) ────────────────────────

declare -A MODELS=(
  ["uk_core_news_sm-3.7.0-py3-none-any.whl"]="https://github.com/explosion/spacy-models/releases/download/uk_core_news_sm-3.7.0/uk_core_news_sm-3.7.0-py3-none-any.whl"
  ["en_core_web_sm-3.7.1-py3-none-any.whl"]="https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl"
  ["ru_core_news_sm-3.7.0-py3-none-any.whl"]="https://github.com/explosion/spacy-models/releases/download/ru_core_news_sm-3.7.0/ru_core_news_sm-3.7.0-py3-none-any.whl"
)

echo "── Downloading spaCy model wheels from GitHub Releases ──"
for filename in "${!MODELS[@]}"; do
  url="${MODELS[$filename]}"
  dest_file="$DEST/$filename"
  if [[ -f "$dest_file" ]]; then
    echo "✓ already exists: $dest_file"
  else
    echo "↓ $filename"
    curl -fSL --retry 3 -o "$dest_file" "$url"
    echo "✓ saved"
  fi
done

# ── 2. Model dependencies from PyPI ──────────────────────────────────────────
# uk_core_news_sm → pymorphy3 + pymorphy3-dicts-uk
# ru_core_news_sm → pymorphy3 + pymorphy3-dicts-ru
# These are normal PyPI packages and can use pip download.

echo ""
echo "── Downloading model dependencies from PyPI ──"
pip download \
  "pymorphy3>=1.0.0" \
  "pymorphy3-dicts-uk" \
  "pymorphy3-dicts-ru" \
  --no-deps \
  -d "$DEST"

echo ""
echo "Done. Files in $DEST/:"
ls -lh "$DEST/"
echo ""
echo "Next step — build the offline image:"
echo "  docker build -f Dockerfile.offline -t guardraill:offline ."
