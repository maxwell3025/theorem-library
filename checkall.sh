#!/bin/bash

curl localhost:8001/health | jq
curl localhost:8002/health | jq
curl localhost:8003/health | jq
curl localhost:8004/health | jq
