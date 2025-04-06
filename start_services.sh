#!/bin/bash

# Function to handle errors
handle_error() {
    echo "Error occurred in $1"
    exit 1
}

# Start Streamlit server in the background
echo "Starting Streamlit server..."
streamlit run /app/streamlit_app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false &

# Wait for Streamlit to start
sleep 5

# Start the FastAPI server
echo "Starting FastAPI server..."
cd /app && uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload --log-level info

# Keep the container running
wait
