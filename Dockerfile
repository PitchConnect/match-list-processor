FROM python:3.9-slim-buster

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY create_group_description.py .

# Set Python path to include src directory
ENV PYTHONPATH=/app

# Run the refactored application
CMD ["python", "-m", "src.app"]