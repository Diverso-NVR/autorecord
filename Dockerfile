FROM ubuntu:18.04

RUN apt-get -y update && apt-get -y install python3-pip python3.8-dev ffmpeg

ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get -y install libpq-dev postgresql postgresql-contrib

COPY ./autorecord /autorecord
COPY ./requirements.txt /

RUN python3.8 -m pip install -r requirements.txt
RUN mkdir /root/vids
RUN mkdir /var/log/autorecord

CMD ["python3.8", "/autorecord/app.py"]
