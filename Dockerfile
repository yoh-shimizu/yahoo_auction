FROM python:3.7-slim-buster
WORKDIR /app

# apt-getのアップデートなど
RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get install -y apt-utils git sudo nano vim

RUN pip install \
    selenium \
    beautifulsoup4 \
    requests