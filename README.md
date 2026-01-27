# Web-Programming-team

1. create venv and activate \n
        -> python3 -m venv venv
        -> source venv/bin/activate  #for mac
    for windows:
        -> python -m venv venv
        -> venv/scripts/activate.ps1

    pip installation:
        -> pip install django
        -> pip install django-tailwind
        -> pip install pyotp

2. runproject
        -> cd job
        -> python3 manage.py makemigrations
        -> python3 manage.py migrate
        -> python3 manage.py runserver

    for windows :
        cd job
        python manage.py makemigrations
        python manage.py migrate
        python manage.py runserver



3. run tailwindCss 
        -> python3 manage.py tailwind start

    for windows:
        -> python manage.py tailwind start


4. library 
     -> pip install Pillow