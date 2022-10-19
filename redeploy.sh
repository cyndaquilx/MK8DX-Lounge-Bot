#!/bin/bash
docker cp mk8dxbot:/app/allowed_phrases.json .
docker build --tag mk8dxbot .
docker stop mk8dxbot
docker rm mk8dxbot
docker run -d --name mk8dxbot --restart unless-stopped mk8dxbot