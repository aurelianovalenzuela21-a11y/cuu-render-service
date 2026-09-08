FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY cuu_daily_quote.py app.py ./

# El navegador Chromium ya viene instalado en esta imagen base de Playwright,
# así que no hace falta correr "playwright install".
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
