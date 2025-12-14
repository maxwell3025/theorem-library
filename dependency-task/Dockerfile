FROM python:3.11-slim

WORKDIR /app

# Install git for cloning repositories
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app .
COPY --from=common . ./common

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
