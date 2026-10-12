> अपडेट: Hugging Face ने Docker Space creation पर HTTP 402 / PRO required लौटाया। नीचे की पुरानी HF hosting योजना अब लागू नहीं है। मुफ्त विकल्प के लिए [RENDER_HOSTING.md](RENDER_HOSTING.md) देखें। Private library dataset बन गया है; Space नहीं बना।

# ritikbhai के लिए मुफ्त hosting

लक्ष्य: Hugging Face **Docker Space**, free CPU hardware। कोई paid AI API या paid storage enable न करें। Free Spaces सो सकते हैं और उनकी local disk स्थायी नहीं मानी जाती। वास्तविक quotas और free CPU availability deployment के समय dashboard पर जाँचें। यहाँ से Hugging Face network access अभी blocked है; deployment और remote backup का live परीक्षण नहीं हुआ है।

## तैयार नाम

- Public app Space: `ritikbhai/sat-sahib-assistant`
- Private PDF backup dataset: `ritikbhai/sat-sahib-library`

ये प्रस्तावित नाम हैं; repos अभी create नहीं हुए हैं।

## सुरक्षित deployment

1. Hugging Face Settings → Access Tokens में ऐसा fine-grained write token बनाएँ जो चुने हुए Space और private dataset को manage कर सके। Token chat, Git या source code में न डालें। Codex environment settings में `HF_TOKEN` requirement का secure value भरें और save करें। यदि scoped token repo creation की अनुमति न दे, user-owned repos पहले dashboard से बनाएँ और manual upload विधि इस्तेमाल करें।
2. Network settings में `huggingface.co` access allow करें। API/file transfers किसी अतिरिक्त host पर denied हों तो उसी reported host को allow करें; verification बंद न करें।
3. Cloud terminal में, runtime credential आने के बाद:

```bash
cd /workspace/Kabir-Ai
.venv/bin/python scripts/deploy_hf.py
```

यह script existing Space/dataset को overwrite नहीं करती। कोई partial failure हो तो बने हुए repos की स्थिति जाँचें; बिना देखे बार-बार script न चलाएँ। Script free default hardware उपयोग करती है; paid hardware request नहीं करती।

4. Space → Settings में निम्न settings जोड़ें:

| प्रकार | नाम | क्या भरना है |
|---|---|---|
| Secret | `ADMIN_PASSWORD` | अपना नया, unique password; कम से कम 16 अक्षर। Password chat में न भेजें। |
| Secret | `HF_TOKEN` | केवल private library dataset को read/write करने वाला token। Deployment token से अलग scoped token बेहतर है। |
| Variable | `HF_DATASET_REPO` | `ritikbhai/sat-sahib-library` |

`ADMIN_PASSWORD` server-side password है। इसे browser bundle, Git या public variable में न रखें। कोई default password नहीं है; setting missing होने पर admin बंद रहता है। Docker में secure cookies default हैं।

5. Space rebuild/restart के बाद public chat खोलें। Admin उसी app के `/admin.html` path पर है। Admin password डालकर login करें, पुस्तक का नाम और PDF चुनें। 30 MB / 600 पृष्ठ की सीमा है। Upload के बाद indexing पूरी होने और cloud backup सफल होने की सूचना देखें। फिर public chat में पुस्तक खोजें।
6. HF token/backup setting न होने पर upload local रहेगा; reset पर खो सकता है। Admin का “Cloud backup फिर चलाएँ” button failed backup दोबारा भेजता है। Dataset हमेशा private होना चाहिए। App approved PDF sources users को उपलब्ध कराता है। Backup private रखने का मतलब app के PDF sources private होना नहीं है।

## यदि स्वयं dashboard से upload करना हो

Docker Space बनाएँ और README.md, Dockerfile, requirements.txt, backend/, web/ तथा scripts/host.sh source files upload करें। `.env`, `.venv`, `.git`, data/ या credentials को public Space में upload **न करें**। वही Space settings भरें। अलग private dataset बनाएँ। पहली किताब `/admin.html` से upload कर सकते हैं; यह थोड़ा समय लेगी।

## Go-live जाँच

- बिना login upload request को 401 मिलना चाहिए।
- गलत password reject हो; 8 प्रयास के बाद 10 मिनट का विराम।
- Admin upload और backup सफल हों; server restart के बाद किताब फिर दिखाई दे।
- हिंदी प्रश्न पर पुस्तक-अंश और PDF पृष्ठ खुलें; असंबंधित प्रश्न पर निर्धारित fallback हो।
- फ़ोन पर microphone permission, “Sat Sahib” और हिंदी TTS जाँचें।

एक app worker रखें। Upload OCR resource use बढ़ाता है। Public requests का in-memory rate limiter proxy के पीछे shared IP पर लागू हो सकता है; यह prototype बड़े traffic के लिए तैयार नहीं है। App generative model नहीं चलाता; केवल PDF अंश खोजता है।
