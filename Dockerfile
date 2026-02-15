FROM python:3.10-slim

RUN apt-get update \
    && apt-get install -y \
       exiftool \
       libgl1 \
       libglib2.0-0 \
       build-essential \
       libffi-dev \
       libjpeg-dev \
       zlib1g-dev \
       libcairo2-dev \
       pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application (including assets folder)
COPY . .

EXPOSE 10000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
