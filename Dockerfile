FROM python:3.13-slim

# Tesseract with Polish data reads scanned PDFs, so visitors do not need it installed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-pol \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PRZETARGO_HOSTED=1 \
    LLM_BASE_URL=https://router.huggingface.co/v1 \
    LLM_MODEL=speakleash/Bielik-11B-v3.0-Instruct \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app
COPY back-end2/requirements.txt back-end2/requirements.txt
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r back-end2/requirements.txt -r backend/requirements.txt

COPY back-end2 back-end2
COPY backend backend
COPY front-end front-end
COPY UZP-hacknation-task/dane UZP-hacknation-task/dane
COPY UZP-hacknation-task/oczekiwane-json UZP-hacknation-task/oczekiwane-json

RUN useradd --create-home app && chown -R app /app
USER app

WORKDIR /app/back-end2
EXPOSE 8000
CMD ["python", "api.py"]
