# Git Test Server

This is a Git HTTP server using nginx and git-http-backend for testing the theorem-library system. It serves a set of interconnected Lean 4 packages that follow the format specified in the architecture documentation.

## Implementation

The server uses:
- **nginx**: Web server handling HTTP requests
- **git-http-backend**: Git's standard CGI program for HTTP protocol
- **fcgiwrap**: FastCGI wrapper for running git-http-backend

This provides a production-grade Git HTTP server implementation rather than a custom Python implementation.

## Test Repositories

The server hosts three interconnected test repositories:

### 1. base-math
- **Purpose**: Foundation package with no dependencies
- **Contents**: Basic mathematical definitions
- **Dependencies**: None

### 2. algebra-theorems
- **Purpose**: Algebraic theorems building on base-math
- **Contents**: Theorems about algebraic structures
- **Dependencies**: base-math

### 3. advanced-proofs
- **Purpose**: Advanced proofs using both previous packages
- **Contents**: Complex mathematical proofs
- **Dependencies**: base-math, algebra-theorems

## Repository Structure

Each repository follows the required format:
```
<repo>/
├── lakefile.toml              # Lean 4 package configuration
├── math-dependencies.json      # Human-level mathematical dependencies
├── latex-source/
│   └── main.tex               # Human-readable proof document
└── *.lean                     # Lean 4 source files
```

## API Endpoints

### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "repositories": 3
}
```

### `GET /repositories`
List all available repositories.

**Response:**
```json
{
  "repositories": [
    {
      "name": "base-math",
      "url": "http://git-server:8000/base-math"
    },
    {
      "name": "algebra-theorems",
      "url": "http://git-server:8000/algebra-theorems"
    },
    {
      "name": "advanced-proofs",
      "url": "http://git-server:8000/advanced-proofs"
    }
  ]
}
```

### Git Protocol Endpoints

The server implements the standard Git HTTP protocol via git-http-backend, supporting:
- `GET /{repo_name}/info/refs?service=git-upload-pack` - Smart HTTP protocol advertisement
- `POST /{repo_name}/git-upload-pack` - For cloning/fetching
- `GET /{repo_name}/HEAD` - Repository HEAD file
- `GET /{repo_name}/objects/{hash}` - Git objects (pack files, loose objects)

This implementation fully supports standard `git clone` operations.

## Usage in Tests

The git-server is automatically started as part of the test suite. Tests can clone repositories directly using standard git commands:

```python
def test_example():
    repo_url = "http://git-server:8000/base-math"
    subprocess.run(["git", "clone", repo_url], check=True)
    # Use the cloned repository in tests...
```

## How Commit Hashes Are Generated

During Docker image build:
1. Repositories are copied to `/git-repos/`
2. Each repository is git-initialized in dependency order
3. Commit hashes from base repositories are substituted into dependent repositories
4. All repositories are committed with their final state
5. Git server info is updated for HTTP access

This ensures that the commit hashes in `lakefile.toml` and `math-dependencies.json` match the actual commits that can be cloned from the git server.
