import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

# -----------------------------
# CONFIG
# -----------------------------
app = Flask(__name__)
CORS(app)

# Load your Google API key from environment variable
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# Load JSON prompt
PROMPT_FILE = "prompt.json"
if os.path.exists(PROMPT_FILE):
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
else:
    SYSTEM_PROMPT = "You are a helpful legal assistant."

# -----------------------------
# MODEL SETUP
# -----------------------------
model = genai.GenerativeModel(
    model_name="gemini-2.5-pro",
    system_instruction=SYSTEM_PROMPT
)

# -----------------------------
# ROUTES
# -----------------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "Legal AI Chatbot running (no calendar)."})


@app.route("/chat", methods=["POST"])
def chat():
    """
    Handles:
    - text messages
    - optional audio base64
    """
    try:
        data = request.json

        user_text = data.get("text", "")
        audio_base64 = data.get("audio", None)

        # Build input
        parts = []
        if user_text:
            parts.append({"text": user_text})

        if audio_base64:
            parts.append({
                "inline_data": {
                    "mime_type": "audio/webm",
                    "data": audio_base64
                }
            })

        # Run model
        response = model.generate_content(parts)

        return jsonify({
            "response": response.text
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
