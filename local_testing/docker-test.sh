cd ../

echo "Building Docker image"
docker image build -t cpin-data-collector .

echo "Running Docker image"
docker container run -p 8020:5000 -v $(pwd)/data:/data --rm cpin-data-collector

echo "Cleaning up"
echo y | docker image prune
echo y | docker volume prune