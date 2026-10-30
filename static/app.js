const form = document.querySelector("#chat-form");
const input = document.querySelector("#prompt");
const messagesElement = document.querySelector("#messages");
const sendButton = document.querySelector("#send-button");
const documentInput = document.querySelector("#document-input");
const documentList = document.querySelector("#document-list");
const uploadForm = document.querySelector("#upload-form");
const uploadButton = document.querySelector("#upload-button");
const fileSelection = document.querySelector("#file-selection");
const uploadStatus = document.querySelector("#upload-status");
const documentCount = document.querySelector("#document-count");
const chatDocumentSummary = document.querySelector("#chat-document-summary");
const webSearch = document.querySelector("#web-search");
const history = [];
let documents = [];

function addMessage(role, content, isError = false) {
  const message = document.createElement("div");
  message.className = `message ${role}${isError ? " error" : ""}`;
  appendLinkifiedText(message, content);
  messagesElement.appendChild(message);
  messagesElement.scrollTop = messagesElement.scrollHeight;
  return message;
}

function appendLinkifiedText(element, content) {
  const urlPattern = /https?:\/\/[^\s<>"]+/g;
  let lastIndex = 0;

  for (const match of content.matchAll(urlPattern)) {
    element.append(document.createTextNode(content.slice(lastIndex, match.index)));
    const link = document.createElement("a");
    link.href = match[0];
    link.textContent = match[0];
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    element.append(link);
    lastIndex = match.index + match[0].length;
  }

  element.append(document.createTextNode(content.slice(lastIndex)));
}

function setSending(sending) {
  input.disabled = sending;
  sendButton.disabled = sending;
  webSearch.disabled = sending;
  sendButton.textContent = sending ? "Sending…" : "Send";
}

function renderDocuments() {
  documentList.replaceChildren();
  documentCount.textContent = `${documents.length} file${documents.length === 1 ? "" : "s"}`;
  chatDocumentSummary.textContent = documents.length
    ? `${documents.length} document${documents.length === 1 ? "" : "s"} available to chat`
    : "No documents uploaded yet";

  for (const uploadedDocument of documents) {
    const item = document.createElement("div");
    item.className = "document-item";
    const details = document.createElement("div");
    const name = document.createElement("a");
    name.className = "document-link";
    name.href = `/api/documents/${encodeURIComponent(uploadedDocument.id)}/file`;
    name.target = "_blank";
    name.rel = "noopener noreferrer";
    name.textContent = uploadedDocument.name;
    const metadata = document.createElement("span");
    metadata.textContent = `${uploadedDocument.characters.toLocaleString()} characters extracted`;
    details.append(name, metadata);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "delete-button";
    remove.textContent = "Delete";
    remove.addEventListener("click", () => deleteDocument(uploadedDocument.id));
    item.append(details, remove);
    documentList.append(item);
  }
}

async function loadDocuments() {
  const response = await fetch("/api/documents");
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Could not load documents.");
  documents = data.documents;
  renderDocuments();
}

async function deleteDocument(documentId) {
  try {
    const response = await fetch(`/api/documents/${documentId}`, { method: "DELETE" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not delete the document.");
    documents = documents.filter((document) => document.id !== documentId);
    renderDocuments();
  } catch (error) {
    addMessage("assistant", error.message || "Document deletion failed.", true);
  }
}

documentInput.addEventListener("change", () => {
  const count = documentInput.files.length;
  fileSelection.textContent = count ? `${count} file${count === 1 ? "" : "s"} selected` : "No files selected";
  uploadStatus.textContent = "";
  uploadStatus.classList.remove("error-text");
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const files = [...documentInput.files];
  if (!files.length) return;

  documentInput.disabled = true;
  uploadButton.disabled = true;
  uploadButton.textContent = "Uploading…";
  uploadStatus.textContent = "";
  uploadStatus.classList.remove("error-text");
  try {
    for (const file of files) {
      const body = new FormData();
      body.append("document", file);
      const response = await fetch("/api/documents", { method: "POST", body });
      const data = await response.json();
      if (!response.ok) throw new Error(`${file.name}: ${data.error || "Upload failed."}`);
      documents.push(data);
    }
    renderDocuments();
    uploadStatus.textContent = "Upload complete.";
  } catch (error) {
    uploadStatus.textContent = error.message || "Document upload failed.";
    uploadStatus.classList.add("error-text");
  } finally {
    documentInput.value = "";
    fileSelection.textContent = "No files selected";
    documentInput.disabled = false;
    uploadButton.disabled = false;
    uploadButton.textContent = "Upload";
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const content = input.value.trim();
  if (!content) return;

  const userMessage = { role: "user", content };
  history.push(userMessage);
  addMessage("user", content);
  input.value = "";
  setSending(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: history,
        document_ids: documents.map((document) => document.id),
        web_search: webSearch.checked,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to get a response from Ollama.");

    history.push(data.message);
    addMessage("assistant", data.message.content);
  } catch (error) {
    history.pop();
    addMessage("assistant", error.message || "Something went wrong.", true);
  } finally {
    setSending(false);
    input.focus();
  }
});

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const showDocuments = tab.dataset.tab === "documents";
    document.querySelector("#chat-panel").classList.toggle("hidden", showDocuments);
    document.querySelector("#documents-panel").classList.toggle("hidden", !showDocuments);
    document.querySelectorAll(".tab").forEach((item) => {
      const active = item === tab;
      item.classList.toggle("active", active);
      item.setAttribute("aria-selected", String(active));
    });
  });
});

loadDocuments().catch((error) => addMessage("assistant", error.message, true));
