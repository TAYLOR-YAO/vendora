from vendora_backend.celery import app
from .models import Event
from .services import process_event

@app.task(bind=True, max_retries=3)
def process_event_task(self, event_id: str):
    ev = Event.objects.get(id=event_id)
    process_event(ev)
