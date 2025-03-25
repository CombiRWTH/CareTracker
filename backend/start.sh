#!/bin/bash

# Wait for the PostgreSQL server to be available
while ! nc -z $DB_HOST $DB_PORT; do
  echo "Waiting for PostgreSQL server..."
  sleep 3
done
echo "PostgreSQL started."

# Check if the database exists
DB_EXISTS=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';" | grep -q 1; echo $?)

if [ $DB_EXISTS -eq 1 ]; then
  echo "Database '$DB_NAME' does not exist. Creating..."
  PGPASSWORD=$DB_PASSWORD createdb -h $DB_HOST -U $DB_USER $DB_NAME
  echo "Database '$DB_NAME' created."
else
  echo "Database '$DB_NAME' already exists. Skipping creation."
fi

# Create the database
echo "Making migrations."
python /app/manage.py makemigrations backend
python /app/manage.py migrate

# Create superuser if it does not exist
SUPERUSER_EXISTS=$(python /app/manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print(User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists())")

if [ $SUPERUSER_EXISTS == "False" ]; then
  echo "Superuser does not exist. Creating..."
  python /app/manage.py createsuperuser --noinput || echo "Superuser creation failed."
  echo "Superuser created."
else
  echo "Superuser already exists. Skipping creation."
fi

# Run cronjobs
echo "Running cronjobs."
printenv | grep -v "no_proxy" >> /etc/environment
service cron start
tail -f /var/log/cron.log >> /proc/1/fd/1 2>&1 &

# Fill database with questions from the PPBV
echo "Filling database with questions from the PPBV."
python /app/manage.py loaddata /app/backend/fixtures/questions.json

#Remove the three down in production

# Fill database with dummy stations
echo "Filling database with dummy stations."
python /app/manage.py loaddata /app/backend/fixtures/stations.json

# Fill database with dummy patients
echo "Filling database with  dummy patients."
python /app/manage.py loaddata /app/backend/fixtures/patients.json

# Fill database with dummy patient journies
echo "Filling database with dummy patient journies."
python /app/manage.py loaddata /app/backend/fixtures/patient_transfers.json

# Run server
python /app/manage.py runserver 0.0.0.0:8000


