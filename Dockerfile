FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml /app/
COPY tripit_mcp/ /app/tripit_mcp/
RUN uv venv --path /app/.venv --python python3.10 && \
    . /app/.venv/bin/activate && \
    uv pip install .

COPY . /app/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["/app/.venv/bin/python", "-m", "tripit_mcp"]
