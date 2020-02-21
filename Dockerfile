FROM ubuntu:18.04

RUN apt-get -y update && apt-get -y install python3-pip python3-dev python3-venv ffmpeg
COPY . /autorecord
RUN pip3 install --no-cache-dir -r /autorecord/requirements.txt
RUN mkdir /root/vids
CMD ["python3", "/autorecord/record_daemon.py"]