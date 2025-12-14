FROM python:3.11-slim

WORKDIR /app

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app .
COPY --from=common . ./common

# Create directory for PDF storage
RUN mkdir -p /data/pdfs

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
