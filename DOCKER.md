# Run Support Ticket Triage in Docker

This repository includes Docker packaging for the Streamlit application, saved classifier artifacts, and persistent SQLite storage.

## Install

1. Start Docker Desktop in Linux-container mode.
2. Stop the existing Streamlit server with Ctrl+C to free port 8501.
3. Back up your existing database.py (for example, database-before-docker.py).
4. Extract all files from this bundle into your project folder, alongside app.py. Replace database.py with the included version. Keep your existing app.py, classifier.py, urgency.py and artifacts folder. Keep requirements-local.txt as your local environment snapshot.
5. In the project's PowerShell terminal:

```powershell
.\.venv\Scripts\python.exe prepare_docker_data.py
docker compose up --build -d
docker compose logs --tail 80 triage
```

Open http://localhost:8501. Initial package installation may take several minutes.
The build requires your saved artifacts/embedding_model, artifacts/knn.joblib,
artifacts/train_categories.npy, artifacts/config.json and urgency prompt file.

## Persistence

Docker uses data/triage.db in your project folder. The preparation script copies your existing root triage.db using SQLite's backup API, including review history, and refuses to overwrite an existing destination. Your original database remains untouched.

The modified database.py uses TRIAGE_DB_PATH when supplied. Ordinary local runs still default to the original root triage.db. After migration these are separate databases. To run locally against the Docker database, first stop Docker, then use:

```powershell
docker compose down
$env:TRIAGE_DB_PATH = Join-Path $PWD 'data\triage.db'
.\.venv\Scripts\python.exe -m streamlit run app.py --server.fileWatcherType none
```

Do not delete data/ if you want to keep Docker's ticket history. A persistent folder is not a backup; periodically back up the database separately.

## Verify

Check your existing tickets appear. Submit a test ticket and note its ID. Run docker compose down, then docker compose up -d. Confirm that ticket and its saved notes remain. Docker health checks confirm the web server responds; they do not test classifier quality or API credentials.

## Routine commands

```powershell
docker compose ps
docker compose logs --tail 80 triage
docker compose down
docker compose up -d
# After changing application code or artifacts:
docker compose up --build -d
```

Only localhost is published. Enter the Portkey key through your existing password input when you request an AI suggestion. No key is included in this package or build configuration. Saved model artifacts are copied into the image; notebooks, databases, caches and local secrets are excluded.

## Version and verification notes

Python 3.11 matches your local Python major/minor version. Runtime package versions are taken from your supplied requirements-local.txt; notebook packages are omitted. CPU PyTorch installs from the official CPU wheel index. The remaining transitive dependencies are resolved during build, so this is not a complete Linux lockfile. Do not silently downgrade scikit-learn to make a build pass: your serialized classifier depends on a compatible environment.

The database edit and migration logic were checked locally. Docker was unavailable in the preparation environment. The user subsequently built and ran the image on Windows and confirmed that a ticket survived container removal/recreation. This has not been independently repeated on another machine. If a version cannot be found, share the specific build error before changing versions. On a Linux host, the bind-mounted data folder must be writable by container UID 10001; Docker Desktop on Windows manages bind mount permissions differently.

References: [Streamlit Docker guide](https://docs.streamlit.io/deploy/tutorials/docker), [PyTorch installation guide](https://docs.pytorch.org/get-started/locally/).

