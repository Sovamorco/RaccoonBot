FROM python:3.10-alpine

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

RUN apk add --no-cache git

RUN mkdir -m 700 /raccoonbot
COPY * /raccoonbot
WORKDIR /raccoonbot

ENTRYPOINT ["python", "-u", "mainbot.py"]
