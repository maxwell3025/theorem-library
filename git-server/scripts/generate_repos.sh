#!/bin/sh
cd /git-repos
count=0
echo "{\"repositories\":[" > /tmp/repos.json
first=true
for repo in */; do
  repo_name=$(basename "$repo")
  if [ -d "$repo/.git" ]; then
    commit=$(cd "$repo" && git rev-parse HEAD)
    count=$((count + 1))
    if [ "$first" = true ]; then
      first=false
    else
      echo "," >> /tmp/repos.json
    fi
    echo "{\"name\":\"$repo_name\",\"url\":\"http://git-server:8000/$repo_name\",\"commit\":\"$commit\"}" >> /tmp/repos.json
  fi
done
echo "]}" >> /tmp/repos.json
echo "{\"status\":\"healthy\",\"repositories\":$count}" > /tmp/health.json
