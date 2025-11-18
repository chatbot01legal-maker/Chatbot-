import os
import json
from flask import Flask, request, jsonify, render_template_string, session
from flask_cors import CORS
from google import genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.generativeai.errors import APIError
import pickle # Para serializar el historial del chat

app = Flask(__name__)

# Configuración de CORS: Asegúrese de cambiar "http://localhost:5000" si prueba en otro puerto
# o si despliega el widget en un dominio diferente a https://www.abolegal.cl
CORS(app, resources={r"/chat": {"origins": ["https://www.abolegal.cl", "http://localhost:5000"]}})

# Clave secreta para sesiones (CRÍTICA para mantener el historial)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super_secret_key_change_me_in_prod")

# --- Configuración de Gemini ---
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    # Usar un error menos intrusivo si se espera una variable de entorno
    print("ADVERTENCIA: GEMINI_API_KEY no está definida. La API fallará.")
    
try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    # Manejo de error si la clave es inválida al instanciar el cliente
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
         raise APIError("El cliente de Gemini no pudo ser inicializado.")

    if "chat_pickle" in session:
        try:
            # Deserializar el objeto de chat si existe
            chat = pickle.loads(session["chat_pickle"])
            # Asegurar que el modelo configurado es el mismo
            if chat.model_name != model_name:
                 raise Exception("Modelo de chat desactualizado.")
            return chat
        except Exception as e:
            print(f"Error al cargar la sesión de chat: {e}. Creando una nueva.")
            session.pop("chat_pickle", None) # Limpiar la sesión corrupta
            
    # Crear una nueva sesión de chat
    chat = client.models.generate_content_stream(
         model=model_name,
         contents=[{"role": "user", "parts": [{"text": INITIAL_MESSAGE}]}],
         config={"system_instruction": INITIAL_MESSAGE, 
                 "safety_settings": safety_settings,
                 "temperature": 0.3,
                 "max_output_tokens": 400},
         # Inicializar la conversación con el mensaje del sistema
         stream=False 
    )
    # Guardar el objeto de chat serializado en la sesión
    session["chat_pickle"] = pickle.dumps(chat)
    session.modified = True
    return chat

# --- HTML del chat (mismo que el suyo) ---
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
        const backend_url = "http://localhost:5000/chat"; // <--- CAMBIAR al desplegar en Render

        function appendMessage(sender, message) {
            const msgDiv = document.createElement('div');
            msgDiv.classList.add('message', sender);
            msgDiv.innerHTML = `${sender.charAt(0).toUpperCase() + sender.slice(1)}: ${message.replace(/\\n/g, '<br>')}`;
            chatWindow.appendChild(msgDiv);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }

        // Recuperar el primer mensaje del asistente
        async function getInitialMessage() {
            try {
                // Llamada a una ruta de inicialización si fuera necesaria. 
                // Por ahora, usamos un mensaje estático y la lógica de Python lo ajustará.
                appendMessage('assistant', 'Hola, soy Lex, tu asesor legal de AboLegal. ¿En qué puedo ayudarte hoy?');
            } catch (error) {
                console.error('Error al obtener el mensaje inicial:', error);
                appendMessage('assistant', 'Error de inicialización.');
            }
        }
        
        document.addEventListener('DOMContentLoaded', getInitialMessage);

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
                // La URL debe coincidir con la de su backend
                const response = await fetch(backend_url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();
                
                // Remover el indicador de tipeo SOLO si la solicitud fue exitosa
                if(document.getElementById('typing-indicator')) {
                    chatWindow.removeChild(typingIndicator);
                }

                if (response.ok) {
                    appendMessage('assistant', data.reply);
                } else {
                    // Manejo de errores HTTP (ej: 400, 500)
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
    # Esta ruta es solo para pruebas internas y desarrollo.
    return render_template_string(CHAT_HTML)


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
        chat_session = get_or_create_chat_session()
        
        # Enviar el nuevo mensaje
        response = chat_session.send_message(
            user_msg,
            stream=False # Desactivamos el streaming por ahora, simplificando la lógica de la Fase 1
        )
        
        reply = response.text
        
        # Guardar el objeto de chat actualizado en la sesión
        session["chat_pickle"] = pickle.dumps(chat_session)
        session.modified = True
        
        return jsonify({"reply": reply})

    except APIError as e:
        print(f"Error de API de Gemini: {e}")
        # En caso de error de API, limpiamos la sesión para forzar una nueva en el siguiente intento
        session.pop("chat_pickle", None) 
        return jsonify({"reply": f"Error interno del modelo (APIError): {str(e)}"}), 500
    except Exception as e:
        print(f"Error desconocido en la ruta /chat: {e}")
        return jsonify({"reply": f"Error interno del servidor: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # NOTA: debug=True solo en desarrollo. En Render se usa Gunicorn.
    app.run(host="0.0.0.0", port=port, debug=True)
    
