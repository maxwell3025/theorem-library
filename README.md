# Theorem Library

This system provides a library for sharing and referencing formally verified mathematical proofs written in Lean 4. It allows mathematicians to publish both human-readable PDF papers and machine-verifiable proof packages, tracking dependencies between mathematical results. The system automatically verifies Lean 4 proofs, compiles LaTeX documents into PDFs, and validates dependency consistency across theorem packages. Users interact via a REST API to upload proofs from Git repositories, query compiled papers and metadata, and analyze dependency graphs. The architecture uses Docker Compose to orchestrate multiple microservices including dependency management, verification, LaTeX compilation, and PDF serving, backed by Neo4j and RabbitMQ. 

## Requirements
You must have Docker, Docker Compose, and Python (tested for Python 3.11.4).
You should also be running this in a Unix-like environment, which Docker requires.

In particular, you should have the Docker Compose plugin, which allows you to run `docker compose` instead of `docker-compose`.

As an optional dependency
## How to run
Create a virtual Python environment in `./venv` and activate it
```bash
python3 -m venv venv
. venv/bin/activate
```

Then, install all of the dev requirements
```bash
pip install -r requirements-dev.txt
```

Then, populate `.env` according to `.env.example` (directly copying should work for testing, but set secure passwords in prod).

Run the start script, which generates `docker-compose.yml` and runs Docker Compose.
```bash
./start.sh >/dev/null 2>&1 &
```

To test the commands, first query `git/repositories` to get a list of urls and commits.
```bash
curl http://localhost/git/repositories | jq
```

Make sure that the output includes the following repositories
```json
{
  "repositories": [
    {
      "name": "advanced-proofs",
      "url": "http://git-server:8000/advanced-proofs",
      "commit": "9c4a2f3ad74c41cddc0697cdd11e6774df7fc801"
    },
    {
      "name": "algebra-theorems",
      "url": "http://git-server:8000/algebra-theorems",
      "commit": "07515b8535b53ba1710d4ecaae13bdef1a2ba57c"
    },
    {
      "name": "base-math",
      "url": "http://git-server:8000/base-math",
      "commit": "a6f3851e8058a375451a17cd475e968ac1c2024f"
    }
  ]
}
```
The commit hashes should be the same, but if they differ, modify the commit hashes in the test commands to match your output.

Now, we can test the commands.

Post a project:
```bash
curl http://localhost/dependency-service/projects -X POST -d '{"repo_url":"http://git-server:8000/advanced-proofs","commit":"9c4a2f3ad74c41cddc0697cdd11e6774df7fc801"}' -H "Content-Type: application/json" | jq
```
We expect this to succeed, since the repo shouldn't be indexed yet
```json
{
  "task_id": "333b1ab9-1a34-49cb-9e3c-57ce49473a3a",
  "status": "queued"
}
```
This will download and compile both the formal proof and the paper in the project.

Get the info for that project:
```bash
curl http://localhost/dependency-service/projects -X GET -d '{"repo_url":"http://git-server:8000/advanced-proofs","commit":"9c4a2f3ad74c41cddc0697cdd11e6774df7fc801"}' -H "Content-Type: application/json" | jq
```
This should return a dictionary of statuses and a url fragment for the paper download
```json
{
  "repo_url": "http://git-server:8000/advanced-proofs",
  "commit": "9c4a2f3ad74c41cddc0697cdd11e6774df7fc801",
  "has_valid_dependencies": "valid",
  "has_valid_proof": "valid",
  "has_valid_paper": "valid",
  "paper_url": "pdf-service/aHR0cDovL2dpdC1zZXJ2ZXI6ODAwMC9hZHZhbmNlZC1wcm9vZnM=/9c4a2f3ad74c41cddc0697cdd11e6774df7fc801/main.pdf"
}
```

Based on the previous `paper_url`, download the compiled paper
```bash
wget http://localhost/pdf-service/aHR0cDovL2dpdC1zZXJ2ZXI6ODAwMC9hZHZhbmNlZC1wcm9vZnM=/9c4a2f3ad74c41cddc0697cdd11e6774df7fc801/main.pdf
```
`./main.pdf` should now have the paper.

Get a list of transitive dependencies for the project:
```bash
curl http://localhost/dependency-service/projects/dependencies -X GET -d '{"repo_url":"http://git-server:8000/advanced-proofs","commit":"9c4a2f3ad74c41cddc0697cdd11e6774df7fc801"}' -H "Content-Type: application/json" | jq
```
This should list 3 projects.

List all projects
```bash
curl http://localhost/dependency-service/projects/all -X GET | jq
```
This should list 3 projects.

Delete the project:
```bash
curl http://localhost/dependency-service/projects -X DELETE -d '{"repo_url":"http://git-server:8000/advanced-proofs","commit":"9c4a2f3ad74c41cddc0697cdd11e6774df7fc801"}' -H "Content-Type: application/json" | jq
```
This should succeed.

List all projects
```bash
curl http://localhost/dependency-service/projects/all -X GET | jq
```
This should now list 2 projects, since we deleted one.

**Note:** There are tests in `test`, but these are outdated and may not succeed.