# Manual Testing with curl

This document provides curl commands for manually interacting with the dependency service and other services in the theorem-library system.

## Prerequisites

1. Ensure all services are running:
   ```bash
   docker compose up --build -d
   ```

2. Wait for services to be healthy:
   ```bash
   docker compose ps
   ```

## Dependency Service

The dependency service is available at `http://localhost/dependency-service` (through nginx) or `http://localhost:8001` (direct).

### Health Check

```bash
# Check if the dependency service is healthy
curl -X GET http://localhost/dependency-service/health | jq
```

### List All Projects

```bash
# Get all projects in the database
curl -X GET http://localhost/dependency-service/projects | jq
```

### Add a Project

First, get available repositories from the git-server:

```bash
# List available test repositories
curl -X GET http://localhost:8005/repositories | jq

# Save the output to use repository URLs and commits
```

Then add a project (replace URL and commit with actual values):

```bash
# Add base-math project
curl -X POST http://localhost/dependency-service/projects \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "http://git-server:8000/base-math",
    "commit": "abc123def456..."
  }' | jq

# The response will include a task_id - save this to check status
```

### Get Project Dependencies

```bash
# Get dependencies for a specific project
# (URL-encode the repo_url if needed)
curl -X GET "http://localhost/dependency-service/projects/http:%2F%2Fgit-server:8000%2Fbase-math/abc123def456.../dependencies" | jq
```

### Manually Add a Dependency

```bash
# Add a dependency relationship between two projects
# (Both projects must already exist in the database)
curl -X POST http://localhost/dependency-service/dependencies \
  -H "Content-Type: application/json" \
  -d '{
    "source_repo": "http://git-server:8000/algebra-theorems",
    "source_commit": "abc123...",
    "dependency_repo": "http://git-server:8000/base-math",
    "dependency_commit": "def456..."
  }' | jq
```

## Git Test Server

The git-server is available at `http://localhost:8005`.

### Health Check

```bash
# Check git-server health and repository count
curl -X GET http://localhost:8005/health | jq
```

### List Repositories

```bash
# Get all available test repositories with their commits
curl -X GET http://localhost:8005/repositories | jq

# Pretty print with repository names and URLs
curl -X GET http://localhost:8005/repositories | jq '.repositories[] | {name, url, commit}'
```

### Clone a Repository

```bash
# Clone one of the test repositories
git clone http://localhost:8005/base-math
cd base-math
git log --oneline
cat lakefile.toml
cat math-dependencies.json
```

## Complete Workflow Example

Here's a complete example of adding interconnected packages:

```bash
# 1. Get repository information
REPOS=$(curl -s http://localhost:8005/repositories | jq -r '.repositories')

# 2. Extract repository details
BASE_MATH_URL=$(echo "$REPOS" | jq -r '.[] | select(.name=="base-math") | .url')
BASE_MATH_COMMIT=$(echo "$REPOS" | jq -r '.[] | select(.name=="base-math") | .commit')

ALGEBRA_URL=$(echo "$REPOS" | jq -r '.[] | select(.name=="algebra-theorems") | .url')
ALGEBRA_COMMIT=$(echo "$REPOS" | jq -r '.[] | select(.name=="algebra-theorems") | .commit')

ADVANCED_URL=$(echo "$REPOS" | jq -r '.[] | select(.name=="advanced-proofs") | .url')
ADVANCED_COMMIT=$(echo "$REPOS" | jq -r '.[] | select(.name=="advanced-proofs") | .commit')

# 3. Add base-math (no dependencies)
echo "Adding base-math..."
curl -X POST http://localhost/dependency-service/projects \
  -H "Content-Type: application/json" \
  -d "{\"repo_url\": \"$BASE_MATH_URL\", \"commit\": \"$BASE_MATH_COMMIT\"}" | jq

# Wait for processing
sleep 5

# 4. Add algebra-theorems (depends on base-math)
echo "Adding algebra-theorems..."
curl -X POST http://localhost/dependency-service/projects \
  -H "Content-Type: application/json" \
  -d "{\"repo_url\": \"$ALGEBRA_URL\", \"commit\": \"$ALGEBRA_COMMIT\"}" | jq

sleep 5

# 5. Add advanced-proofs (depends on both)
echo "Adding advanced-proofs..."
curl -X POST http://localhost/dependency-service/projects \
  -H "Content-Type: application/json" \
  -d "{\"repo_url\": \"$ADVANCED_URL\", \"commit\": \"$ADVANCED_COMMIT\"}" | jq

sleep 5

# 6. List all projects
echo "All projects:"
curl -s http://localhost/dependency-service/projects | jq

# 7. Check dependencies for advanced-proofs
echo "Dependencies for advanced-proofs:"
ENCODED_URL=$(echo "$ADVANCED_URL" | jq -sRr @uri)
curl -s "http://localhost/dependency-service/projects/$ENCODED_URL/$ADVANCED_COMMIT/dependencies" | jq
```

## Other Services

### Verification Service

```bash
# Health check
curl -X GET http://localhost/verification-service/health | jq
```

### PDF Service

```bash
# Health check
curl -X GET http://localhost/pdf-service/health | jq
```

### LaTeX Service

```bash
# Health check
curl -X GET http://localhost/latex-service/health | jq
```

## Troubleshooting

### Check Service Logs

```bash
# View dependency service logs
docker logs dependency-service

# View dependency worker logs (processes the git cloning)
docker logs dependency-worker

# View git-server logs
docker logs git-server

# Follow logs in real-time
docker logs -f dependency-worker
```

### Check Service Health

```bash
# Check all service statuses
docker compose ps

# Check specific service health
docker inspect dependency-service --format='{{.State.Health.Status}}'
```

### Reset Database

```bash
# Stop all services and remove volumes
docker compose down --volumes

# Start fresh
docker compose up --build -d
```

## Tips

1. **URL Encoding**: When repo URLs contain special characters, encode them:
   ```bash
   ENCODED_URL=$(echo "http://git-server:8000/base-math" | jq -sRr @uri)
   ```

2. **Pretty JSON**: Always pipe to `jq` for readable output

3. **Save Output**: Save task IDs and commit hashes for later use:
   ```bash
   TASK_ID=$(curl -s ... | jq -r '.task_id')
   ```

4. **Wait for Tasks**: The Celery workers process tasks asynchronously. Wait a few seconds between adding projects and querying their dependencies.
