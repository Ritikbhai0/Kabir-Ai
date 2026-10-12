#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
command -v tesseract >/dev/null || { echo 'Install the OS tesseract-ocr package, then rerun setup.' >&2; exit 1; }
mkdir -p data/tessdata
if [ ! -s data/tessdata/hin.traineddata ]; then
  curl -fL https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/hin.traineddata -o data/tessdata/hin.traineddata.tmp
  mv data/tessdata/hin.traineddata.tmp data/tessdata/hin.traineddata
fi
if [ -f data/gyan_ganga_hindi.pdf ]; then
  .venv/bin/python backend/ingest.py data/gyan_ganga_hindi.pdf --title 'ज्ञान गंगा' --workers 4
fi
