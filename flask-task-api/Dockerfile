# Use official Python image
FROM python:3.9

# Set working directory
WORKDIR /app

# Copy files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir flask psycopg2-binary flask_sqlalchemy

# Expose port
EXPOSE 5000

# Run the app
CMD ["python", "app.py"]
