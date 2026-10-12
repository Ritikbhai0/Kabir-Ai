'use strict';
const $ = id => document.getElementById(id);
let csrf = '';
let timer;
async function api(path, options = {}) {
  const response = await fetch('/api/admin/' + path, { ...options, headers: { 'x-csrf-token': csrf, ...options.headers } });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401) show(false);
    throw new Error(typeof data.detail === 'string' ? data.detail : 'अनुरोध असफल हुआ।');
  }
  return data;
}
function show(loggedIn) { $('login-form').hidden = loggedIn; $('admin-panel').hidden = !loggedIn; if (!loggedIn) { csrf = ''; clearTimeout(timer); } }
function message(text) { $('admin-status').textContent = text; }
async function poll() {
  clearTimeout(timer);
  try {
    const job = await api('job');
    const active = ['uploading', 'processing', 'backing_up'].includes(job.state);
    $('upload-button').disabled = active;
    $('backup').disabled = active;
    message(job.message || (active ? 'काम चल रहा है…' : 'पुस्तक जोड़ने के लिए तैयार।'));
    if (active) timer = setTimeout(poll, 3000);
  } catch (error) { message(error.message); }
}
$('login-form').onsubmit = async event => {
  event.preventDefault();
  try {
    const result = await api('login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password: $('password').value }) });
    csrf = result.csrf; $('password').value = ''; show(true); poll();
  } catch (error) { message(error.message); }
};
$('upload-form').onsubmit = async event => {
  event.preventDefault();
  const file = $('pdf-file').files[0];
  if (!file || file.size > 30 * 1024 * 1024) { message('30 MB तक की PDF चुनें।'); return; }
  $('upload-button').disabled = true;
  message('PDF भेजी जा रही है…');
  try {
    await api('upload', { method: 'POST', headers: { 'Content-Type': 'application/pdf', 'x-book-title': encodeURIComponent($('book-title').value.trim()) }, body: file });
    $('upload-form').reset(); poll();
  } catch (error) { message(error.message); $('upload-button').disabled = false; }
};
$('logout').onclick = async () => { try { await api('logout', { method: 'POST' }); show(false); message('Logout हो गया।'); } catch (error) { message(error.message); } };
$('backup').onclick = async () => { try { await api('backup', { method: 'POST' }); poll(); } catch (error) { message(error.message); } };
(async () => { try { const result = await api('session'); csrf = result.csrf; show(true); poll(); } catch { show(false); } })();
