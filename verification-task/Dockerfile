FROM python:3.11-slim

WORKDIR /app

COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=common . ./common

ENV PYTHONUNBUFFERED=1

CMD ["sleep", "100"]
