FROM python:3.12-slim AS build
WORKDIR /w
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FIELDSHIFT_DB=/data/fieldshift.db
WORKDIR /app
COPY --from=build /install /usr/local
RUN useradd --create-home --uid 10001 fieldshift && mkdir -p /data && chown fieldshift /data
COPY --chown=fieldshift backend ./backend
COPY --chown=fieldshift frontend ./frontend
USER fieldshift
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import os,sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%s/readyz' % os.environ.get('PORT','8000'), timeout=4).status==200 else 1)"
# One service: the backend also serves frontend/. Render/Fly set $PORT; locally it defaults to 8000.
CMD ["sh", "-c", "uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000}"]
