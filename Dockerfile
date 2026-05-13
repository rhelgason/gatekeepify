FROM python:3.10-slim

WORKDIR /app

COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt && \
    pip install --no-cache-dir supervisor

COPY . .

ENV PORT=8000

EXPOSE ${PORT}

CMD ["supervisord", "-c", "supervisord.conf"]
