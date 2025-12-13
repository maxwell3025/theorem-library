# theorem-library
Created as a project for COMPSCI 426

## Project Title and Description
This system is a library of formally verified mathematical proofs alongside human-readable proofs.
Importantly, unlike a package manager, this is focused on the human-level dependencies, unlike the package managers for formal verification languages, which focus on software dependencies.
For instance, a dependency for managing language constructs would not be considered a dependency here, since it is not a feature of the proof, but rather the way that it was formalized.

This system manages proofs using Git commits containing Lean 4 packages with additional folders and files to add human-level dependency and documentation.
The system provices a REST API for running Lean 4 on the proofs to formally verify them, running LaTeX to build the human-readable proofs, and querying the dependency graph to find out whether any given proof is itself verified, whether it has a fully verified network of dependencies, and how many proofs depend on it.

## Architecture Overview
![Architecture Diagram](figures/architecture_diagram.png)

This program uses a microservices architectecture.
The services are currently mapped to host ports `8000`-`8004`(inclusive).
In particular, there are 4 systems:

### Dependency Service
This service is responsible for managing dependency data and exposing analytics queries on this dependency data.
For instance, users will be able to query a list of proofs that any given proof depends on.
This service will pull only `lakefile.toml`, and `math-dependencies.json` from the Git repository to validate it and add all of the metadata to the database.
For almost all of its functionaltiy, this service can function independently, since it only makes queries to the database.

#### Dependencies
- This service depends on the database.

### Verification Service
This service is responsible for managing Lean 4 test runs and queuing up those runs.
This is a separate service because compiling and running Lean 4 packages is a slow task that should be able to scale independently.
This will also asynchronously update the Lean status of each Git repo/commit pair in the database.

#### Dependencies
- This service depends on the database.

### PDF Server
This service handles storing and serving PDF documents containing the human readable proofs.
This is separate from the other services since large file transfers are a large workload that shouldn't interfere with (comparatively) quick tasks like querying the database.

#### Dependencies
- No dependencies.

### LaTeX Service
This service compiles LaTeX files and handles queueing of LaTeX jobs.
This is a separate service because compiling LaTeX projects is a slow task that should be able to scale independently.
This will also asynchronously update the LaTeX status of each Git repo/commit pair in the database.

#### Dependencies
- This service depends on the database.
- This service depends on the PDF Server.

## Prerequisites
This project requires the following software to be present on the host:
- Docker
- Docker Compose
- Python 3.11 (for development)
- curl (for testing)
- jq (for testing)

## Installation & Setup
I am on Linux, so I am using the Docker Compose plugin.
If you are using the standalone version, replace all instances of `docker compose` with
`docker-compse`.

First, change directories into the root of the project.
To verify that you are in the right folder, run the following command:
```bash
ls
```
This should list at least the following files and folders:
```
common
dependency-service
docker-compose.yml
figures
latex-service
LICENSE
pdf-service
README.md
verification-service
```

Next, populate `.env`
```bash
NEO4J_USER=neo4j
NEO4J_PASSWORD="<insert password>"
```
Next, to run the system, run the following command:
```bash
docker compose up --build -d
```

To stop the system, run the following command:
```bash
docker compose stop
docker compose down
```

## Usage Instructions
Currently, the only way to use the system is by running healthchecks.
### Neo4j Browser
Access the Neo4j Browser dashboard at:
```
http://localhost:8000
```
Login with the credentials from your `.env` file (NEO4J_USER and NEO4J_PASSWORD).

### Neo4j Health Check
```bash
curl -X GET localhost:8001/health | jq '.dependencies.neo4j'
# Example response (from dependency service which checks Neo4j):
# {
#   "status": "healthy",
#   "response_time_ms": 5
# }
```

### Dependency Service
```bash
curl -X GET localhost:8001/health | jq
# Example response:
# {
#   "status": "healthy",
#   "service": "dependency-service",
#   "dependencies": {
#     "neo4j": {
#       "status": "healthy",
#       "response_time_ms": 4
#     }
#   }
# }
```

### Verification Service
```bash
curl -X GET localhost:8002/health | jq
# Example response:
# {
#   "status": "healthy",
#   "service": "verification-service",
#   "dependencies": {
#     "neo4j": {
#       "status": "healthy",
#       "response_time_ms": 4
#     }
#   }
# }
```

### PDF Service
```bash
curl -X GET localhost:8003/health | jq
# Example response:
# {
#   "status": "healthy",
#   "service": "pdf-service",
#   "dependencies": {}
# }
```

### LaTeX Service
```bash
curl -X GET localhost:8004/health | jq
# Example response:
# {
#   "status": "healthy",
#   "service": "latex-service",
#   "dependencies": {
#     "neo4j": {
#       "status": "healthy",
#       "response_time_ms": 4
#     },
#     "pdf-service": {
#       "status": "healthy",
#       "response_time_ms": 1
#     }
#   }
# }
```


## API Documentation
### Dependency Service
#### `GET /health`
##### Request
Body should be empty

##### Response
Will have status code `200` if healthy and `503` if unhealthy
Will have a body with shape
```json
{
  "service": "dependency-service",
  "status": "healthy|unhealthy",
  "dependencies": {
    "neo4j": {
      "status": "healthy|unhealthy|timeout",
      "response_time_ms?": "int"
    }
  }
}
```
Where
- `service` is the name of the service,
- `status` is either `"healthy"` or `"unhealthy"` depending on if the service is healthy or not
- `dependencies` is a dictionary of services that this service depends on with the following healthcheck information:
  - `dependencies[x].status` is `"healthy"`, `"unhealthy"`, or `"timeout"` depending on if the service is healthy or not and if the request was successful.
  - `dependencies[x].response_time_ms` is only present if `status` is `"healthy"` or `"unhealthy"`, and it is the integer number of milliseconds that the response took.


##### Example
```bash
curl -X GET localhost:8001/health | jq
# {
#   "status": "healthy",
#   "service": "dependency-service",
#   "dependencies": {
#     "neo4j": {
#       "status": "healthy",
#       "response_time_ms": 4
#     }
#   }
# }
```

### Verification Service
#### `GET /health`
##### Request
Body should be empty

##### Response
Will have status code `200` if healthy and `503` if unhealthy
Will have a body with shape
```json
{
  "service": "verification-service",
  "status": "healthy|unhealthy",
  "dependencies": {
    "neo4j": {
      "status": "healthy|unhealthy|timeout",
      "response_time_ms?": "int"
    }
  }
}
```
Where
- `service` is the name of the service,
- `status` is either `"healthy"` or `"unhealthy"` depending on if the service is healthy or not
- `dependencies` is a dictionary of services that this service depends on with the following healthcheck information:
  - `dependencies[x].status` is `"healthy"`, `"unhealthy"`, or `"timeout"` depending on if the service is healthy or not and if the request was successful.
  - `dependencies[x].response_time_ms` is only present if `status` is `"healthy"` or `"unhealthy"`, and it is the integer number of milliseconds that the response took.

##### Example
```bash
curl -X GET localhost:8002/health | jq
# {
#   "status": "healthy",
#   "service": "verification-service",
#   "dependencies": {
#     "neo4j": {
#       "status": "healthy",
#       "response_time_ms": 4
#     }
#   }
# }
```

### PDF Service
##### Request
Body should be empty

##### Response
Will have status code `200` if healthy and `503` if unhealthy
Will have a body with shape
```json
{
  "service": "dependency-service",
  "status": "healthy|unhealthy",
  "dependencies": {}
}
```
Where
- `service` is the name of the service,
- `status` is either `"healthy"` or `"unhealthy"` depending on if the service is healthy or not
Note that `dependencies` is an empty object since this service has no dependencies

##### Example
#### `GET /health`
```bash
curl -X GET localhost:8003/health | jq
# {
#   "status": "healthy",
#   "service": "pdf-service",
#   "dependencies": {}
# }
```

### LaTeX Service
#### `GET /health`
##### Request
Body should be empty

##### Response
Will have status code `200` if healthy and `503` if unhealthy
Will have a body with shape
```json
{
  "service": "dependency-service",
  "status": "healthy|unhealthy",
  "dependencies": {
    "neo4j": {
      "status": "healthy|unhealthy|timeout",
      "response_time_ms?": "int"
    },
    "pdf-service": {
      "status": "healthy|unhealthy|timeout",
      "response_time_ms?": "int"
    }
  }
}
```
Where
- `service` is the name of the service,
- `status` is either `"healthy"` or `"unhealthy"` depending on if the service is healthy or not
- `dependencies` is a dictionary of services that this service depends on with the following healthcheck information:
  - `dependencies[x].status` is `"healthy"`, `"unhealthy"`, or `"timeout"` depending on if the service is healthy or not and if the request was successful.
  - `dependencies[x].response_time_ms` is only present if `status` is `"healthy"` or `"unhealthy"`, and it is the integer number of milliseconds that the response took.

##### Example
```bash
curl -X GET localhost:8004/health | jq
# {
#   "status": "healthy",
#   "service": "latex-service",
#   "dependencies": {
#     "neo4j": {
#       "status": "healthy",
#       "response_time_ms": 4
#     },
#     "pdf-service": {
#       "status": "healthy",
#       "response_time_ms": 1
#     }
#   }
# }
```

## Testing
To test the health of each of the services, run the following commands in Bash:
### Postgres
```bash
pg_isready -h localhost -p 8000
# Example response:
# localhost:8000 - accepting connections
```

### Dependency Service
```bash
curl -X GET localhost:8001/health | jq
# Example response:
# {
#   "status": "healthy",
#   "service": "dependency-service",
#   "dependencies": {
#     "neo4j": {
#       "status": "healthy",
#       "response_time_ms": 4
#     }
#   }
# }
```

### Verification Service
```bash
curl -X GET localhost:8002/health | jq
# Example response:
# {
#   "status": "healthy",
#   "service": "verification-service",
#   "dependencies": {
#     "neo4j": {
#       "status": "healthy",
#       "response_time_ms": 4
#     }
#   }
# }
```

### PDF Service
```bash
curl -X GET localhost:8003/health | jq
# Example response:
# {
#   "status": "healthy",
#   "service": "pdf-service",
#   "dependencies": {}
# }
```

### LaTeX Service
```bash
curl -X GET localhost:8004/health | jq
# Example response:
# {
#   "status": "healthy",
#   "service": "latex-service",
#   "dependencies": {
#     "neo4j": {
#       "status": "healthy",
#       "response_time_ms": 4
#     },
#     "pdf-service": {
#       "status": "healthy",
#       "response_time_ms": 1
#     }
#   }
# }
```

## Project Structure
Each service is organized into its own subfolder.
These are:
- `dependency-service`
- `latex-service`
- `pdf-service`
- `verification-service`
In addition, the folder `common` contains a common library used by all services.
