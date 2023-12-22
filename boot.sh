#!/bin/bash
source venv/bin/activate
flask db init
flask db migrate
flask db upgrade
exec gunicorn -b :5001 run:app