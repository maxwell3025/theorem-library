import base64
import sys
import fastapi
import logging
from common.dependency_service import public_model
import common.model
import common.api.neo4j
import common.middleware
from common.logging_config import configure_logging, configure_logging_uvicorn
from contextlib import asynccontextmanager
import typing
import uvicorn
import os
import httpx
from neo4j import GraphDatabase
from common.config import config
from common.dependency_service import schema
import neomodel
import main_celery

configure_logging()

logger = logging.getLogger("dependency-service")

# Neo4j connection parameters
NEO4J_USER: str = os.getenv("NEO4J_USER")  # type: ignore
if NEO4J_USER is None:
    raise ValueError("NEO4J_USER environment variable is not set")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD")  # type: ignore
if NEO4J_PASSWORD is None:
    raise ValueError("NEO4J_PASSWORD environment variable is not set")

NEO4J_HOST = config.neo4j.host
NEO4J_BOLT_PORT = config.neo4j.bolt_port
NEO4J_URI = f"bolt://{NEO4J_USER}:{NEO4J_PASSWORD}@{NEO4J_HOST}:{NEO4J_BOLT_PORT}"


@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    neomodel_config = neomodel.get_config()
    neomodel_config.database_url = NEO4J_URI
    neomodel.db.install_all_labels()
    logger.info("Connected to Neo4j and ensured all labels are installed.")
    yield


app = fastapi.FastAPI(lifespan=lifespan)

app.add_middleware(common.middleware.CorrelationIdMiddleware)


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

    # Ensure the project exists in the database
    with neomodel.db.write_transaction:
        new_project: schema.Project = schema.Project.nodes.get_or_none(
            repo_url=request.repo_url,
            commit=request.commit,
        )
        if new_project is None:
            new_project = schema.Project(
                repo_url=request.repo_url,
                commit=request.commit,
            )

    # Queue the Celery task for dependency indexing
    task = main_celery.clone_and_index_repository.delay(
        request.repo_url, request.commit
    )

    # Request verification service to verify the proofs
    try:
        verification_response = httpx.post(
            url="http://verification-service:8000/run",
            json={"repo_url": request.repo_url, "commit_hash": request.commit},
            timeout=30,
        )
        if verification_response.is_success:
            logger.info(
                f"Queued verification task for {request.repo_url}@{request.commit}"
            )
        else:
            logger.error(
                f"Failed to queue verification task: {verification_response.status_code}\n"
                f"{verification_response.text[:500]}"
            )
    except Exception as e:
        logger.error(f"Exception while requesting verification: {e}")

    # Request latex service to compile the paper
    try:
        latex_response = httpx.post(
            url="http://latex-service:8000/run",
            json={"repo_url": request.repo_url, "commit_hash": request.commit},
            timeout=30,
        )
        if latex_response.is_success:
            logger.info(
                f"Queued LaTeX compilation task for {request.repo_url}@{request.commit}"
            )
        else:
            logger.error(
                f"Failed to queue LaTeX compilation task: {latex_response.status_code}\n"
                f"{latex_response.text[:500]}"
            )
    except Exception as e:
        logger.error(f"Exception while requesting LaTeX compilation: {e}")

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
            )
        new_project.has_valid_dependencies = "valid" if request.is_valid else "invalid"  # type: ignore

        dependency_nodes: list[schema.Project] = []
        to_index: list[public_model.ProjectInfo] = []
        for dependency in request.dependencies:
            node = schema.Project.nodes.get_or_none(
                repo_url=dependency.repo_url,
                commit=dependency.commit,
            )
            if node is None:
                to_index.append(dependency)
                node = schema.Project(
                    repo_url=dependency.repo_url,
                    commit=dependency.commit,
                )
            node.save()
            dependency_nodes.append(node)

        new_project.save()
        for dependency_node in dependency_nodes:
            new_project.dependencies.connect(dependency_node)  # type: ignore

    for dependency in to_index:
        logger.info(
            f"Requesting indexing for dependency {dependency.repo_url}@{dependency.commit}"
        )
        await httpx.AsyncClient().post(
            url="http://dependency-service:8000/projects",
            json=public_model.ProjectInfo(
                repo_url=dependency.repo_url,
                commit=dependency.commit,
            ).model_dump(),
            timeout=30,
        )

    return fastapi.responses.JSONResponse(
        content=public_model.AddDependencyResponse(
            success=True,
            message="Project and dependencies added successfully",
        ).model_dump(),
        status_code=202,
    )


@app.post("/internal/verification_status")
async def internal_update_verification_status(
    request: public_model.UpdateStatusRequest,
) -> fastapi.Response:
    """Internal endpoint to update the verification status of a project."""
    logger.info(f"Updating verification status for {request.repo_url}@{request.commit}")

    with neomodel.db.write_transaction:
        project: schema.Project = schema.Project.nodes.get_or_none(
            repo_url=request.repo_url,
            commit=request.commit,
        )
        if project is None:
            return fastapi.responses.JSONResponse(
                content={"error": "Project not found"},
                status_code=404,
            )

        project.has_valid_proof = "valid" if request.has_valid_status else "invalid"  # type: ignore
        project.save()

    return fastapi.responses.JSONResponse(
        content={"message": "Verification status updated successfully"},
        status_code=200,
    )


@app.post("/internal/paper_status")
async def internal_update_paper_status(
    request: public_model.UpdateStatusRequest,
) -> fastapi.Response:
    """Internal endpoint to update the LaTeX compilation status of a project."""
    logger.info(
        f"Updating LaTeX compilation status for {request.repo_url}@{request.commit}"
    )

    with neomodel.db.write_transaction:
        project: schema.Project = schema.Project.nodes.get_or_none(
            repo_url=request.repo_url,
            commit=request.commit,
        )
        if project is None:
            return fastapi.responses.JSONResponse(
                content={"error": "Project not found"},
                status_code=404,
            )

        project.has_valid_paper = "valid" if request.has_valid_status else "invalid"  # type: ignore
        project.save()

    return fastapi.responses.JSONResponse(
        content={"message": "LaTeX compilation status updated successfully"},
        status_code=200,
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


@app.get("/projects/dependencies")
async def get_project_dependencies(
    project: public_model.ProjectInfo,
) -> typing.List[public_model.DependencyListResponse]:
    """Get all dependencies for a specific project."""
    logger.info(
        f"GET dependencies - repo_url='{project.repo_url}', commit='{project.commit}'"
    )
    with neomodel.db.read_transaction:
        rows, headers = neomodel.db.cypher_query(
            """
            MATCH (p:Project {repo_url: $repo_url, commit: $commit})-[:DEPENDS_ON*0..]->(d:Project)
            RETURN DISTINCT properties(d) as dependencies
            """,
            params=project.model_dump(),
        )
        logger.info(f"Query result: {rows}")
        dependencies = [
            public_model.DependencyListResponse(
                repo_url=result[0]["repo_url"],
                commit=result[0]["commit"],
                has_valid_dependencies=result[0]["has_valid_dependencies"],
                has_valid_proof=result[0]["has_valid_proof"],
                has_valid_paper=result[0]["has_valid_paper"],
                paper_url=f"pdf-service/{base64.urlsafe_b64encode(result[0]['repo_url'].encode()).decode()}/{result[0]['commit']}/main.pdf",
            )
            for result in rows
        ]
        return dependencies


if __name__ == "__main__":
    # Get uvicorn's default logging config and customize it
    log_config = uvicorn.config.LOGGING_CONFIG
    configure_logging_uvicorn(log_config)

    # Start uvicorn with custom logging config
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=log_config)
