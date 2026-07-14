FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN addgroup --system mindspark && adduser --system --ingroup mindspark mindspark
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mindspark_bot ./mindspark_bot
RUN mkdir -p /app/data && chown -R mindspark:mindspark /app
USER mindspark
WORKDIR /app/mindspark_bot
EXPOSE 8080
CMD ["python", "main.py"]
