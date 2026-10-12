import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from backend import storage

class StorageTests(unittest.TestCase):
    def test_missing_credentials_never_claims_backup(self):
        with patch.dict(os.environ,{'HF_TOKEN':'','HF_DATASET_REPO':''}):
            self.assertFalse(storage.backup())

    def test_public_dataset_is_rejected(self):
        with patch.dict(os.environ,{'HF_TOKEN':'unit-test-token','HF_DATASET_REPO':'test/library'}),patch('huggingface_hub.HfApi') as api:
            api.return_value.repo_info.return_value=SimpleNamespace(private=False)
            with self.assertRaises(ValueError): storage.backup()
            api.return_value.upload_folder.assert_not_called()

    def test_restore_and_backup_only_library_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'snapshot'; dest=Path(tmp)/'data'
            (source/'books').mkdir(parents=True)
            (source/'books'/'book.pdf').write_bytes(b'%PDF-test')
            (source/'catalog.json').write_text(json.dumps({'books':[]}))
            with patch.dict(os.environ,{'HF_TOKEN':'unit-test-token','HF_DATASET_REPO':'test/library'}),patch.object(storage,'DATA',dest),patch('huggingface_hub.HfApi') as api,patch('huggingface_hub.snapshot_download',return_value=str(source)) as download:
                api.return_value.repo_info.return_value=SimpleNamespace(private=True,sha='pinned-revision')
                storage.restore()
                self.assertEqual((dest/'books/book.pdf').read_bytes(),b'%PDF-test')
                self.assertEqual(json.loads((dest/'catalog.json').read_text()),{'books':[]})
                self.assertEqual(download.call_args.kwargs['revision'],'pinned-revision')
                self.assertTrue(storage.backup())
                self.assertEqual(api.return_value.upload_folder.call_args.kwargs['allow_patterns'],['catalog.json','books/*.pdf'])
