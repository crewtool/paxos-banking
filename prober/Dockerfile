# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.9-slim

ENV APP_HOME /app
WORKDIR $APP_HOME

COPY ./requirements.txt ./
RUN pip install -r requirements.txt

COPY . ./

CMD [ "python3", "prober.py" ]
