FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY backend /app/backend
RUN python -m pip install --no-cache-dir /app/backend

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "personal_os.interfaces.http.app:app", "--host", "0.0.0.0", "--port", "8000"]
