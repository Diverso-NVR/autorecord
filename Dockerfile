FROM python:3.8

ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt -y update && apt -y install ffmpeg libpq-dev postgresql postgresql-contrib

COPY ./autorecord /autorecord
COPY ./requirements.txt /

RUN python3.8 -m pip install -r requirements.txt
RUN mkdir /root/vids
RUN mkdir /var/log/autorecord

ENV PYTHONPATH=/autorecord

CMD ["python", "/autorecord/app.py"]
