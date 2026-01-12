FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY streamlit/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy UI code
COPY streamlit/ .

# Run Streamlit
CMD ["streamlit", "run", "st_app.py", "--server.port=8501", "--server.address=0.0.0.0"]