docker stop nvr_autorecord
docker rm nvr_autorecord
docker build -t nvr_autorecord .
docker run -idt --name nvr_autorecord --net=host --env-file ../.env_nvr nvr_autorecord
