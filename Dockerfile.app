FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1\
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY app/src/ ./src/
COPY app/migrations ./migrations/

COPY app/src/static/ ./static/
COPY app/src/index.html ./

ENV PYTHONPATH=/app

RUN useradd --create-home --shell /bin/bash admin
RUN chown -R admin:admin /app
USER admin

EXPOSE 8000

CMD ["python", "src/main.py"]
