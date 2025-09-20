FROM python:3.11-slim
WORKDIR /app
COPY agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent/ .
ENV PORT=8080
CMD ["gunicorn", "-b", ":8080", "main:app"]