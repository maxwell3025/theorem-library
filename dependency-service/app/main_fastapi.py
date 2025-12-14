import fastapi
import logging
from common.dependency_service import public_model
import common.model
import common.api.neo4j
import common.middleware
from common.logging_config import configure_logging, configure_logging_uvicorn
import typing
import uvicorn
import os
from neo4j import GraphDatabase
import neomodel
from common.config import config
from common.dependency_service import schema
import main_celery

configure_logging()

logger = logging.getLogger("dependency-service")

app = fastapi.FastAPI()

app.add_middleware(common.middleware.CorrelationIdMiddleware)

# Neo4j connection parameters
NEO4J_USER = os.getenv("NEO4J_USER", default="neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", default="")
NEO4J_HOST = config.neo4j.host
NEO4J_BOLT_PORT = config.neo4j.bolt_port
NEO4J_URI = f"bolt://{NEO4J_USER}:{NEO4J_PASSWORD}@{NEO4J_HOST}:{NEO4J_BOLT_PORT}"


@app.get("/health", response_model=public_model.HealthCheckResponse)
async def health_check() -> fastapi.Response:
    # Currently, nothing can cause a service to report itself as unhealthy
    status: common.model.HealthCheckStatus = "healthy"
    status_code = 200 if status == "healthy" else 503
    # Use methods defined in /common to run health checks
    dependencies: typing.Dict[str, common.model.HealthCheckDependency] = {
        "neo4j": common.api.neo4j.check_health()
    }

    response_content = public_model.HealthCheckResponse(
        status=status,
        dependencies=dependencies,
    )

    return fastapi.Response(
        content=response_content.model_dump_json(exclude_none=True),
        status_code=status_code,
    )


@app.post("/projects", response_model=public_model.AddProjectResponse)
async def add_project(request: public_model.ProjectInfo) -> fastapi.Response:
    """Add a project by cloning its repository at a specific commit and indexing dependencies."""
    logger.info(f"Received request to add project {request.repo_url}@{request.commit}")

    # Queue the Celery task
    task = main_celery.clone_and_index_repository.delay(
        request.repo_url, request.commit
    )

    return fastapi.responses.JSONResponse(
        content=public_model.AddProjectResponse(
            task_id=task.id,
            status="queued",
        ).model_dump(),
        status_code=202,
    )


@app.post("/internal/projects", response_model=public_model.AddDependencyResponse)
async def internal_add_project(
    request: public_model.AddProjectInternalRequest,
) -> fastapi.Response:
    """Internal endpoint to add project dependencies directly to the database."""

    neomodel_config = neomodel.get_config()
    neomodel_config.database_url = NEO4J_URI

    logger.info(f"Connecting to Neo4j")
    with neomodel.db.write_transaction:
        new_project: schema.Project = schema.Project.nodes.get_or_none(
            repo_url=request.source.repo_url,
            commit=request.source.commit,
        )
        if new_project is None:
            new_project = schema.Project(
                repo_url=request.source.repo_url,
                commit=request.source.commit,
                has_valid_dependencies=request.is_valid,
            )

        dependency_nodes: list[schema.Project] = []
        subtasks = []
        for dependency in request.dependencies:
            node = schema.Project.nodes.get_or_none(
                repo_url=dependency.repo_url,
                commit=dependency.commit,
            )
            node = schema.Project(
                repo_url=dependency.repo_url,
                commit=dependency.commit,
            )
            node.save()
            if node is None:
                subtasks.append(
                    main_celery.clone_and_index_repository.delay(
                        dependency.repo_url,
                        dependency.commit,
                    )
                )
            dependency_nodes.append(node)

        new_project.save()
        for dependency_node in dependency_nodes:
            new_project.dependencies.connect(dependency_node)  # type: ignore

    return fastapi.responses.JSONResponse(
        content=public_model.AddDependencyResponse(
            success=True,
            message="Project and dependencies added successfully",
            subtask_ids=[task.id for task in subtasks],
        ).model_dump(),
        status_code=202,
    )


@app.get("/projects")
async def list_projects() -> typing.List[public_model.ProjectInfo]:
    """List all projects in the database."""
    with GraphDatabase.driver(
        NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
    ) as driver, driver.session() as session:
        result = session.run(
            """
            MATCH (p:Project)
            RETURN p.repo_url as repo_url, p.commit as commit
            ORDER BY p.repo_url, p.commit
            """
        )
        projects = [
            public_model.ProjectInfo(
                repo_url=record["repo_url"], commit=record["commit"]
            )
            for record in result
        ]
        return projects


@app.get("/projects/{repo_url:path}/{commit}/dependencies")
async def get_project_dependencies(
    repo_url: str, commit: str
) -> typing.List[public_model.DependencyInfo]:
    """Get all dependencies for a specific project."""
    logger.info(f"GET dependencies - repo_url='{repo_url}', commit='{commit}'")
    with GraphDatabase.driver(
        NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
    ) as driver, driver.session() as session:
        result = session.run(
            """
            MATCH (p:Project {repo_url: $repo_url, commit: $commit})-[:DEPENDS_ON]->(d:Project)
            RETURN p.repo_url as source_repo, p.commit as source_commit, 
                   d.repo_url as dependency_repo, d.commit as dependency_commit
            ORDER BY d.repo_url, d.commit
            """,
            repo_url=repo_url,
            commit=commit,
        )
        dependencies = [
            public_model.DependencyInfo(
                source_repo=record["source_repo"],
                source_commit=record["source_commit"],
                dependency_repo=record["dependency_repo"],
                dependency_commit=record["dependency_commit"],
            )
            for record in result
        ]
        return dependencies


if __name__ == "__main__":
    # Get uvicorn's default logging config and customize it
    log_config = uvicorn.config.LOGGING_CONFIG
    configure_logging_uvicorn(log_config)

    # Start uvicorn with custom logging config
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=log_config)
