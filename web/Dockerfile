FROM python:3.7.9-slim-buster

ENV PYTHONUNBUFFERED 1
ENV TZ=Europe/Moscow

WORKDIR /code
COPY . /code/

RUN pip install -r requirements.txt

RUN echo "Europe/Moscow" > /etc/timezone
RUN dpkg-reconfigure -f noninteractive tzdata