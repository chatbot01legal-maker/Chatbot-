from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import base64
import io
import json
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# ==============================
# CONFIG → GEMINI 2.5 PRO
# ==============================
openai.api_key = "TU_API_KEY_GEMINI"

# ==============================
# MEMORIA POR USUARIO
# ==============================
conversaciones = {}  # {"usuario_id": [{"role":"user","content": "..."}]}

# ==============================
# GOOGLE CALENDAR
# ==============================
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Tu archivo credentials.json debe estar en el mismo repo
SCOPES = ["https://www.googleapis.com/auth/calendar"]
calendar_credentials = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
calendar_service = build("calendar", "v3", credentials=calendar_credentials)

CALENDAR_ID = "primary"   # O el ID del calendario que quieras usar


def agendar_llamada(nombre, email):
    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(minutes=30)

    evento = {
        "summary": f"Reunión con {nombre}",
        "description": f"Agendada por el chatbot legal",
        "start": {"dateTime": start_time.isoformat() + "Z"},
        "end": {"dateTime": end_time.isoformat() + "Z"},
        "attendees": [{"email": email}],
        "conferenceData": {
            "createRequest": {"requestId": f"meet_{datetime.utcnow().timestamp()}"}
        }
    }

    evento_creado = calendar_service.events().insert(
        calendarId=CALENDAR_ID,
        body=evento,
        conferenceDataVersion=1
    ).execute()

    return evento_creado["hangoutLink"]


# ==============================
# TRANSCRIBIR AUDIO → TEXTO
# ==============================
def transcribir_audio(audio_b64):
    audio_bytes = base64.b64decode(audio_b64)

    response = openai.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=("audio.webm", audio_bytes, "audio/webm")
    )
    return response.text


# ==============================
# TEXTO → VOZ DE GEMINI
# ==============================
def generar_audio(texto):
    respuesta_audio = openai.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",  # Cambiar si quieres otra
        input=texto
    )
    return base64.b64encode(respuesta_audio.read()).decode("utf-8")


# ==============================
# CHAT PRINCIPAL
# ==============================
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    usuario_id = data.get("usuario_id", "anon")
    mensaje_texto = data.get("mensaje", "")
    mensaje_audio = data.get("audio", None)  # Base64

    # Crear memoria del usuario
    if usuario_id not in conversaciones:
        conversaciones[usuario_id] = []

    # Si viene audio → transcribir
    if mensaje_audio:
        mensaje_texto = transcribir_audio(mensaje_audio)

    # Guardar entrada usuario
    conversaciones[usuario_id].append({"role":"user","content": mensaje_texto})

    # Enviar a Gemini
    respuesta = openai.chat.completions.create(
        model="gemini-2.5-pro",
        messages=conversaciones[usuario_id]
    )

    texto_respuesta = respuesta.choices[0].message["content"]

    # Guardar respuesta en memoria
    conversaciones[usuario_id].append({"role":"assistant","content": texto_respuesta})

    # Generar audio Gemini
    audio_base64 = generar_audio(texto_respuesta)

    return jsonify({
        "respuesta_texto": texto_respuesta,
        "respuesta_audio": audio_base64
    })


# ==============================
# AGENDAR LLAMADA
# ==============================
@app.route("/agendar", methods=["POST"])
def agendar():
    data = request.json
    nombre = data.get("nombre")
    email = data.get("email")

    link = agendar_llamada(nombre, email)

    return jsonify({"meet_url": link})


# ==============================
# RUTA INICIAL
# ==============================
@app.route("/")
def inicio():
    return "Backend Legal-IA funcionando correctamente."


# ==============================
# EJECUCIÓN
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
