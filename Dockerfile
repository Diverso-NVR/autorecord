FROM python:3

ARG VERSION=1

COPY . /autorecord

RUN pip install --no-cache-dir -r /autorecord/requirements.txt

ENV PYTHONPATH /autorecord

CMD ["python", "/autorecord/record_daemon.py"]