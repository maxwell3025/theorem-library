#!/bin/bash

for i in {1..50}; do
  curl http://localhost/dependency-service/projects -X PUT -d '{"repo_url":"http://git-server:8000/advanced-proofs","commit":"9c4a2f3ad74c41cddc0697cdd11e6774df7fc801"}' -H "Content-Type: application/json" > /dev/null
done
