FROM ubuntu:18.04

RUN apt-get -y update && apt-get -y install python3-pip python3-dev python3-venv ffmpeg

ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get -y install libpq-dev postgresql postgresql-contrib

COPY ./autorecord /autorecord
COPY ./requirements.txt /

RUN pip3 install -r requirements.txt
RUN mkdir /root/vids

CMD ["python3", "/autorecord/app.py"]
