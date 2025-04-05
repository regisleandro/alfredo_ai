#!/bin/bash

# Start Streamlit server 
streamlit run /app/streamlit_app.py &

# Start the FastAPI server in the background
uvicorn api.main:app --host 0.0.0.0 --port 8000 &

