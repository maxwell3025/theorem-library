FROM texlive/texlive:latest

WORKDIR /app

# Install git and Python dependencies
RUN apt-get update && apt-get install -y \
    git \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

COPY ./app ./
COPY --from=common . ./common

ENV PYTHONUNBUFFERED=1

CMD ["python3", "main.py"]
