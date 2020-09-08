docker stop nvr_autorecord
docker rm nvr_autorecord
docker build -t nvr_autorecord .
docker run -d \
 -it \
 --name nvr_autorecord \
 --net=host \
 --env-file ../.env_nvr \
 -v $HOME/creds:/autorecord/creds \
 -v /var/log/autorecord:/var/log/autorecord
 nvr_autorecord
