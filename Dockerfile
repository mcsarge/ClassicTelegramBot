FROM python:3.7.6-slim-stretch

RUN pip install --no-cache-dir pymodbus paho-mqtt

ADD bot/app.py /
ADD bot/support/*.py support/

ENTRYPOINT ["python3", "app.py"]