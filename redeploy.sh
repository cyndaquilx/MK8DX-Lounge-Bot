#!/bin/bash
docker cp updatingbot:/app/allowed_phrases.json .
docker build --tag updatingbot .
docker stop updatingbot
docker rm updatingbot
docker run -d --name updatingbot --restart unless-stopped updatingbot