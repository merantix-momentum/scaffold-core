FROM python:3.9-slim

# Install required tools
RUN apt-get update && apt-get install -y \
    curl git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Configure Poetry environment
ENV POETRY_VERSION="1.7.1"
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VIRTUALENVS_CREATE=false

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copy dependency files
ADD pyproject.toml poetry.lock ./

# Install dependencies
RUN /opt/poetry/bin/poetry install --no-interaction --no-ansi --no-root --all-extras --with docs && \
    /opt/poetry/bin/poetry -n cache clear --all .

ADD . .
