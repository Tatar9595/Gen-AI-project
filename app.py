from __future__ import annotations

import os
from io import BytesIO
from uuid import uuid4

import requests
from flask import Flask, jsonify, render_template, request, send_file
from docx import Document
from pypdf import PdfReader


app = Flask(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_WEB_SEARCH_URL = "https://ollama.com/api/web_search"
MODEL = "qwen3:1.7b"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_CONTEXT_CHARS = 24_000
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}
uploaded_documents: dict[str, dict[str, object]] = {}
WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current or external information.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "The search query."}},
            "required": ["query"],
        },
    },
}


@app.get("/")
def index():
    return render_template("index.html", model=MODEL)


def extract_text(filename: str, file_bytes: bytes) -> str:
    extension = filename.rsplit(".", 1)[-1].lower()
    if extension in {"txt", "md"}:
        return file_bytes.decode("utf-8", errors="replace")
    if extension == "pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(file_bytes)).pages)
    if extension == "docx":
        document = Document(BytesIO(file_bytes))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    raise ValueError("Unsupported file type.")


def run_web_search(query: str) -> str:
    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        raise RuntimeError("Web search is not configured. Set OLLAMA_API_KEY and restart the app.")

    response = requests.post(
        OLLAMA_WEB_SEARCH_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"query": query},
        timeout=30,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        return "No web results were found."

    return "\n\n".join(
        f"Title: {result.get('title', 'Untitled')}\nURL: {result.get('url', '')}\n"
        f"Content: {result.get('content', '')[:1500]}"
        for result in results[:5]
    )


@app.route("/api/documents", methods=["GET", "POST"])
def upload_document():
    if request.method == "GET":
        return jsonify(documents=[
            {"id": document_id, "name": document["name"], "characters": len(document["text"])}
            for document_id, document in uploaded_documents.items()
        ])

    upload = request.files.get("document")
    if upload is None or not upload.filename:
        return jsonify(error="Choose a document to upload."), 400

    filename = upload.filename
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        return jsonify(error="Only PDF, DOCX, TXT, and Markdown files are supported."), 400

    file_bytes = upload.read(MAX_UPLOAD_BYTES + 1)
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        return jsonify(error="Documents must be 10 MB or smaller."), 413

    try:
        text = extract_text(filename, file_bytes).strip()
    except Exception:
        return jsonify(error="The document could not be read. Try a valid, non-password-protected file."), 400

    if not text:
        return jsonify(error="No readable text was found in this document."), 400

    document_id = str(uuid4())
    uploaded_documents[document_id] = {
        "name": filename,
        "text": text,
        "file_bytes": file_bytes,
        "mimetype": upload.mimetype or "application/octet-stream",
    }
    return jsonify(id=document_id, name=filename, characters=len(text))


@app.delete("/api/documents/<document_id>")
def delete_document(document_id: str):
    if document_id not in uploaded_documents:
        return jsonify(error="This document is no longer available."), 404
    del uploaded_documents[document_id]
    return jsonify(success=True)


@app.get("/api/documents/<document_id>/file")
def open_document(document_id: str):
    document = uploaded_documents.get(document_id)
    if document is None or "file_bytes" not in document:
        return jsonify(error="This document is no longer available. Upload it again."), 404

    return send_file(
        BytesIO(document["file_bytes"]),
        mimetype=document["mimetype"],
        download_name=document["name"],
        as_attachment=False,
    )


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    messages = data.get("messages")

    if not isinstance(messages, list) or not messages:
        return jsonify(error="Please provide at least one chat message."), 400

    valid_messages = []
    for message in messages:
        if not isinstance(message, dict):
            return jsonify(error="Each message must be an object."), 400
        role = message.get("role")
        content = message.get("content")
        if role not in {"user", "assistant", "system"} or not isinstance(content, str):
            return jsonify(error="Messages need a valid role and text content."), 400
        valid_messages.append({"role": role, "content": content})

    document_ids = data.get("document_ids", [])
    if not isinstance(document_ids, list) or not all(isinstance(document_id, str) for document_id in document_ids):
        return jsonify(error="Document IDs must be a list."), 400

    selected_documents = [uploaded_documents[document_id] for document_id in document_ids if document_id in uploaded_documents]
    if document_ids and len(selected_documents) != len(document_ids):
        return jsonify(error="One or more uploaded documents are no longer available. Upload them again."), 400

    if selected_documents:
        document_context = "\n\n".join(
            f"--- Document: {document['name']} ---\n{document['text']}" for document in selected_documents
        )[:MAX_CONTEXT_CHARS]
        valid_messages.insert(0, {
            "role": "system",
            "content": (
                "Use the uploaded documents below as context when relevant. "
                "If the answer is not in them, say so clearly.\n\n" + document_context
            ),
        })

    use_web_search = data.get("web_search", False)
    if not isinstance(use_web_search, bool):
        return jsonify(error="Web search must be enabled or disabled."), 400
    if use_web_search and not os.environ.get("OLLAMA_API_KEY"):
        return jsonify(error="Web search is not configured on this server."), 503

    try:
        for _ in range(4):
            request_payload = {"model": MODEL, "messages": valid_messages, "stream": False}
            if use_web_search:
                request_payload["tools"] = [WEB_SEARCH_TOOL]
            response = requests.post(OLLAMA_URL, json=request_payload, timeout=120)
            response.raise_for_status()
            payload = response.json()
            model_message = payload.get("message", {})
            tool_calls = model_message.get("tool_calls", [])
            if not tool_calls:
                break

            valid_messages.append({
                "role": "assistant",
                "content": model_message.get("content", ""),
                "tool_calls": tool_calls,
            })
            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                if function.get("name") != "web_search":
                    continue
                query = function.get("arguments", {}).get("query")
                if not isinstance(query, str) or not query.strip():
                    continue
                valid_messages.append({
                    "role": "tool",
                    "tool_name": "web_search",
                    "content": run_web_search(query.strip()),
                })
        else:
            return jsonify(error="The model made too many web-search requests. Please try a narrower question."), 502
    except requests.ConnectionError:
        return jsonify(error="Cannot reach Ollama. Start Ollama and make sure it is listening on port 11434."), 503
    except requests.Timeout:
        return jsonify(error="Ollama took too long to respond. Please try again."), 504
    except requests.RequestException as exc:
        details = exc.response.text if exc.response is not None else str(exc)
        return jsonify(error=f"Ollama returned an error: {details}"), 502
    except ValueError:
        return jsonify(error="Ollama returned an invalid response."), 502

    answer = payload.get("message", {}).get("content")
    if not isinstance(answer, str):
        return jsonify(error="Ollama returned a response without an assistant message."), 502

    return jsonify(message={"role": "assistant", "content": answer})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=True)
