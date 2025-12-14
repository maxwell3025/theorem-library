import pytest
import httpx
import logging
from formatutils import pretty_print_response
import base64

logger = logging.getLogger(__name__)


def test_health_check(http_client: httpx.Client, pdf_service_url: str):
    """Test that the PDF service health check endpoint returns healthy status."""
    response = http_client.get(url=f"{pdf_service_url}/health")
    pretty_print_response(response, logger)
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    data = response.json()
    assert data["status"] == "healthy"


def test_pdf_crud_operations(http_client: httpx.Client, pdf_service_url: str):
    """Test all CRUD operations on a single PDF."""
    git_url = "https://github.com/test/theorem-repo.git"
    commit_hash = "abc123def456789"
    
    # CREATE: Create a new PDF
    pdf_content_original = b"%PDF-1.4\n%Original PDF content\n%%EOF"
    pdf_data_b64_original = base64.b64encode(pdf_content_original).decode('utf-8')
    
    create_request = {
        "git_url": git_url,
        "commit_hash": commit_hash,
        "pdf_data": pdf_data_b64_original,
    }
    
    create_response = http_client.post(
        url=f"{pdf_service_url}/pdf",
        json=create_request,
    )
    pretty_print_response(create_response, logger)
    assert create_response.status_code == 201
    create_data = create_response.json()
    assert create_data["git_url"] == git_url
    assert create_data["commit_hash"] == commit_hash
    assert create_data["size_bytes"] == len(pdf_content_original)
    
    # READ: Retrieve the PDF
    read_response = http_client.get(
        url=f"{pdf_service_url}/pdf",
        params={"git_url": git_url, "commit_hash": commit_hash},
    )
    pretty_print_response(read_response, logger)
    assert read_response.status_code == 200
    read_data = read_response.json()
    assert read_data["git_url"] == git_url
    assert read_data["commit_hash"] == commit_hash
    assert read_data["size_bytes"] == len(pdf_content_original)
    retrieved_content = base64.b64decode(read_data["pdf_data"])
    assert retrieved_content == pdf_content_original
    
    # UPDATE: Modify the PDF content
    pdf_content_updated = b"%PDF-1.4\n%Updated PDF content with more data\n%%EOF"
    pdf_data_b64_updated = base64.b64encode(pdf_content_updated).decode('utf-8')
    
    update_request = {
        "git_url": git_url,
        "commit_hash": commit_hash,
        "pdf_data": pdf_data_b64_updated,
    }
    
    update_response = http_client.put(
        url=f"{pdf_service_url}/pdf",
        json=update_request,
    )
    pretty_print_response(update_response, logger)
    assert update_response.status_code == 200
    update_data = update_response.json()
    assert update_data["git_url"] == git_url
    assert update_data["commit_hash"] == commit_hash
    assert update_data["size_bytes"] == len(pdf_content_updated)
    
    # READ again: Verify the update
    read_after_update_response = http_client.get(
        url=f"{pdf_service_url}/pdf",
        params={"git_url": git_url, "commit_hash": commit_hash},
    )
    pretty_print_response(read_after_update_response, logger)
    assert read_after_update_response.status_code == 200
    read_after_update_data = read_after_update_response.json()
    retrieved_updated_content = base64.b64decode(read_after_update_data["pdf_data"])
    assert retrieved_updated_content == pdf_content_updated
    assert retrieved_updated_content != pdf_content_original
    
    # DELETE: Remove the PDF
    delete_response = http_client.delete(
        url=f"{pdf_service_url}/pdf",
        params={"git_url": git_url, "commit_hash": commit_hash},
    )
    pretty_print_response(delete_response, logger)
    assert delete_response.status_code == 200
    delete_data = delete_response.json()
    assert delete_data["git_url"] == git_url
    assert delete_data["commit_hash"] == commit_hash
    
    # READ after DELETE: Verify it's gone
    read_after_delete_response = http_client.get(
        url=f"{pdf_service_url}/pdf",
        params={"git_url": git_url, "commit_hash": commit_hash},
    )
    pretty_print_response(read_after_delete_response, logger)
    assert read_after_delete_response.status_code == 404
