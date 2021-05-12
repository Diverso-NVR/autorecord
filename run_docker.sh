docker stop nvr_autorecord
docker rm nvr_autorecord
docker build -t nvr_autorecord .
docker run -d \
 -it \
 --restart on-failure \
 --name nvr_autorecord \
 --net=host \
 -v $HOME/creds:/autorecord/creds \
 nvr_autorecord
