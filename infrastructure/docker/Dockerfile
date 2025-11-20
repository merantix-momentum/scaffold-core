FROM python:3.9-slim


# Install required tools
RUN apt-get update && apt-get install -y \
    curl git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv
ENV UV_VERSION="0.9.3"
RUN curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Copy source code
COPY . .

# Install dependencies
RUN uv sync --frozen --all-extras

ENV PATH="/.venv/bin:$PATH"