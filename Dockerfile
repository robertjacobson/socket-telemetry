FROM python:3.9

WORKDIR /app

RUN pip install influxdb-client  

ADD server.py .

CMD ["python", "server.py"]