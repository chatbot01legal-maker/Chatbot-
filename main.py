from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.status import HTTP_200_OK
from schemas import ScheduleRequest, ScheduleResponse
from datetime import datetime, timedelta
import os
import json

# --- IMPORTACIONES PARA GOOGLE CALENDAR API ---
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- INSTANCIA DE LA APLICACIÓN ---
app = FastAPI(
    title="LAW LAB - CASE_INTAKE API",
    version="1.0.0",
    description="API de agendamiento legal integrada con Google Calendar"
)

# --- CORS PARA FRONTEND ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, reemplazar con dominio específico
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURACIÓN GOOGLE CALENDAR ---
def get_calendar_service():
    """
    Autentica con Google Calendar API usando credenciales de servicio.
    Las credenciales deben estar en la variable de entorno GOOGLE_CREDENTIALS_JSON
    """
    try:
        credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
        if not credentials_json:
            raise ValueError("GOOGLE_CREDENTIALS_JSON no está definida en variables de entorno")
        
        credentials_info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        service = build('calendar', 'v3', credentials=credentials)
        return service
    except Exception as e:
        raise RuntimeError(f"Error en autenticación Google Calendar: {e}")

# --- LÓGICA REAL DE AGENDAMIENTO ---
def agendar_cita_real(request: ScheduleRequest) -> str:
    """
    Implementación real que crea un evento en Google Calendar.
    Retorna el event_id real de Google Calendar.
    """
    try:
        service = get_calendar_service()
        calendar_id = os.getenv('CALENDAR_ID')
        
        if not calendar_id:
            raise ValueError("CALENDAR_ID no está definido en variables de entorno")
        
        event = {
            'summary': f'Cita Legal - {request.client_name}',
            'description': request.problem_description,
            'start': {
                'dateTime': request.suggested_datetime.isoformat(),
                'timeZone': 'America/Santiago',
            },
            'end': {
                'dateTime': (request.suggested_datetime + timedelta(hours=1)).isoformat(),
                'timeZone': 'America/Santiago',
            },
            'attendees': [
                {'email': request.client_email}
            ],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 30},
                ],
            },
        }
        
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event,
            sendUpdates='all'
        ).execute()
        
        event_id = created_event['id']
        print(f"[{datetime.now().isoformat()}] Cita creada para {request.client_email} - ID: {event_id}")
        
        return event_id
        
    except HttpError as e:
        raise RuntimeError(f"Error de Google Calendar API: {e}")
    except Exception as e:
        raise RuntimeError(f"Error inesperado: {e}")

# --- ENDPOINTS ---
@app.get("/", status_code=HTTP_200_OK)
async def root():
    return {
        "status": "ok", 
        "service": "LAW LAB API", 
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/schedule", response_model=ScheduleResponse, status_code=HTTP_200_OK)
async def schedule_appointment(request: ScheduleRequest):
    try:
        appointment_id = agendar_cita_real(request)
        
        return ScheduleResponse(
            status="success",
            appointment_id=appointment_id,
            message=f"Agendamiento completado para {request.client_email}.",
            scheduled_time=request.suggested_datetime
        )
        
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Error de configuración: {e}")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Error con Google Calendar: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno del servidor")
