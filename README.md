---
title: Sat Sahib
emoji: 📚
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# Sat Sahib — PDF आधारित हिंदी web app

मोबाइल और कंप्यूटर के browser में चलने वाला मुफ्त प्रारंभिक संस्करण। कोई paid AI API, API key या internet search नहीं।

**वर्तमान क्षमता:** यह स्थानीय TF-IDF खोज से पुस्तक के संबंधित अंश निकालता है (extractive retrieval)। यह generative AI या पूर्ण semantic RAG नहीं है। अपने शब्दों में उत्तर नहीं गढ़ता। प्रश्न के शब्द न मिलने पर निर्धारित fallback देता है। संबंधित अंश मिलना इस बात की गारंटी नहीं कि उसमें प्रश्न का पूरा उत्तर है। UI यह सीमा स्पष्ट करता है। अगला चरण: समीक्षा किए हुए OCR पाठ और प्रश्नोत्तर परीक्षणों के बाद स्थानीय मॉडल, यदि मशीन सक्षम हो।

## इस cloud workspace में चलाएँ

Setup के लिए `bash scripts/setup.sh` और फिर `bash scripts/start.sh` चलाएँ। इससे isolated Python environment इस्तेमाल होगा। इस workspace में पहली किताब पहले से index की गई है।

## अपने कंप्यूटर पर चलाएँ

Python 3.11+ चाहिए। Terminal में repository के folder से:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

अपने कंप्यूटर के browser में loopback host, port 8000 खोलें। Server में `data/catalog.json` न होने पर पुस्तक तैयार होने की सूचना आएगी।

## पहली या नई PDF जोड़ें

मालिक `/admin.html` पर सुरक्षित login करके PDF upload कर सकता है। सामान्य users upload नहीं कर सकते। Admin के लिए `ADMIN_PASSWORD` secret (कम से कम 16 अक्षर) आवश्यक है। Local HTTP परीक्षण के लिए केवल अपनी मशीन पर `COOKIE_SECURE=0` सेट करें; hosting पर secure cookies चालू रखें। Terminal ingestion भी उपलब्ध है। Ubuntu/Debian पर Tesseract package (`tesseract-ocr`) install होना चाहिए। Hindi model आधिकारिक Tesseract repository से लें:

```bash
mkdir -p data/tessdata
curl -fL https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/hin.traineddata -o data/tessdata/hin.traineddata
python backend/ingest.py /path/to/book.pdf --title 'पुस्तक का नाम' --workers 4
```

एक समय में एक ingestion चलाएँ। सफल completion पर index atomically बदलेगा और server अगले request पर नई किताब खोज सकेगा। Website rebuild/restart जरूरी नहीं। दोबारा उसी PDF को index करने पर OCR cache इस्तेमाल होता है। अधूरे ingestion का आंशिक catalog प्रकाशित नहीं होता। PDFs, OCR, model और catalog सभी `data/` में हैं और Git में नहीं जाते; इनका अलग backup रखें। दूसरी मशीन पर original PDF फिर से upload/index करें या `data/` सुरक्षित restore करें।

वर्तमान ज्ञान गंगा: 336 PDF पृष्ठ। पुराने fonts के कारण Hindi OCR किया गया है। OCR में मात्राओं, नामों और अंकों की गलतियाँ बची हैं; इसे पूरी तरह proofread नहीं किया गया है। स्रोत PDF से पुष्टि करें। UI में हमेशा **PDF पृष्ठ संख्या** है, छपी पुस्तक संख्या नहीं।

## जाँच

पहली किताब index होने के बाद:

```bash
python -m unittest discover -s tests -v
node --check web/app.js
```

## आवाज़ और गोपनीयता

शुरुआत में `Sat Sahib · शुरू करें` दबाएँ; browsers user gesture के बिना audio रोक सकते हैं। Browser/device की Hindi TTS आवाज़, speed और pitch इस्तेमाल होते हैं। Voice input समर्थित browser और microphone permission माँगता है; remote hosting में HTTPS चाहिए। Browser speech recognition provider को audio भेज सकता है। App audio या प्रश्नों को disk पर store नहीं करता। Text input fallback हमेशा है। वास्तविक microphone और Hindi voice को उपयोगकर्ता के device पर जाँचना बाकी है।

## सीमाएँ और सार्वजनिक hosting

यह स्थानीय prototype है। Files और प्रश्न बाहर किसी AI API को नहीं भेजे जाते। PDFs का पाठ app instructions के रूप में execute नहीं होता। PDF API पूरी indexed book उपलब्ध कराती है; केवल वे पुस्तकें जोड़ें जिन्हें सभी app उपयोगकर्ताओं के साथ साझा करना उचित हो। मुफ्त Docker hosting और private PDF backup के निर्देश [docs/FREE_HOSTING.md](docs/FREE_HOSTING.md) में हैं। Public deployment से पहले HTTPS, proxy rate limiting और पुस्तक वितरण अनुमति जाँचें। Admin sessions एक घंटे में expire होते हैं; upload 30 MB / 600 पृष्ठ तक सीमित है। वर्तमान rate limiter एक process के लिए है; proxy के पीछे सभी users एक IP दिख सकते हैं। मुफ्त hosting की compute/storage सीमाएँ होती हैं; 24/7 unlimited free hosting शामिल नहीं है।

## Animated design और admin

CSS 3D book, floating orbs और transitions उपलब्ध हैं। `prefers-reduced-motion` पर motion बंद है। सामान्य chat में कोई upload control नहीं है। Admin access, CSRF, file validation और वास्तविक ingestion के tests शामिल हैं।

## Hosting update

Hugging Face Docker hosting returned HTTP 402 (PRO required), so no paid Space was created. The private PDF dataset was uploaded successfully. Free Render deployment is prepared in `render.yaml`; see [docs/RENDER_HOSTING.md](docs/RENDER_HOSTING.md). Deployment requires Render account access.
