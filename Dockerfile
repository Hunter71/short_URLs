FROM python:3.11 as base

WORKDIR /code

ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip setuptools wheel \
    && apt-get update \
    && apt install -yq \
        curl \
    && curl -sSL https://install.python-poetry.org/ | python -

ENV PATH="${PATH}:/root/.local/bin"

COPY pyproject.toml /code/pyproject.toml
COPY poetry.lock /code/poetry.lock

RUN poetry config virtualenvs.create false

EXPOSE 8000


FROM base as dev

RUN poetry install -vv --no-interaction --no-ansi

COPY . /code/


FROM base as release

RUN poetry install --no-interaction --no-ansi --no-dev

COPY . /code/
