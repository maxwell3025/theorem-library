# Git Server Service for Testing

## Overview
A git HTTP server service has been added to the theorem-library testing infrastructure. This service provides a set of interconnected Lean 4 packages that can be used for integration testing of the dependency service and other components.

## What Was Added

### 1. Git Server Service (`git-server/`)
- **Dockerfile**: Builds a container with git and Python/FastAPI
- **app/main.py**: FastAPI server implementing Git HTTP protocol
- **requirements.txt**: Python dependencies (FastAPI, uvicorn, httpx)
- **README.md**: Documentation of the git-server service
- **repos/**: Test repository templates

### 2. Test Repositories
Three interconnected Lean 4 packages following the project format:

#### base-math
- No dependencies
- Contains basic mathematical definitions
- Includes `lakefile.toml`, `math-dependencies.json` (empty array), `latex-source/main.tex`, and `.lean` files

#### algebra-theorems
- Depends on: base-math
- Contains algebraic theorems
- Demonstrates single dependency

#### advanced-proofs
- Depends on: base-math, algebra-theorems
- Contains advanced proofs
- Demonstrates multiple dependencies and transitive relationships

### 3. Docker Compose Integration
- Added `git-server` service to `common/compose.py`
- Service runs on port 8005
- Includes healthcheck endpoint
- Available on the `theorem-library` network

### 4. Test Infrastructure Updates

#### conftest.py
- Added `git_server_url` fixture: Returns the git-server base URL
- Added `git_repositories` fixture: Fetches repository info from git-server API
- Updated SERVICES dict to include git-server

#### test_dependency_service.py
- Updated `test_add_project` to use `git_repositories` fixture
- Added `test_add_interconnected_packages`: Tests adding packages with dependencies
- Added `test_verify_dependency_chain`: Verifies dependency relationships

#### test_git_server.py (new)
- Tests git-server health check
- Tests repository listing
- Tests git_repositories fixture

## How It Works

### Repository Initialization
During Docker build:
1. Copy repository templates to `/git-repos/`
2. Initialize base-math and commit (gets commit hash A)
3. Replace placeholder `COMMIT_BASE_MATH` in algebra-theorems with hash A
4. Initialize algebra-theorems and commit (gets commit hash B)
5. Replace placeholders in advanced-proofs with hashes A and B
6. Initialize advanced-proofs and commit
7. Run `git update-server-info` for HTTP serving

### Git HTTP Protocol
The server implements:
- Smart HTTP protocol (preferred by modern git clients)
- Dumb HTTP protocol (fallback)
- Supports `git clone`, `git fetch` operations

### Test Usage
Tests can use the fixtures to get repository information:

```python
def test_example(git_repositories: dict):
    base_math = git_repositories["base-math"]
    # base_math = {
    #   "name": "base-math",
    #   "url": "http://git-server:8000/base-math",
    #   "commit": "abc123def456..."
    # }
```

## Benefits

1. **Reproducible Testing**: Tests use local repositories with known content
2. **No External Dependencies**: Don't rely on GitHub or other external services
3. **Realistic Test Data**: Packages follow the exact format required by the system
4. **Dependency Testing**: Can test the full dependency resolution pipeline
5. **Fast**: No network latency from external git hosts
6. **Isolated**: Tests won't break if external repositories change

## Running Tests

The git-server is automatically included when running the test suite:

```bash
pytest test/test_git_server.py          # Test git-server itself
pytest test/test_dependency_service.py   # Tests now use git-server
```

The `docker_compose` fixture in conftest.py handles starting the git-server along with other services.
