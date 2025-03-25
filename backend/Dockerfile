# Use the official Python image from the Docker Hub
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set working directory
WORKDIR /app

# Install dependencies from requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install packages for database check
RUN apt-get update && apt-get install -y dos2unix netcat-openbsd postgresql-client cron

# Copy Django project files into working directory of container
COPY . .

# Set environment variables for the Cron job
ENV PYTHONPATH "${PYTHONPATH}:/app"
ENV DJANGO_SETTINGS_MODULE "medical_staff_assessment.settings"

# Copy the crontab file to the cron.d directory
COPY cronjobs/crontab /etc/cron.d/crontab

# Give execution rights on the cron jobs
RUN chmod 0644 /etc/cron.d/crontab

# Apply cron jobs
RUN crontab /etc/cron.d/crontab

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Expose the port the app runs on
EXPOSE 8000

# Create startup script and set it as enrtypoint
COPY start.sh /start.sh
RUN dos2unix /start.sh
RUN chmod +x /start.sh
ENTRYPOINT ["/start.sh"]
