"""Optional private Hugging Face dataset backup for ephemeral free hosting."""
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('DATA_DIR', str(ROOT / 'data')))

def backup():
    repo, token = os.environ.get('HF_DATASET_REPO'), os.environ.get('HF_TOKEN')
    if not repo or not token:
        return False
    from huggingface_hub import HfApi
    api = HfApi(token=token)
    info = api.repo_info(repo_id=repo, repo_type='dataset')
    if not info.private:
        raise ValueError('Backup dataset must be private')
    api.upload_folder(repo_id=repo, repo_type='dataset', folder_path=str(DATA), allow_patterns=['catalog.json', 'books/*.pdf'], commit_message='Update PDF library and index')
    return True

def restore():
    repo, token = os.environ.get('HF_DATASET_REPO'), os.environ.get('HF_TOKEN')
    if not repo or not token:
        return
    from huggingface_hub import snapshot_download, HfApi
    info = HfApi(token=token).repo_info(repo_id=repo, repo_type='dataset')
    if not info.private:
        raise ValueError('Backup dataset must be private')
    snapshot = Path(snapshot_download(repo_id=repo, repo_type='dataset', revision=info.sha, token=token, allow_patterns=['catalog.json', 'books/*.pdf']))
    # Download all files before replacing catalog; never expose a half-restored book.
    DATA.mkdir(parents=True, exist_ok=True)
    if (snapshot / 'books').exists():
        shutil.copytree(snapshot / 'books', DATA / 'books', dirs_exist_ok=True)
    if (snapshot / 'catalog.json').exists():
        temp = DATA / 'restore.tmp'
        shutil.copyfile(snapshot / 'catalog.json', temp)
        temp.replace(DATA / 'catalog.json')

if __name__ == '__main__':
    restore()
