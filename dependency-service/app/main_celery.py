from common.logging_config import configure_logging, configure_logging_celery
from common.config import config
import common.api.neo4j
import celery
import celery.utils.log
import os
import tempfile
import subprocess
import json
from pathlib import Path
import tomli
import model

configure_logging()

celery_app = celery.Celery("dependency_celery", broker="amqp://rabbitmq//")

configure_logging_celery(celery_app)

logger = celery.utils.log.get_task_logger("dependency_celery")

# Neo4j connection parameters
NEO4J_USER = os.getenv("NEO4J_USER", default="neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", default="")
NEO4J_HOST = config.neo4j.host
NEO4J_BOLT_PORT = config.neo4j.bolt_port
NEO4J_URI = f"bolt://{NEO4J_HOST}:{NEO4J_BOLT_PORT}"


def parse_dependencies_from_repo(repo_path: Path, repo_url: str, commit: str) -> dict:
    """
    Parse dependencies from math-dependencies.json and validate against lakefile.toml for Lean 4 packages.
    Ensures all math dependencies have exact git commits specified in lakefile.toml.
    Raises exceptions if validation fails.
    """
    dependencies = []
    validation_errors = []

    # Parse lakefile.toml to get lakefile dependencies
    lakefile = repo_path / "lakefile.toml"
    lakefile_deps = {}
    
    with open(lakefile, "rb") as f:
        lake_data = tomli.load(f)
        
        # Extract dependencies from lakefile.toml
        # Lean 4 lakefile.toml has [[require]] sections for each dependency
        lakefile_requires = lake_data.get("require", [])
        for req in lakefile_requires:
            if isinstance(req, dict):
                dep_git = req.get("git")
                dep_rev = req.get("rev")
                if dep_git and dep_rev:
                    lakefile_deps[dep_git] = dep_rev

    # Parse math-dependencies.json
    math_deps_file = repo_path / "math-dependencies.json"
    with open(math_deps_file, "r") as f:
        dependency_list = json.load(f)
        
        for dep in dependency_list:
            dep_git = dep.get("git")
            dep_commit = dep.get("commit")
            
            # Validate required fields
            if not dep_git:
                validation_errors.append("Dependency missing 'git' field")
                continue
            
            if not dep_commit:
                validation_errors.append(f"Dependency '{dep_git}' missing 'commit' field")
                continue
            
            # Validate dependency exists in lakefile.toml with exact commit
            if dep_git not in lakefile_deps:
                validation_errors.append(
                    f"Dependency '{dep_git}' in math-dependencies.json not found in lakefile.toml [[require]] sections"
                )
                continue
            
            lakefile_rev = lakefile_deps[dep_git]
            
            # Check commit/rev matches exactly
            if lakefile_rev != dep_commit:
                validation_errors.append(
                    f"Dependency '{dep_git}': commit mismatch - "
                    f"math-dependencies.json has '{dep_commit}', lakefile.toml has '{lakefile_rev}'"
                )
                continue
            
            # All validations passed
            dependencies.append({
                "git": dep_git,
                "commit": dep_commit
            })

    if validation_errors:
        error_msg = f"Validation failed for {repo_url}@{commit}: {'; '.join(validation_errors)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    return {
        "repo_url": repo_url,
        "commit": commit,
        "dependencies": dependencies
    }


@celery_app.task(queue='dependency')
def clone_and_index_repository(repo_url: str, commit: str) -> dict:
    """Clone a repository at a specific commit and index its dependencies in Neo4j."""
    task_id = celery.current_task.request.id
    logger.info(f"Task {task_id}: Cloning repository {repo_url} at commit {commit}")

    from neo4j import GraphDatabase

    driver = None
    result = {
        "status": "failed",
        "message": "",
        "repo_url": repo_url,
        "commit": commit,
        "dependencies_count": 0,
    }

    try:
        # Create a temporary directory for cloning
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "repo"

            # Clone the repository
            logger.info(f"Cloning into {repo_path}")
            clone_result = subprocess.run(
                [
                    "git",
                    "clone",
                    repo_url,
                    str(repo_path),
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if clone_result.returncode != 0:
                error_msg = f"Failed to clone repository: {clone_result.stderr}"
                logger.error(error_msg)
                result["message"] = error_msg
                return result

            # Checkout the specific commit
            logger.info(f"Checking out commit {commit}")
            checkout_result = subprocess.run(
                ["git", "checkout", commit],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if checkout_result.returncode != 0:
                error_msg = f"Failed to checkout commit: {checkout_result.stderr}"
                logger.error(error_msg)
                result["message"] = error_msg
                return result

            logger.info(f"Successfully checked out commit")

            # Parse dependencies (will raise ValueError if validation fails)
            dep_info = parse_dependencies_from_repo(repo_path, repo_url, commit)
            dependencies = dep_info["dependencies"]

            logger.info(
                f"Found project {repo_url}@{commit} with {len(dependencies)} dependencies"
            )

            # Connect to Neo4j and store the data
            driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

            with driver.session() as session:
                # Create or merge the project node (identified by repo_url + commit)
                session.run(
                    """
                    MERGE (p:Project {repo_url: $repo_url, commit: $commit})
                    SET p.last_indexed = datetime()
                    """,
                    repo_url=repo_url,
                    commit=commit,
                )

                # Create dependency nodes and relationships
                for dep in dependencies:
                    dep_git = dep.get("git")
                    dep_commit = dep.get("commit")

                    session.run(
                        """
                        MERGE (d:Project {repo_url: $dep_repo, commit: $dep_commit})
                        WITH d
                        MATCH (p:Project {repo_url: $source_repo, commit: $source_commit})
                        MERGE (p)-[r:DEPENDS_ON]->(d)
                        """,
                        dep_repo=dep_git,
                        dep_commit=dep_commit,
                        source_repo=repo_url,
                        source_commit=commit,
                    )

                logger.info(f"Successfully indexed project {repo_url}@{commit} in Neo4j")

            result = {
                "status": "success",
                "message": f"Successfully indexed {repo_url}@{commit} with {len(dependencies)} dependencies",
                "repo_url": repo_url,
                "commit": commit,
                "dependencies_count": len(dependencies),
            }

    except subprocess.TimeoutExpired:
        result["message"] = "Repository clone timed out after 5 minutes"
        logger.error(result["message"])
    except Exception as e:
        result["message"] = f"Error processing repository: {str(e)}"
        logger.error(result["message"], exc_info=True)
    finally:
        if driver:
            driver.close()

    return result
