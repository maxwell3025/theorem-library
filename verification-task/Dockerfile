FROM python:3.11-slim

WORKDIR /app

# Install git and Lean 4 dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install elan (Lean version manager)
RUN curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh -s -- -y --default-toolchain none
ENV PATH="/root/.elan/bin:${PATH}"
RUN elan default stable

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=common . ./common
COPY ./app ./app

ENV PYTHONUNBUFFERED=1

CMD ["python", "app/main.py"]
