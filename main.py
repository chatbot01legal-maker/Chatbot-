from flask import Flask, request, jsonify, render_template_string, session
from flask_cors import CORS
import os
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# Necesario para sesiones
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Por favor define GEMINI_API_KEY en las variables de entorno.")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-pro")

CHAT_HTML = """ 
<!-- Mantén el HTML igual que antes -->
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(CHAT_HTML)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_msg = data.get("message", "")

    if not user_msg:
        return jsonify({"reply": "No se recibió ningún mensaje."})

    # Inicializar historial de la sesión
    if "history" not in session:
        session["history"] = [
            {"role": "assistant", "content": "Hola, soy Lex, tu asesor legal de AboLegal. ¿En qué puedo ayudarte hoy?"}
        ]

    # Agregar mensaje del usuario
    session["history"].append({"role": "user", "content": user_msg})

    # Construir prompt completo a partir del historial
    prompt = ""
    for msg in session["history"]:
        if msg["role"] == "user":
            prompt += f"Usuario: {msg['content']}\n"
        else:
            prompt += f"Asesor IA: {msg['content']}\n"

    # Llamada a Gemini
    try:
        resp = model.generate_text(
            prompt=prompt,
            temperature=0.3,
            max_output_tokens=400
        )
        reply = resp.text if resp and hasattr(resp, "text") else "Lo siento, hubo un error con el modelo."
    except Exception as e:
        reply = f"Lo siento, hubo un error con el modelo: {str(e)}"

    # Guardar respuesta en historial
    session["history"].append({"role": "assistant", "content": reply})

    return jsonify({"reply": reply})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
