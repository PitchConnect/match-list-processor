#!/bin/bash
docker stop process-matches-service
docker rm process-matches-service
docker build -t process-matches-app .
docker run --name process-matches-service --network fogis-network -v process-matches-data:/data process-matches-app