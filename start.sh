#!/bin/sh
# Launch analyzer (port 5002) and anonymizer (port 5001) as separate processes.
uvicorn app.analyzer_app:app --host 0.0.0.0 --port 5002 &
uvicorn app.anonymizer_app:app --host 0.0.0.0 --port 5001 &
wait
