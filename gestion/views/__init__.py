# Re-export all views so existing imports like
# `from .views import dashboard_recepcion` keep working.

from .dashboard import *       # noqa: F401,F403
from .reservas import *        # noqa: F401,F403
from .turnos import *          # noqa: F401,F403
from .clientes import *        # noqa: F401,F403
from .profesionales import *   # noqa: F401,F403
from .servicios import *       # noqa: F401,F403
from .productos import *       # noqa: F401,F403
from .fichas import *          # noqa: F401,F403
from .ventas import *          # noqa: F401,F403
from .api import *             # noqa: F401,F403
from .estaciones import *      # noqa: F401,F403
