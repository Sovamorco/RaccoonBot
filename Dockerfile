FROM python:3.10-alpine

RUN apk add --no-cache git build-base libffi-dev

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

COPY . /raccoonbot
WORKDIR /raccoonbot

ENTRYPOINT ["python", "-u", "mainbot.py"]
