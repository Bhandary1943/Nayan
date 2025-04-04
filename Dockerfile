# Use official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for dlib
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    libgtk-3-dev \
    libboost-all-dev \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy files
COPY . /app

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=10000", "--server.address=0.0.0.0"]
