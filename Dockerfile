FROM python:3-alpine3.10
WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt

EXPOSE 3000

CMD python3 -m gunicorn wsgi --bind 0.0.0.0:3000 --chdir ./