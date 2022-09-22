echo `date +"%s"`>version.txt
docker build . -t 192.168.4.130:5002/tobybot:latest
docker push 192.168.4.130:5002/tobybot:latest
echo New version is `cat version.txt`