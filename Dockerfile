FROM python:3.10-alpine

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

RUN mkdir -m 700 /src
COPY * /src
WORKDIR /src

ENTRYPOINT ["python", "mainbot.py"]
