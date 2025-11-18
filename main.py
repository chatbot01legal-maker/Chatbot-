from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os

app = Flask(__name__)
CORS(app)

# ============================
# CONFIGURAR GEMINI
# ============================
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("Por favor define GEMINI_API_KEY en las variables de entorno.")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

# ============================
# ENDPOINT DEL CHAT
# ============================
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_message = data.get("message", "").strip()

        # Mensaje de bienvenida si no hay mensaje del usuario
        if not user_message:
            welcome_text = (
                "Hola, soy Lex, tu asesor legal de AboLegal. "
                "Estoy aquí para ayudarte con tus consultas legales. "
                "¿En qué puedo ayudarte hoy?"
            )
            return jsonify({"response": welcome_text, "status": "ok"})

        # Generar respuesta con Gemini
        response = model.generate(
            prompt=user_message,
            max_output_tokens=300
        )

        return jsonify({"response": response.output_text, "status": "ok"})

    except Exception as e:
        return jsonify({"error": str(e), "status": "fail"}), 500

# ============================
# ENDPOINT DE TEST (GET)
# ============================
@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "Legal AI Chatbot running (no calendar).", "status": "ok"})

# ============================
# RUN SERVER
# ============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
