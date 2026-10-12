FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-hin ca-certificates && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 app
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=secret,id=build_ca if [ -f /run/secrets/build_ca ]; then PIP_CERT=/run/secrets/build_ca pip install --no-cache-dir -r requirements.txt; else pip install --no-cache-dir -r requirements.txt; fi
COPY --chown=app:app backend backend
COPY --chown=app:app web web
COPY --chown=app:app scripts scripts
RUN mkdir -p /app/data/tessdata && cp /usr/share/tesseract-ocr/5/tessdata/hin.traineddata /app/data/tessdata/ && chown -R app:app /app/data
USER app
ENV DATA_DIR=/app/data COOKIE_SECURE=1 PORT=7860 PYTHONUNBUFFERED=1
EXPOSE 7860
CMD ["bash", "scripts/host.sh"]
