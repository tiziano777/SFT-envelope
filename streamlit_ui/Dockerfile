FROM python:3.10-slim

WORKDIR /app

COPY streamlit_ui/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Also install envelope for validation
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
