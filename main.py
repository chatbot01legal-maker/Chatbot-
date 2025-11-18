from flask import Flask, request, jsonify, render_template_string, session
from flask_cors import CORS
import os
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

# Necesario para sesiones. Usa una clave secreta fuerte en producción.
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Por favor define GEMINI_API_KEY en las variables de entorno de Render.")

# Configuración y modelo
genai.configure(api_key=API_KEY)
model_name = "gemini-2.5-flash"
model = genai.GenerativeModel(model_name)

# Mensaje de bienvenida inicial (para inicializar el chat)
INITIAL_MESSAGE = "Hola, soy Lex, tu asesor legal de AboLegal. ¿En qué puedo ayudarte hoy?"

# --- Código HTML para la Interfaz ---
CHAT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AboLegal Chatbot</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; background-color: #f4f4f4; }
        #chat-window { border: 1px solid #ccc; height: 400px; overflow-y: scroll; padding: 10px; background-color: #fff; border-radius: 8px; }
        .message { margin-bottom: 10px; padding: 8px; border-radius: 5px; }
        .user { text-align: right; background-color: #d1e7dd; margin-left: 20%; }
        .assistant { text-align: left; background-color: #f8d7da; margin-right: 20%; }
        #input-container { display: flex; margin-top: 10px; }
        #user-input { flex-grow: 1; padding: 10px; border: 1px solid #ccc; border-radius: 5px 0 0 5px; }
        #send-button { padding: 10px 15px; background-color: #007bff; color: white; border: none; cursor: pointer; border-radius: 0 5px 5px 0; }
        #send-button:disabled { background-color: #a0a0a0; cursor: not-allowed; }
    </style>
</head>
<body>
    <h1>Asesor Legal AboLegal (Lex) ⚖️</h1>
    <div id="chat-window"></div>
    <div id="input-container">
        <input type="text" id="user-input" placeholder="Escribe tu consulta legal..." autocomplete="off">
        <button id="send-button">Enviar</button>
    </div>

    <script>
        const chatWindow = document.getElementById('chat-window');
        const userInput = document.getElementById('user-input');
        const sendButton = document.getElementById('send-button');

        function appendMessage(sender, message) {
            const msgDiv = document.createElement('div');
            msgDiv.classList.add('message', sender);
            msgDiv.innerHTML = `${sender.charAt(0).toUpperCase() + sender.slice(1)}: ${message.replace(/\\n/g, '<br>')}`;
            chatWindow.appendChild(msgDiv);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }

        document.addEventListener('DOMContentLoaded', () => {
            appendMessage('assistant', 'Hola, soy Lex, tu asesor legal de AboLegal. ¿En qué puedo ayudarte hoy?');
        });

        async function sendMessage() {
            const message = userInput.value.trim();
            if (!message) return;

            appendMessage('user', message);
            userInput.value = '';
            sendButton.disabled = true;
            userInput.disabled = true;

            const typingIndicator = document.createElement('div');
            typingIndicator.id = 'typing-indicator';
            typingIndicator.classList.add('message', 'assistant');
            typingIndicator.innerHTML = 'Lex está escribiendo...';
            chatWindow.appendChild(typingIndicator);
            chatWindow.scrollTop = chatWindow.scrollHeight;

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();
                chatWindow.removeChild(typingIndicator);
                appendMessage('assistant', data.reply);
            } catch (error) {
                console.error('Error:', error);
                if(document.getElementById('typing-indicator')) {
                    chatWindow.removeChild(typingIndicator);
                }
                appendMessage('assistant', 'Lo siento, no pude conectar con el servidor.');
            } finally {
                sendButton.disabled = false;
                userInput.disabled = false;
                userInput.focus();
            }
        }

        sendButton.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
"""

# --- Rutas de Flask ---
@app.route("/", methods=["GET"])
def index():
    if "chat_session_history" not in session:
        session["chat_session_history"] = []
    return render_template_string(CHAT_HTML)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_msg = data.get("message", "")
    if not user_msg:
        return jsonify({"reply": "No se recibió ningún mensaje."})

    history = session.get("chat_session_history", [])
    history.append({"role": "user", "content": user_msg})

    try:
        # Llamada al modelo Gemini
        resp = model.chat(
            messages=[{"role": "system", "content": INITIAL_MESSAGE}] + history,
            temperature=0.3,
            max_output_tokens=400
        )
        reply = resp.last
    except Exception as e:
        reply = f"Lo siento, hubo un error con el modelo: {str(e)}"

    history.append({"role": "assistant", "content": reply})
    session["chat_session_history"] = history
    session.modified = True

    return jsonify({"reply": reply})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
