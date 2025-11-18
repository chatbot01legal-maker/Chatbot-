from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import google.generativeai as genai
import os

app = Flask(__name__)
CORS(app)

# ============================
# CONFIGURAR GEMINI
# ============================
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.0-flash-thinking-exp-01-21")

# ============================
# RUTA PRINCIPAL DEL CHAT (HTML)
# ============================
CHAT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Asesor Legal IA</title>
    <style>
        body {
            font-family: Arial;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
        }
        #container {
            width: 100%;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        #messages {
            flex: 1;
            padding: 15px;
            overflow-y: auto;
        }
        #input-area {
            padding: 10px;
            background: #ddd;
            display: flex;
        }
        #input-area input {
            flex: 1;
            padding: 10px;
            border-radius: 6px;
            border: 1px solid #aaa;
        }
        #input-area button {
            margin-left: 10px;
            padding: 10px 18px;
            background: #1a237e;
            border: none;
            color: white;
            border-radius: 6px;
            cursor: pointer;
        }
    </style>

    <script>
        async function sendMessage() {
            const input = document.getElementById("msg");
            const text = input.value.trim();
            if (!text) return;

            const messagesBox = document.getElementById("messages");
            messagesBox.innerHTML += "<p><b>Tú:</b> " + text + "</p>";

            input.value = "";

            const response = await fetch("/api/message", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({message: text})
            });

            const data = await response.json();
            messagesBox.innerHTML += "<p><b>Asesor IA:</b> " + data.reply + "</p>";

            messagesBox.scrollTop = messagesBox.scrollHeight;
        }
    </script>
</head>

<body>
    <div id="container">
        <div id="messages"></div>

        <div id="input-area">
            <input id="msg" placeholder="Escribe tu mensaje…" onkeydown="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Enviar</button>
        </div>
    </div>
</body>
</html>
"""

@app.route("/")
def home():
    return jsonify({"status": "ok", "message": "Legal AI Chatbot running."})

@app.route("/chat")
def chat():
    return render_template_string(CHAT_HTML)

# ============================
# API DEL CHAT
# ============================
@app.route("/api/message", methods=["POST"])
def api_message():
    data = request.get_json()
    user_msg = data.get("message", "")

    try:
        response = model.generate_content(user_msg)
        reply = response.text
    except Exception as e:
        reply = "Lo siento, hubo un error con el modelo."

    return jsonify({"reply": reply})

# ============================
# INICIO SERVIDOR
# ============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
