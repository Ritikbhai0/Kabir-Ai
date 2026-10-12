"""Owner-only PDF ingestion. Never exposed as a public upload endpoint."""
import argparse
import fcntl
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('DATA_DIR', str(ROOT / 'data')))

def read_page(args):
    filename, number, language = args
    with pymupdf.open(filename) as doc:
        page = doc[number]
        text = page.get_text()
        devanagari = sum('\u0900' <= c <= '\u097f' for c in text)
        method = 'text'
        if devanagari < max(30, len(text) * .25):
            with tempfile.TemporaryDirectory() as tmp:
                image = Path(tmp) / 'page.png'
                page.get_pixmap(dpi=180).save(image)
                result = subprocess.run(['tesseract', str(image), 'stdout', '--tessdata-dir', str(DATA / 'tessdata'), '-l', language, '--psm', '3'], capture_output=True, text=True, check=True, env={**os.environ, 'OMP_THREAD_LIMIT': '1'}, timeout=180)
                text, method = result.stdout, 'ocr'
    return {'pdf_page': number + 1, 'text': text.strip(), 'method': method}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf', type=Path)
    parser.add_argument('--title', required=True)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    DATA.mkdir(exist_ok=True)
    book_id = hashlib.sha256(args.pdf.read_bytes()).hexdigest()[:20]
    books = DATA / 'books'
    books.mkdir(exist_ok=True)
    target = books / (book_id + '.pdf')
    if not target.exists():
        shutil.copyfile(args.pdf, target)
    cache = DATA / 'ocr' / book_id
    cache.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(target) as doc:
        total = len(doc)
    pending = [i for i in range(total) if not (cache / f'{i+1}.json').exists()]
    with ProcessPoolExecutor(max_workers=max(1, min(8, args.workers))) as pool:
        for page in pool.map(read_page, [(str(target), i, 'hin') for i in pending]):
            (cache / f"{page['pdf_page']}.json").write_text(json.dumps(page, ensure_ascii=False), encoding='utf-8')
            print(f"Read page {page['pdf_page']}/{total}", flush=True)
    pages = [json.loads((cache / f'{i+1}.json').read_text()) for i in range(total)]
    if not any(len(p['text'].strip()) >= 40 for p in pages):
        raise ValueError('PDF has no usable text')
    index = DATA / 'catalog.json'
    catalog = json.loads(index.read_text()) if index.exists() else {'books': []}
    catalog['books'] = [b for b in catalog['books'] if b['id'] != book_id]
    catalog['books'].append({'id': book_id, 'title': args.title, 'pages': pages})
    temporary = index.with_suffix('.tmp')
    temporary.write_text(json.dumps(catalog, ensure_ascii=False), encoding='utf-8')
    temporary.replace(index)
    print(f'Indexed {total} pages. The server will reload the catalog automatically.')

if __name__ == '__main__':
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / 'ingestion.lock').open('w') as guard:
        fcntl.flock(guard, fcntl.LOCK_EX)
        main()
