FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ADB is required to control Android devices (recommended to use WiFi ADB when running in Docker).
RUN apt-get update \
  && apt-get install -y --no-install-recommends android-tools-adb ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN pip install -U pip setuptools wheel \
  && pip install -r requirements.txt \
  && pip install -e .

CMD ["python", "main.py"]

