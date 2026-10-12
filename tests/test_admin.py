import os
import time
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import app
from backend import admin

class AdminTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'ADMIN_PASSWORD': 'test-only-password-12345', 'COOKIE_SECURE': '1'})
        self.env.start()
        with admin.lock:
            admin.sessions.clear(); admin.attempts.clear(); admin.job = {'state': 'idle'}
        self.client = TestClient(app, base_url='https://testserver')

    def tearDown(self):
        self.env.stop()

    def login(self):
        response = self.client.post('/api/admin/login', json={'password': 'test-only-password-12345'})
        self.assertEqual(response.status_code, 200)
        cookie = response.headers['set-cookie'].lower()
        for flag in ['httponly', 'secure', 'samesite=strict']:
            self.assertIn(flag, cookie)
        return response.json()['csrf']

    def test_public_cannot_upload_or_check_jobs(self):
        response = self.client.post('/api/admin/upload', content=b'%PDF', headers={'content-type':'application/pdf','x-book-title':'test'})
        self.assertEqual(response.status_code,401)
        self.assertEqual(self.client.get('/api/admin/job').status_code,401)

    def test_disabled_without_configured_secret(self):
        with patch.dict(os.environ, {'ADMIN_PASSWORD':''}):
            self.assertEqual(self.client.post('/api/admin/login',json={'password':'anything'}).status_code,503)

    def test_bad_password_rate_limit(self):
        for _ in range(8):
            self.assertEqual(self.client.post('/api/admin/login',json={'password':'wrong'}).status_code,401)
        self.assertEqual(self.client.post('/api/admin/login',json={'password':'wrong'}).status_code,429)

    def test_csrf_and_pdf_validation(self):
        csrf=self.login()
        self.assertEqual(self.client.post('/api/admin/upload',content=b'%PDF').status_code,403)
        headers={'x-csrf-token':csrf,'content-type':'application/pdf','x-book-title':'test'}
        self.assertEqual(self.client.post('/api/admin/upload',content=b'not a pdf',headers=headers).status_code,400)
        self.assertEqual(self.client.post('/api/admin/upload',content=b'%PDF broken',headers=headers).status_code,400)
        with patch.object(admin,'MAX_BYTES',10):
            self.assertEqual(self.client.post('/api/admin/upload',content=b'%PDF'+b'x'*20,headers=headers).status_code,413)
        self.assertEqual(admin.job['state'],'idle')

    def test_logout_invalidates_session(self):
        csrf=self.login()
        self.assertEqual(self.client.get('/api/admin/session').json()['csrf'],csrf)
        self.assertEqual(self.client.post('/api/admin/logout',headers={'x-csrf-token':csrf}).status_code,200)
        self.assertEqual(self.client.get('/api/admin/session').status_code,401)

    def test_expired_session_denied(self):
        self.login()
        for item in admin.sessions.values(): item['expires']=0
        self.assertEqual(self.client.get('/api/admin/session').status_code,401)

    def test_authenticated_real_book_ingestion(self):
        from urllib.parse import quote
        csrf=self.login()
        pdf=(admin.DATA/'gyan_ganga_hindi.pdf').read_bytes()
        with patch.dict(os.environ,{'HF_TOKEN':'','HF_DATASET_REPO':''}):
            response=self.client.post('/api/admin/upload',content=pdf,headers={'x-csrf-token':csrf,'content-type':'application/pdf','x-book-title':quote('ज्ञान गंगा')})
            self.assertEqual(response.status_code,202)
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                state=self.client.get('/api/admin/job').json()
                if state['state'] not in ['uploading','processing']: break
                time.sleep(.1)
            self.assertEqual(state['state'],'complete',state)
            self.assertFalse(state['durable'])
        self.assertTrue(self.client.get('/api/status').json()['ready'])
