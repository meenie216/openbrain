FROM python:3.12-slim
WORKDIR /app

COPY mcp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common ./common
COPY mcp/db.py mcp/server.py ./

ENV PYTHONPATH=/app

CMD ["python", "server.py"]
