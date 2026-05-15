import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import RequestFactory
from gestion.views import api_horarios_disponibles
import datetime

factory = RequestFactory()
fecha = str(datetime.date.today())
request = factory.get(f'/api/horarios/?profesional=1&servicio=1&fecha={fecha}')
response = api_horarios_disponibles(request)

print(f"Status: {response.status_code}")
try:
    print(response.content.decode())
except Exception as e:
    print("Error decoding:", e)

