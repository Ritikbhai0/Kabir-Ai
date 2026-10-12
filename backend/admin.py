"""Owner-only administration; credentials never reach public pages."""
from collections import defaultdict, deque
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('DATA_DIR', str(ROOT / 'data')))
router = APIRouter(prefix='/api/admin')
lock = threading.RLock()
sessions = {}
attempts = defaultdict(deque)
job = {'state': 'idle'}
MAX_BYTES = 30 * 1024 * 1024


def configured_password():
    password = os.environ.get('ADMIN_PASSWORD', '')
    if len(password) < 16:
        raise HTTPException(503, 'Admin बंद है। Hosting settings में कम से कम 16 अक्षरों का ADMIN_PASSWORD सेट करें।')
    return password


def session(request, write=False):
    configured_password()
    with lock:
        key = request.cookies.get('admin_session', '')
        item = sessions.get(key)
        if not item or item['expires'] < time.time():
            sessions.pop(key, None)
            raise HTTPException(401, 'पहले admin login करें।')
        if write and not secrets.compare_digest(request.headers.get('x-csrf-token', ''), item['csrf']):
            raise HTTPException(403, 'सुरक्षा जाँच असफल। दोबारा login करें।')
        return item


class Login(BaseModel):
    password: str = Field(min_length=1, max_length=512)


@router.post('/login')
def login(body: Login, request: Request, response: Response):
    expected = configured_password()
    ip = request.client.host if request.client else 'local'
    now = time.time()
    with lock:
        for key in list(attempts):
            if not attempts[key] or attempts[key][-1] < now - 600:
                del attempts[key]
        queue = attempts[ip]
        while queue and queue[0] < now - 600:
            queue.popleft()
        if len(queue) >= 8:
            raise HTTPException(429, 'बहुत प्रयास हुए। 10 मिनट बाद प्रयास करें।')
        queue.append(now)
        if not hmac.compare_digest(hashlib.sha256(body.password.encode()).digest(), hashlib.sha256(expected.encode()).digest()):
            raise HTTPException(401, 'पासवर्ड सही नहीं है।')
        for key in list(sessions):
            if sessions[key]['expires'] < now:
                del sessions[key]
        if len(sessions) >= 20:
            sessions.pop(next(iter(sessions)))
        key, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        sessions[key] = {'csrf': csrf, 'expires': now + 3600}
    response.set_cookie('admin_session', key, httponly=True, secure=os.environ.get('COOKIE_SECURE', '1') != '0', samesite='strict', max_age=3600, path='/api/admin')
    response.headers['Cache-Control'] = 'no-store'
    return {'csrf': csrf}


@router.get('/session')
def current_session(request: Request):
    return {'csrf': session(request)['csrf']}


@router.post('/logout')
def logout(request: Request, response: Response):
    session(request, write=True)
    with lock:
        sessions.pop(request.cookies.get('admin_session', ''), None)
    response.delete_cookie('admin_session', path='/api/admin')
    return {'ok': True}


@router.get('/job')
def progress(request: Request):
    session(request)
    with lock:
        return dict(job)


def process_book(path, title):
    global job
    try:
        result = subprocess.run([sys.executable, str(ROOT / 'backend/ingest.py'), str(path), '--title', title, '--workers', str(max(1, min(2, int(os.environ.get('INGEST_WORKERS', '2')))))], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=7200)
        if result.returncode:
            raise RuntimeError('ingestion failed')
        from backend.storage import backup
        try:
            durable = backup()
            state = {'state': 'complete', 'message': 'पुस्तक जुड़ गई है। सभी users अब इसमें खोज सकते हैं।', 'durable': durable}
            if not durable:
                state['message'] += ' बाहरी backup सेट नहीं है; hosting reset पर डेटा मिट सकता है।'
        except Exception:
            state = {'state': 'backup_failed', 'message': 'पुस्तक स्थानीय रूप से जुड़ी है, लेकिन cloud backup असफल हुआ। Backup फिर चलाएँ।'}
        with lock:
            job = state
    except Exception:
        with lock:
            job = {'state': 'failed', 'message': 'PDF तैयार नहीं हो सकी। फ़ाइल/OCR और server configuration जाँचें।'}
    finally:
        path.unlink(missing_ok=True)


@router.post('/upload', status_code=202)
async def upload(request: Request):
    global job
    session(request, write=True)
    if request.headers.get('content-type', '').split(';')[0] != 'application/pdf':
        raise HTTPException(415, 'केवल PDF स्वीकार है।')
    title = unquote(request.headers.get('x-book-title', '')).strip()
    if not 1 <= len(title) <= 120 or any(ord(c) < 32 for c in title):
        raise HTTPException(400, 'पुस्तक का नाम 1–120 अक्षरों में लिखें।')
    with lock:
        if job['state'] in {'uploading', 'processing', 'backing_up'}:
            raise HTTPException(409, 'एक पुस्तक पर काम चल रहा है। उसके बाद upload करें।')
        job = {'state': 'uploading'}
    path = None
    try:
        DATA.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=DATA, suffix='.pdf', delete=False) as output:
            path = Path(output.name)
            size = 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(413, 'PDF अधिकतम 30 MB हो सकती है।')
                output.write(chunk)
        with path.open('rb') as source:
            if source.read(5) != b'%PDF-':
                raise HTTPException(400, 'मान्य PDF फ़ाइल चुनें।')
        try:
            with pymupdf.open(path) as pdf:
                if pdf.is_encrypted or not 1 <= len(pdf) <= 600:
                    raise HTTPException(400, 'PDF बिना password की और 1–600 पृष्ठ की होनी चाहिए।')
                if any(page.rect.width > 2000 or page.rect.height > 2000 for page in pdf):
                    raise HTTPException(400, 'PDF के पृष्ठ बहुत बड़े हैं। सामान्य आकार की PDF चुनें।')
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(400, 'यह PDF पढ़ी नहीं जा सकती।')
        with lock:
            job = {'state': 'processing', 'title': title, 'message': 'पुस्तक पढ़ी जा रही है। बड़ी किताब में कई मिनट लग सकते हैं।'}
        threading.Thread(target=process_book, args=(path, title), daemon=True).start()
        path = None
        return dict(job)
    finally:
        if path:
            path.unlink(missing_ok=True)
        with lock:
            if job['state'] == 'uploading':
                job = {'state': 'idle'}


@router.post('/backup')
def retry_backup(request: Request):
    global job
    session(request, write=True)
    with lock:
        if job['state'] in {'uploading', 'processing', 'backing_up'}:
            raise HTTPException(409, 'पहले वर्तमान काम पूरा होने दें।')
        job = {'state': 'backing_up'}
    def run():
        global job
        from backend.storage import backup
        try:
            ok = backup()
            result = {'state': 'complete' if ok else 'backup_failed', 'message': 'Cloud backup पूरा हुआ।' if ok else 'HF_TOKEN और HF_DATASET_REPO सेट करें।'}
        except Exception:
            result = {'state': 'backup_failed', 'message': 'Cloud backup असफल। Token permission और dataset जाँचें।'}
        with lock:
            job = result
    threading.Thread(target=run, daemon=True).start()
    return {'state': 'backing_up'}
