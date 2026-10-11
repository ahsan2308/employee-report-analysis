# Use official Python image
FROM python:3.12.15-bookworm

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    unixodbc-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update && ACCEPT_EULA=Y apt-get install -y \
    msodbcsql17 \
    && apt-get clean


# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Default command (for API)
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]