from flask import Flask, request, jsonify, render_template_string, session
from flask_cors import CORS
import os
import google.generativeai as genai
from google.generativeai.types import Content # Importar Content para manejar el historial

app = Flask(__name__)
CORS(app)

# Necesario para sesiones
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Por favor define GEMINI_API_KEY en las variables de entorno.")

genai.configure(api_key=API_KEY)
# Usaremos un modelo diseñado para la conversación
model_name = "gemini-2.5-flash" 
# El 2.5 Pro también funciona, pero Flash es más rápido y económico para chat
model = genai.GenerativeModel(model_name)

# Mensaje de bienvenida inicial (se usa para inicializar el chat)
INITIAL_MESSAGE = "Hola, soy Lex, tu asesor legal de AboLegal. ¿En qué puedo ayudarte hoy?"

# --- HTML omitido por brevedad, asumiendo que CHAT_HTML está bien definido ---

@app.route("/", methods=["GET"])
def index():
    # Limpiar o inicializar el chat de la sesión al cargar la página si lo deseas
    if "chat_session_history" not in session:
        session["chat_session_history"] = []
    return render_template_string(CHAT_HTML)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_msg = data.get("message", "")

    if not user_msg:
        return jsonify({"reply": "No se recibió ningún mensaje."})
    
    # 1. Recuperar o inicializar el historial/chat
    # El historial se guarda como una lista de diccionarios que representan objetos Content de Gemini
    history_dicts = session.get("chat_session_history", [])
    
    # Convertir los diccionarios del historial a objetos Content para la sesión de chat
    history_contents = [Content.from_dict(d) for d in history_dicts]

    # Iniciar la sesión de chat con el historial recuperado
    chat_session = model.start_chat(history=history_contents)

    # 2. Si el historial está vacío (primera vez), añade el mensaje inicial del Asistente (Lex)
    if not history_contents:
        # Añade el mensaje inicial como contexto, sin esperar una respuesta (role='model')
        # Esto es solo para que el modelo sepa la personalidad. No se muestra al usuario.
        chat_session.history.append(Content(role='model', parts=[{'text': INITIAL_MESSAGE}]))
        # Guarda este Content en la sesión de Flask (como dict)
        session["chat_session_history"].append({'role': 'model', 'parts': [{'text': INITIAL_MESSAGE}]})

    # 3. Enviar el nuevo mensaje y obtener la respuesta
    try:
        # Usamos send_message, que añade automáticamente el mensaje de 'user' y la respuesta de 'model' al historial.
        resp = chat_session.send_message(
            user_msg, 
            config=genai.types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=400
            )
        )
        reply = resp.text if resp and hasattr(resp, "text") else "Lo siento, hubo un error con el modelo."
    except Exception as e:
        reply = f"Lo siento, hubo un error con el modelo: {str(e)}"
        # Si hay un error, el historial no se actualiza.
        return jsonify({"reply": reply})

    # 4. Guardar el historial actualizado de la sesión de chat
    # El historial ahora incluye el último mensaje del usuario y la respuesta del modelo.
    # Convertimos los objetos Content de Gemini a diccionarios que se pueden serializar en la sesión de Flask.
    
    # Recuperamos los dos últimos mensajes (user y model) y los agregamos al historial de la sesión de Flask
    # La API de Gemini ya los añadió a chat_session.history
    
    # El historial ya incluye el mensaje del usuario y la respuesta del modelo.
    # Guardamos los dos últimos elementos añadidos al historial (User y Model)
    user_content = chat_session.history[-2].to_dict()
    model_content = chat_session.history[-1].to_dict()
    
    session["chat_session_history"].append(user_content)
    session["chat_session_history"].append(model_content)
    session.modified = True # Asegurar que Flask guarde la sesión

    return jsonify({"reply": reply})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
