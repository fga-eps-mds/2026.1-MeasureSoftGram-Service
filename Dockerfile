FROM python:3.10-buster

ENV PYTHONUNBUFFERED 1

EXPOSE 80
EXPOSE 8181

RUN mkdir /src
WORKDIR /src
COPY src requirements.txt /src/

RUN pip install -r requirements.txt

# copy project
COPY . .

# collect static files
RUN python manage.py collectstatic --noinput