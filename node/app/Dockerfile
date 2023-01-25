# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.9-slim
RUN apt-get update && apt-get install -y procps

ENV APP_HOME /app
WORKDIR $APP_HOME

COPY ./requirements.txt ./
RUN pip install -r requirements.txt

COPY . ./

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app
