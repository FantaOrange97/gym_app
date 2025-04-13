# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy everything
COPY . .

# Install dependencies
RUN pip install flask bcrypt

# Expose port
EXPOSE 8000

# Run the Flask app
CMD ["python", "app.py"]