FROM python:3.10-slim-bookworm

RUN mkdir -p /app
WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
RUN pip install -e ./

COPY ./src /app/src