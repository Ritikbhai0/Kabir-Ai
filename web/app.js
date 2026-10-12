'use strict';
const $ = id => document.getElementById(id);
const messages = $('messages');
let busy = false;
let voices = [];
const hasSpeech = 'speechSynthesis' in window;
function populateVoices() {
  if (!hasSpeech) return;
  voices = speechSynthesis.getVoices().filter(v => v.lang.toLowerCase().startsWith('hi'));
  $('voice').replaceChildren(new Option('फ़ोन / browser की default आवाज़', ''));
  voices.forEach((v, i) => $('voice').add(new Option(v.name, String(i))));
}
function speak(text) {
  if (!hasSpeech) { $('voice-status').textContent = 'इस browser में उत्तर सुनना उपलब्ध नहीं है।'; return; }
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text.replace(/^Sat Sahib/, 'सत साहिब'));
  utterance.lang = 'hi-IN';
  if ($('voice').value !== '') utterance.voice = voices[Number($('voice').value)];
  utterance.rate = Number($('speed').value);
  utterance.pitch = Number($('pitch').value);
  utterance.onerror = () => { $('voice-status').textContent = 'आवाज़ नहीं चल सकी। उत्तर पढ़ सकते हैं।'; };
  speechSynthesis.speak(utterance);
}
if (hasSpeech) { populateVoices(); speechSynthesis.addEventListener('voiceschanged', populateVoices); }
$('welcome').onclick = () => speak('Sat Sahib। अपना प्रश्न लिखें या बोलें।');
$('stop-speech').onclick = () => { if (hasSpeech) speechSynthesis.cancel(); };
for (const name of ['speed', 'pitch']) $(name).oninput = () => $(name + '-value').textContent = $(name).value + '×';
function element(tag, className, text) { const node = document.createElement(tag); node.className = className; node.textContent = text; return node; }
async function ask(question) {
  if (busy || question.trim().length < 2) return;
  busy = true; $('send').disabled = true;
  const initial = messages.querySelector('.initial'); if (initial) initial.remove();
  messages.append(element('div', 'question-bubble', question));
  const pending = element('p', 'pending', 'पुस्तक में संबंधित अंश खोज रहे हैं…'); messages.append(pending);
  messages.scrollTop = messages.scrollHeight;
  try {
    const response = await fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question }), signal: AbortSignal.timeout(30000) });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'प्रश्न भेजा नहीं जा सका। फिर प्रयास करें।');
    const answer = element('article', 'answer', '');
    answer.append(element('div', 'answer-heading', 'SAT SAHIB · पुस्तक आधारित खोज'));
    answer.append(element('p', 'answer-text', data.answer));
    for (const source of data.sources) {
      const link = element('a', 'source', `▤ ${source.book} · PDF पृष्ठ ${source.pdf_page} ↗`);
      link.href = source.url; link.target = '_blank'; link.rel = 'noopener'; answer.append(link);
    }
    if (data.sources.length) answer.append(element('p', 'answer-note', 'संबंधित अंश है, सत्यापित पूर्ण उत्तर नहीं। OCR पाठ को मूल PDF से जाँचें। पृष्ठ संख्या PDF की है।'));
    const listen = element('button', 'text-button', '◉ उत्तर सुनें'); listen.onclick = () => speak(data.answer); answer.append(listen);
    messages.append(answer);
    if ($('auto-speak').checked) speak(data.answer);
    $('question').value = '';
  } catch (error) {
    messages.append(element('p', 'error', error.name === 'TimeoutError' ? 'खोज में अधिक समय लगा। फिर प्रयास करें।' : error.message));
  } finally { pending.remove(); busy = false; $('send').disabled = false; messages.scrollTop = messages.scrollHeight; }
}
$('ask-form').onsubmit = event => { event.preventDefault(); ask($('question').value.trim()); };
$('question').onkeydown = event => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); $('ask-form').requestSubmit(); } };
document.querySelectorAll('[data-question]').forEach(button => button.onclick = () => { $('question').value = button.dataset.question; ask(button.dataset.question); });
const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let listening = false;
if (Recognition) {
  const recognition = new Recognition(); recognition.lang = 'hi-IN'; recognition.interimResults = false;
  $('mic').onclick = () => {
    if (listening) { recognition.stop(); return; }
    if (hasSpeech) speechSynthesis.cancel();
    try { recognition.start(); } catch { $('voice-status').textContent = 'माइक्रोफ़ोन चालू नहीं हो सका।'; }
  };
  recognition.onstart = () => { listening = true; $('mic').setAttribute('aria-pressed', 'true'); $('voice-status').textContent = 'सुन रहे हैं… बोलकर अपना प्रश्न पूछें'; };
  recognition.onresult = event => { $('question').value = event.results[0][0].transcript.slice(0, 500); $('voice-status').textContent = 'प्रश्न जाँचें, फिर ↑ दबाएँ।'; };
  recognition.onerror = () => { $('voice-status').textContent = 'आवाज़ नहीं पहचानी गई। अनुमति जाँचें या प्रश्न लिखें।'; };
  recognition.onend = () => { listening = false; $('mic').setAttribute('aria-pressed', 'false'); };
} else { $('mic').disabled = true; $('voice-status').textContent = 'इस browser में voice input नहीं है। प्रश्न लिखें।'; }
async function status() {
  try {
    const response = await fetch('/api/status'); if (!response.ok) throw new Error();
    const data = await response.json();
    $('library-status').textContent = data.ready ? data.books.map(b => `${b.title} · ${b.pages} PDF पृष्ठ`).join(' | ') : 'पुस्तक तैयार हो रही है। कृपया थोड़ी देर बाद प्रयास करें।';
  } catch { $('library-status').textContent = 'सेवा उपलब्ध नहीं है। थोड़ी देर बाद प्रयास करें।'; }
}
status();
