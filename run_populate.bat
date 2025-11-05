@echo off
echo Running populate_sample_data.py...
python manage.py shell < populate_sample_data.py
echo Done!
pause
