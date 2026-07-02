FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    apt-transport-https \
    unixodbc \
    unixodbc-dev \
    odbcinst \
    && rm -rf /var/lib/apt/lists/*

# Download and install msodbcsql18 directly
RUN curl -sSL -O https://packages.microsoft.com/debian/12/prod/pool/main/m/msodbcsql18/msodbcsql18_18.4.1.1-1_amd64.deb \
    && ACCEPT_EULA=Y dpkg -i msodbcsql18_18.4.1.1-1_amd64.deb \
    && rm msodbcsql18_18.4.1.1-1_amd64.deb

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Volume pour stocker les données de garde (PDF + JSON persisté)
RUN mkdir -p /app/uploads
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
