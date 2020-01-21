docker stop nvr_autorecord
docker rm nvr_autorecord
docker build -t nvr_autorecord .
docker run --env-file=.env -idt --name nvr_autorecord 