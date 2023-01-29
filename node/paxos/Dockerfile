# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.10-slim
RUN apt-get update && apt-get install -y procps

ENV APP_HOME /app
WORKDIR $APP_HOME

COPY ./requirements.txt ./
RUN pip install -r requirements.txt

COPY . ./

CMD exec gunicorn --bind :$PORT --workers 1 -k uvicorn.workers.UvicornWorker paxos:app
