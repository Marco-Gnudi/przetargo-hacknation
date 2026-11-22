# Optional self-contained alternative to start.sh: Python, Tesseract and Polish OCR data in one image.
#   docker build -t przetargo .
#   docker run --rm -p 127.0.0.1:8000:8000 -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" przetargo
#   docker run --rm -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" -e MISTRAL_API_KEY przetargo python main.py
FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-pol tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# HOST is 0.0.0.0 only inside the container; publish it as 127.0.0.1:8000 so it stays local.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY back-end2 back-end2
COPY backend backend
COPY front-end front-end
COPY UZP-hacknation-task/dane UZP-hacknation-task/dane
COPY UZP-hacknation-task/oczekiwane-json UZP-hacknation-task/oczekiwane-json
COPY main.py doctor.py ./

# Writable for any --user "$(id -u):$(id -g)", so output files on Linux hosts belong to the caller.
RUN mkdir -p input output backend/.cache && chmod -R a+rwX input output backend/.cache

EXPOSE 8000
CMD ["python", "back-end2/api.py"]
