FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 180 -r requirements.txt

COPY app ./app

RUN useradd -u 1001 -r -g 0 -d /app -s /sbin/nologin appuser && \
    chown -R 1001:0 /app && \
    chmod -R g=u /app
USER 1001

EXPOSE 8080

ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
