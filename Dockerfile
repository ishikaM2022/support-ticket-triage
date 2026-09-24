FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements-docker.txt ./
RUN python -m pip install torch==2.14.0+cpu --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install -r requirements-docker.txt \
    && python -m pip check
RUN useradd --create-home --uid 10001 triage && mkdir -p /app/data && chown triage:triage /app/data
COPY --chown=triage:triage app.py classifier.py database.py urgency.py ./
COPY --chown=triage:triage artifacts/ ./artifacts/
USER triage
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 CMD python -c "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT', '8501') + '/_stcore/health', timeout=3)"
CMD ["sh", "-c", "python -m streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-8501} --server.fileWatcherType=none --browser.gatherUsageStats=false"]
