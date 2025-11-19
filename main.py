import os
import json
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
# Ya no es necesario 'pickle' en esta solución temporal
# import pickle 
# Importamos genai para la configuración global y GenerativeModel
import google.generativeai as genai 
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.generativeai.errors import APIError

app = Flask(__name__)

# Configuración de CORS: CORRECCIÓN PENDIENTE (T06). Se mantiene la configuración inicial
# El origen permitido debe ser la URL de Hostinger donde está el widget
CORS(app, resources={r"/chat": {"origins": ["https://www.abolegal.cl", "http://localhost:5000"]}})

# Clave secreta para sesiones (CRÍTICA para mantener el historial)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super_secret_key_change_me_in_prod")

# --- Configuración de Gemini ---
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("ADVERTENCIA: GEMINI_API_KEY no está definida. La API fallará.")
    
# ******************************************************************
# CORRECCIÓN DE TICKET #1: MIGRACIÓN A LA CONFIGURACIÓN MODERNA (genai.configure)

if API_KEY:
    genai.configure(api_key=API_KEY)
    
model_name = "gemini-2.5-flash"

# El mensaje inicial que define el rol (System Instruction)
INITIAL_MESSAGE = "Eres Lex, un asistente legal experto de AboLegal. Tu único objetivo es recopilar información preliminar sobre el caso legal del usuario. Debes mantener un tono formal, profesional y de apoyo. No debes proporcionar consejos legales concretos, sino hacer preguntas para documentar el caso. NO puedes agendar la cita todavía."

# Configuración de seguridad (opcional, pero recomendable)
safety_settings = [
    {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE},
]


# --- Funciones de Utilidad de Chat ---
def get_or_create_chat_session():
    """Crea un nuevo objeto chat de Gemini en cada solicitud.
    ADVERTENCIA: Esta es una solución temporal T07 para evitar el PicklingError.
    El historial de chat se perderá en cada solicitud POST.
    """
    
    if not API_KEY:
         raise APIError("La clave API de Gemini no está configurada.")

    # 1. Creamos el objeto GenerativeModel con la configuración de sistema
    ai_model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=INITIAL_MESSAGE,
        config={
            "safety_settings": safety_settings,
            "temperature": 0.3,
            "max_output_tokens": 400
        }
    )

    # 2. Iniciamos y devolvemos la conversación SIN guardar en la sesión
    chat = ai_model.start_chat()
    
    # IMPORTANTE: Aquí se podría integrar la lógica de historial con PostgreSQL
    # para regenerar el contexto, pero eso es Tarea T02 (Pendiente).
    
    return chat

# --- HTML del chat (Contenido del Iframe) ---
CHAT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AboLegal Chatbot</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 10px; background-color: #fff; display: flex; flex-direction: column; height: 100%; }
        #chat-window { border: none; flex-grow: 1; overflow-y: scroll; padding: 0 5px; }
        .message { margin-bottom: 10px; padding: 8px; border-radius: 5px; max-width: 80%; }
        .user { text-align: right; background-color: #d1e7dd; margin-left: auto; }
        .assistant { text-align: left; background-color: #f8d7da; margin-right: auto; }
        #input-container { display: flex; margin-top: 10px; padding-top: 5px; border-top: 1px solid #eee; }
        #user-input { flex-grow: 1; padding: 10px; border: 1px solid #ccc; border-radius: 5px 0 0 5px; }
        #send-button { padding: 10px 15px; background-color: #1a237e; color: white; border: none; cursor: pointer; border-radius: 0 5px 5px 0; }
        #send-button:disabled { background-color: #a0a0a0; cursor: not-allowed; }
    </style>
</head>
<body>
    <div id="chat-window"></div>
    <div id="input-container">
        <input type="text" id="user-input" placeholder="Escribe tu consulta legal..." autocomplete="off">
        <button id="send-button">Enviar</button>
    </div>

    <script>
        const chatWindow = document.getElementById('chat-window');
        const userInput = document.getElementById('user-input');
        const sendButton = document.getElementById('send-button');
        const backend_url = "/chat"; 

        function appendMessage(sender, message) {
            const msgDiv = document.createElement('div');
            msgDiv.classList.add('message', sender);
            msgDiv.innerHTML = `${message.replace(/\\n/g, '<br>')}`;
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
                const response = await fetch(backend_url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();
                
                if(document.getElementById('typing-indicator')) {
                    chatWindow.removeChild(typingIndicator);
                }

                if (response.ok) {
                    appendMessage('assistant', data.reply);
                } else {
                    appendMessage('assistant', `Error del servidor: ${data.reply || response.statusText}`);
                }

            } catch (error) {
                console.error('Error:', error);
                if(document.getElementById('typing-indicator')) {
                    chatWindow.removeChild(typingIndicator);
                }
                appendMessage('assistant', 'Lo siento, no pude conectar con el backend. Revisa la consola para más detalles.');
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
    return render_template_string(CHAT_HTML)

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "service": "legal-ai-backend"}), 200

@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return '', 200

    data = request.get_json()
    user_msg = data.get("message", "")
    if not user_msg:
        return jsonify({"reply": "No se recibió ningún mensaje."}), 400

    try:
        # Se genera un nuevo objeto chat en cada solicitud (solución T07)
        chat_session = get_or_create_chat_session()
        
        # Enviar el mensaje al objeto 'chat' de Gemini
        response = chat_session.send_message(
            user_msg,
            stream=False 
        )
        
        reply = response.text
        
        # Eliminadas las líneas de pickle
        
        return jsonify({"reply": reply})

    except APIError as e:
        print(f"Error de API de Gemini: {e}")
        # session.pop("chat_pickle", None) # No es necesario si no usamos session
        return jsonify({"reply": f"Error interno del modelo (APIError): Revise su clave Gemini."}), 500
    except Exception as e:
        print(f"Error desconocido en la ruta /chat: {e}")
        return jsonify({"reply": f"Error interno del servidor: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
