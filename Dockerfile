FROM python:3.10.1-slim-buster

ENV POETRY_VERSION=1.1.12
ENV POETRY_VIRTUALENVS_CREATE=false

ENV PYTHONUNBUFFERED 1

RUN apt-get update \
  && apt-get install -y --no-install-recommends  \
    wget  \
    build-essential \
    # Installing Geospatial libraries
    binutils  \
    libproj-dev  \
    gdal-bin \
  # Installing `poetry` package manager:
  # https://github.com/python-poetry/poetry
  && pip install "poetry==$POETRY_VERSION" && poetry --version \
  # Cleaning cache:
  && apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/* \
  && rm -rf ~/.cache/pip/* && rm -rf /usr/share/man/*

WORKDIR /code
COPY ./poetry.lock ./pyproject.toml /code/

RUN poetry run pip install setuptools==59.6.0 \
  && poetry install --no-interaction --no-ansi  \
  && find /usr/local -type f -name '*.pyc' -delete

COPY . /code/

RUN python main.py
