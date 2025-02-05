#!/bin/bash

# Start Streamlit server 
streamlit run /app/streamlit_app.py &

# Start the FastAPI server in the background
uvicorn api.main:app --host 0.0.0.0 --port 8000 &

# Start the Node.js server in the alfredo_rocket directory
cd /app/alfredo_rocket
node alfredo_rocket.js
