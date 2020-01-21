docker stop nvr_autorecord
docker rm nvr_autorecord
docker build -t nvr_autorecord .
sudo docker run -idt --env-file .env nvr_autorecord

