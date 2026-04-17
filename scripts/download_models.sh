#!/usr/bin/env bash
# Download spaCy model wheels for offline Docker builds.
#
# Run this ONCE on a machine that has internet access, then commit (or copy)
# the resulting spacy_models/ directory alongside the Dockerfile.
#
# Usage:
#   bash scripts/download_models.sh
#
# spaCy models are NOT on PyPI — they are .whl files hosted on GitHub Releases.
# "pip download uk-core-news-sm" hits a stub safety package and fails.
# Use these direct URLs instead.

set -euo pipefail

DEST="spacy_models"
mkdir -p "$DEST"

declare -A MODELS=(
  ["uk_core_news_sm-3.7.0-py3-none-any.whl"]="https://github.com/explosion/spacy-models/releases/download/uk_core_news_sm-3.7.0/uk_core_news_sm-3.7.0-py3-none-any.whl"
  ["en_core_web_sm-3.7.1-py3-none-any.whl"]="https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl"
  ["ru_core_news_sm-3.7.0-py3-none-any.whl"]="https://github.com/explosion/spacy-models/releases/download/ru_core_news_sm-3.7.0/ru_core_news_sm-3.7.0-py3-none-any.whl"
)

for filename in "${!MODELS[@]}"; do
  url="${MODELS[$filename]}"
  dest_file="$DEST/$filename"
  if [[ -f "$dest_file" ]]; then
    echo "✓ already exists: $dest_file"
  else
    echo "↓ downloading $filename ..."
    curl -fSL --retry 3 -o "$dest_file" "$url"
    echo "✓ saved to $dest_file"
  fi
done

echo ""
echo "Done. Files in $DEST/:"
ls -lh "$DEST/"
echo ""
echo "Next step — build the offline image:"
echo "  docker build -f Dockerfile.offline -t guardraill:offline ."
