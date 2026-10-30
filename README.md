# Local Ollama Chat

A minimal Flask web app for chatting with a local `qwen3:1.7b` Ollama model. Conversation history remains in the browser and is sent with every request; the browser never calls Ollama directly.

You can attach PDF, DOCX, TXT, and Markdown documents. Their extracted text is kept only in the running Flask process and provided to the model as context with each question. This initial demo accepts files up to 10 MB and sends up to 24,000 extracted characters across the selected documents.

When **Web search** is selected, the model can call Ollama's web-search API. Set your Ollama API key before starting the app:

```powershell
$env:OLLAMA_API_KEY = "your-key"
python app.py
```

The key stays on the Flask server; it is never sent to the browser.

## Setup

1. Make sure Ollama is installed and running.
2. Download the requested model if needed:

   ```powershell
   ollama pull qwen3:1.7b
   ```

3. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

## Run

Start the Flask app:

```powershell
python app.py
```

Then open http://127.0.0.1:5000 in a browser. Flask is deliberately bound only to `127.0.0.1`.

If the interface reports that it cannot reach Ollama, start the Ollama service (for example, `ollama serve`) and verify that `qwen3:1.7b` is available with `ollama list`.
