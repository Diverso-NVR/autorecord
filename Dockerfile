FROM python:3

ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt -y install ffmpeg libpq-dev postgresql postgresql-contrib

COPY ./autorecord /autorecord
COPY ./requirements.txt /

RUN pip3 install -r requirements.txt
RUN mkdir /root/vids
RUN mkdir /var/log/autorecord

CMD ["python", "/autorecord/app.py"]
