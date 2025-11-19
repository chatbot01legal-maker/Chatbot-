import os
import json
from flask import Flask, request, jsonify, render_template_string, session
from flask_cors import CORS
# ******************************************************************
# CORRECCIÓN DE TICKET #1: Importación de Gemini (Version 0.8.5)
# Reemplazamos 'from google import genai' por la importación directa de Client
from google.generativeai import Client 
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.generativeai.errors import APIError
import pickle # Para serializar el historial del chat

app = Flask(__name__)

# Configuración de CORS:
CORS(app, resources={r"/chat": {"origins": ["https://www.abolegal.cl", "http://localhost:5000"]}})

# Clave secreta para sesiones (CRÍTICA para mantener el historial)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super_secret_key_change_me_in_prod")

# --- Configuración de Gemini ---
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("ADVERTENCIA: GEMINI_API_KEY no está definida. La API fallará.")
    
try:
    # ******************************************************************
    # CORRECCIÓN DE TICKET #1: Usamos la clase Client directamente
    client = Client(api_key=API_KEY)
except Exception as e:
    print(f"Error al instanciar el cliente de Gemini: {e}")
    client = None

model_name = "gemini-2.5-flash"

# El mensaje inicial que define el rol (System Instruction)
INITIAL_MESSAGE = "Eres Lex, un asistente legal experto de AboLegal. Tu único objetivo es recopilar información preliminar sobre el caso legal del usuario. Debes mantener un tono formal, profesional y de apoyo. No debes proporcionar consejos legales concretos, sino hacer preguntas para documentar el caso. NO puedes agendar la cita todavía."

# Configuración de seguridad (opcional, pero recomendable)
safety_settings = [
    {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE},
]


# --- Funciones de Utilidad de Chat ---
def get_or_create_chat_session():
    """Recupera el objeto chat de Gemini de la sesión de Flask o crea uno nuevo."""
    global client
    
    if not client:
         # Esto se disparará si la clave API no es válida al inicio
         raise APIError("El cliente de Gemini no pudo ser inicializado. Revise GEMINI_API_KEY.")

    if "chat_pickle" in session:
        try:
            # Deserializar el objeto de chat si existe
            chat = pickle.loads(session["chat_pickle"])
            # Asegurar que el modelo configurado es el mismo
            if chat.model_name != model_name:
                 raise Exception("Modelo de chat desactualizado.")
            return chat
        except Exception as e:
            # Si el pickle está corrupto, lo limpiamos y creamos uno nuevo
            print(f"Error al cargar la sesión de chat: {e}. Creando una nueva.")
            session.pop("chat_pickle", None)
            
    # Crear una nueva sesión de chat
    # NOTA: Usamos generate_content_stream con stream=False para inicializar la sesión
    # con el System Instruction antes del primer mensaje del usuario.
    chat = client.models.generate_content_stream(
         model=model_name,
         contents=[{"role": "user", "parts": [{"text": "Inicia la conversación."}]}],
         config={"system_instruction": INITIAL_MESSAGE, 
                 "safety_settings": safety_settings,
                 "temperature": 0.3,
                 "max_output_tokens": 400},
         stream=False 
    )
    
    # Guardar el objeto de chat serializado en la sesión
    session["chat_pickle"] = pickle.dumps(chat)
    session.modified = True
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
        const backend_url = "/chat"; // Se resuelve a la URL del backend

        function appendMessage(sender, message) {
            const msgDiv = document.createElement('div');
            msgDiv.classList.add('message', sender);
            msgDiv.innerHTML = `${message.replace(/\\n/g, '<br>')}`;
            chatWindow.appendChild(msgDiv);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }

        document.addEventListener('DOMContentLoaded', () => {
             // Mensaje inicial estático que coincide con el rol del bot
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
    # Esta ruta servirá el contenido del IFRAME (el chat real)
    return render_template_string(CHAT_HTML)

@app.route("/ping", methods=["GET"])
def ping():
    # Ruta de chequeo de salud (útil para Render)
    return jsonify({"status": "ok", "service": "legal-ai-backend"}), 200

@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    # Manejo de preflight OPTIONS para CORS
    if request.method == "OPTIONS":
        return '', 200

    data = request.get_json()
    user_msg = data.get("message", "")
    if not user_msg:
        return jsonify({"reply": "No se recibió ningún mensaje."}), 400

    try:
        # Recuperar o crear la sesión de chat (con historial)
        # Esto iniciará una nueva conversación si la sesión ha expirado o no existe
        chat_session = get_or_create_chat_session()
        
        # Enviar el nuevo mensaje
        response = chat_session.send_message(
            user_msg,
            stream=False # Desactivamos el streaming por ahora
        )
        
        reply = response.text
        
        # Guardar el objeto de chat actualizado en la sesión
        session["chat_pickle"] = pickle.dumps(chat_session)
        session.modified = True
        
        return jsonify({"reply": reply})

    except APIError as e:
        print(f"Error de API de Gemini: {e}")
        # Limpiamos la sesión para forzar una nueva en el siguiente intento
        session.pop("chat_pickle", None) 
        return jsonify({"reply": f"Error interno del modelo (APIError): Revise su clave Gemini."}), 500
    except Exception as e:
        print(f"Error desconocido en la ruta /chat: {e}")
        return jsonify({"reply": f"Error interno del servidor: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # NOTA: debug=True solo en desarrollo. En Render se usa Gunicorn.
    app.run(host="0.0.0.0", port=port, debug=True)
