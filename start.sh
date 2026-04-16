#!/bin/bash

# Start cron daemon
service cron start

# Run Django server
python manage.py runserver 0.0.0.0:8000
