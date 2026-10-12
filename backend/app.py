"""Free, local, extractive PDF question answering. No external AI or search."""
from collections import defaultdict, deque
import json
import os
from pathlib import Path
import re
import threading
import time
import unicodedata

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('DATA_DIR', str(ROOT / 'data')))
CATALOG = DATA / 'catalog.json'
FALLBACK = 'Sat Sahib, उपलब्ध अधिकृत सामग्री में मुझे इस प्रश्न का स्पष्ट उत्तर नहीं मिला.'
STOP = set('क्या क्यों कैसे कौन कहाँ कहां कब किस किसके किसने किसका कितने कितना की के का है हैं में से को और या एक यह वह भी ही पर तो लिए बारे बताओ बताएं बताइए बतायें मुझे हमें आप जी महाराज कृपया अनुसार होता होती होते करें कर रहा रही था थे the is what who how'.split())

def words(text):
    text = unicodedata.normalize('NFC', text).lower()
    return [w for w in re.findall(r'[\u0900-\u097fa-z0-9]+', text) if len(w) > 1 and w not in STOP and not w.isdigit()]

class Library:
    def __init__(self):
        self.lock = threading.RLock()
        self.stamp = None
        self.books = []
        self.chunks = []
        self.matrix = None

    def refresh(self):
        stamp = CATALOG.stat().st_mtime_ns if CATALOG.exists() else None
        if stamp == self.stamp:
            return
        raw = json.loads(CATALOG.read_text(encoding='utf-8'))
        chunks = []
        for book in raw['books']:
            for page in book['pages']:
                # Short, overlapping passages preserve exact OCR text and page provenance.
                lines = page['text'].splitlines()
                for start in range(0, len(lines), 7):
                    text = '\n'.join(lines[start:start + 11]).strip()
                    if len(words(text)) >= 12:
                        chunks.append({'text': text, 'book': book['title'], 'book_id': book['id'], 'pdf_page': page['pdf_page'], 'ocr': page['method'] == 'ocr'})
        if not chunks:
            raise ValueError('Catalog has no searchable text')
        vectorizer = TfidfVectorizer(analyzer=words, sublinear_tf=True)
        matrix = vectorizer.fit_transform(c['text'] for c in chunks)
        self.books, self.chunks = raw['books'], chunks
        self.vectorizer, self.matrix, self.stamp = vectorizer, matrix, stamp

    def search(self, question):
        with self.lock:
            self.refresh()
            if self.matrix is None:
                raise HTTPException(503, 'पुस्तक की तैयारी चल रही है। थोड़ी देर बाद पूछें।')
            terms = set(words(question))
            if not terms:
                return []
            # Unknown meaningful terms cause abstention instead of unrelated answers.
            if any(w not in self.vectorizer.vocabulary_ for w in terms):
                return []
            scores = (self.matrix @ self.vectorizer.transform([question]).T).toarray().ravel()
            matches = []
            for index in scores.argsort()[::-1][:20]:
                chunk = self.chunks[int(index)]
                coverage = len(terms & set(words(chunk['text']))) / len(terms)
                if scores[index] < .16 or coverage < 1:
                    continue
                if any(m['book_id'] == chunk['book_id'] and m['pdf_page'] == chunk['pdf_page'] for m in matches):
                    continue
                matches.append(chunk.copy())
                if len(matches) == 2:
                    break
            return matches

library = Library()
app = FastAPI(title='Sat Sahib · PDF Assistant', docs_url=None, redoc_url=None, openapi_url=None)
visitors = defaultdict(deque)
rate_lock = threading.Lock()

@app.middleware('http')
async def protections(request: Request, call_next):
    response = await call_next(request)
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    if request.url.path.startswith('/api/admin'):
        response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'microphone=(self)'
    return response

class Question(BaseModel):
    question: str = Field(min_length=2, max_length=500)

@app.get('/api/status')
def status():
    with library.lock:
        library.refresh()
        return {'ready': library.matrix is not None, 'mode': 'extractive', 'books': [{'title': b['title'], 'pages': len(b['pages'])} for b in library.books]}

@app.post('/api/ask')
def ask(body: Question, request: Request):
    now = time.monotonic()
    ip = request.client.host if request.client else 'local'
    with rate_lock:
        for key in list(visitors):
            if not visitors[key] or now - visitors[key][-1] > 60:
                del visitors[key]
        queue = visitors[ip]
        while queue and now - queue[0] > 60:
            queue.popleft()
        if len(queue) >= 20:
            raise HTTPException(429, 'कृपया एक मिनट बाद फिर प्रयास करें।')
        queue.append(now)
    matches = library.search(body.question)
    if not matches:
        return {'answer': FALLBACK, 'sources': [], 'mode': 'not_found'}
    return {'answer': 'Sat Sahib। पुस्तक में आपके प्रश्न से संबंधित यह अंश मिला है:\n\n' + matches[0]['text'], 'sources': [{**c, 'url': f"/api/books/{c['book_id']}.pdf#page={c['pdf_page']}"} for c in matches], 'mode': 'extractive'}

@app.get('/api/books/{book_id}.pdf')
def pdf(book_id: str):
    with library.lock:
        library.refresh()
        if not re.fullmatch('[a-f0-9]{20}', book_id) or book_id not in {b['id'] for b in library.books}:
            raise HTTPException(404)
    return FileResponse(DATA / 'books' / f'{book_id}.pdf', media_type='application/pdf')

from backend.admin import router as admin_router
app.include_router(admin_router)

app.mount('/', StaticFiles(directory=ROOT / 'web', html=True), name='web')
