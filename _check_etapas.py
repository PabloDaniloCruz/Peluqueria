import django, os, sys
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()
from gestion.models import Servicio, EtapaServicio, Estacion, DetalleTurno
from django.db.models import Count

print("=== ETAPAS POR SERVICIO ===")
for s in Servicio.objects.filter(activo=True):
    etapas = s.etapas.all().order_by("orden")
    if etapas:
        print(f"\n{s.nombre}:")
        for e in etapas:
            print(f"  {e.orden}. {e.nombre} ({e.duracion}min, tipo={e.tipo_estacion}, req_prof={e.requiere_profesional})")
    else:
        print(f"{s.nombre}: (sin etapas)")

print("\n=== ESTACIONES ===")
for e in Estacion.objects.filter(activa=True):
    print(f"  {e.nombre} ({e.tipo})")

print("\n=== DETALLE_TURNO: estaciones usadas ===")
rows = DetalleTurno.objects.values("estacion__nombre", "estacion__tipo").annotate(c=Count("id")).order_by("-c")
for r in rows:
    print(f"  {r['estacion__nombre']} ({r['estacion__tipo']}): {r['c']} turnos")
