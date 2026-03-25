def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Upload" in response.data or b"Commercial" in response.data


def test_upload_valid_document_redirects_to_result(client, sample_upload):
    response = client.post(
        "/upload",
        data=sample_upload,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Document Processed" in response.data
    assert b"Test summary" in response.data


def test_upload_invalid_extension_shows_error(client):
    data = {
        "document": (b"fake content", "bad.exe")
    }
    response = client.post(
        "/upload",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Unsupported file type" in response.data


def test_chat_route_loads_after_upload(client, sample_upload):
    upload_response = client.post(
        "/upload",
        data=sample_upload,
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert upload_response.status_code == 302

    result_location = upload_response.headers["Location"]
    doc_id = int(result_location.rstrip("/").split("/")[-1])

    response = client.get(f"/chat/{doc_id}")
    assert response.status_code == 200
    assert b"Ask Questions About" in response.data


def test_ask_route_returns_json_answer(client, sample_upload):
    upload_response = client.post(
        "/upload",
        data=sample_upload,
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    doc_id = int(upload_response.headers["Location"].rstrip("/").split("/")[-1])

    response = client.post(f"/ask/{doc_id}", data={"question": "What is the deadline?"})
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"] is True
    assert json_data["answer"] == "Test chatbot answer"


def test_report_route_loads(client, sample_upload):
    upload_response = client.post(
        "/upload",
        data=sample_upload,
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    doc_id = int(upload_response.headers["Location"].rstrip("/").split("/")[-1])

    response = client.get(f"/report/{doc_id}")
    assert response.status_code == 200
    assert b"Structured Report" in response.data


def test_pdf_download_route_returns_pdf(client, sample_upload):
    upload_response = client.post(
        "/upload",
        data=sample_upload,
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    doc_id = int(upload_response.headers["Location"].rstrip("/").split("/")[-1])

    response = client.get(f"/report/{doc_id}/download")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
