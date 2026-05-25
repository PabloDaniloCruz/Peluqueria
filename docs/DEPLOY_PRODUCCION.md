# Guía de Puesta en Producción — Studio Salta

> Nunca subiste nada a producción antes? Esta guía te lleva de la mano, paso a paso, desde cero hasta tener el sistema funcionando en PythonAnywhere.

## ¿Qué vamos a hacer?

Subir la app Django de Studio Salta a **PythonAnywhere**, un servicio gratuito que hostea aplicaciones web Python. Va a quedar accesible desde internet en una URL tipo `https://danilo2004.pythonanywhere.com`.

---

## Lo que necesitás antes de arrancar

- [ ] Una **cuenta en GitHub** (ya la tenés — el repo es `PabloDaniloCruz/Peluqueria`)
- [ ] Una **cuenta en PythonAnywhere** (gratis, la creamos acá)
- [ ] **Git instalado** en tu máquina local (ya lo tenés)
- [ ] El código **commiteado y pusheado** a GitHub

---

## Paso 1: Subir el código a GitHub

En tu máquina local (donde venís trabajando):

```bash
# 1. Agregar todo al commit
git add .

# 2. Hacer el commit (si no lo hiciste ya)
git commit -m "fix: seguridad y bugs pre-producción"

# 3. Subir a GitHub
git push origin main
```

> ⚠️ Si `git push` te pide usuario y contraseña, usá un **token personal** de GitHub (Settings → Developer settings → Personal access tokens). La contraseña de GitHub ya no funciona para `git push`.

---

## Paso 2: Crear cuenta en PythonAnywhere

1. Andá a [https://www.pythonanywhere.com/](https://www.pythonanywhere.com/)
2. Hacé clic en **"Start running Python online in 5 minutes"** → **"Create a free account"**
3. Elegí un nombre de usuario (si el que querés está ocupado, probá variantes)
4. Confirmá el mail

> ✨ **Tip:** tu URL final va a ser `https://tunombre.pythonanywhere.com`. Si tu usuario es `danilo2004`, la URL será la que ya está configurada.

---

## Paso 3: Crear la Web App

Ya logueado en PythonAnywhere:

1. Andá a la pestaña **"Web"** (arriba a la derecha)
2. Hacé clic en **"Add a new web app"**
3. Elegí **"Manual configuration"** (importante: NO elijas "Django")
4. Elegí la versión de Python: **3.12** (o la que tenés localmente, verificá con `python --version`)
5. Listo, ya tenés la web app creada

Al final de este paso, PythonAnywhere te muestra:
- **Tu URL:** `https://danilo2004.pythonanywhere.com`
- **Tu WSGI file:** `/var/www/danilo2004_pythonanywhere_com_wsgi.py`
- **Tu directorio home:** `/home/danilo2004/`

Anotá mentalmente la ruta del WSGI file — la vamos a necesitar.

---

## Paso 4: Clonar el repositorio

1. En PythonAnywhere, andá a la pestaña **"Consoles"** (arriba)
2. Hacé clic en **"Bash"** para abrir una terminal
3. Cloná el repo:

```bash
# Te va a pedir user y token de GitHub
git clone https://github.com/PabloDaniloCruz/Peluqueria.git

# Verificá que se creó la carpeta
ls
```

Si ves la carpeta `Peluqueria/`, todo bien.

---

## Paso 5: Crear el entorno virtual e instalar dependencias

Seguís en la terminal de PythonAnywhere:

```bash
# Ir a la carpeta del proyecto
cd Peluqueria

# Crear el entorno virtual
python3 -m venv venv

# Activarlo
source venv/bin/activate

# Actualizar pip (por si acaso)
pip install --upgrade pip

# Instalar todas las dependencias del proyecto
pip install -r requirements.txt
```

> ✅ **Para verificar:** después de instalar, corré `pip list | grep Django`. Tenés que ver `Django 5.2.14`.

---

## Paso 6: Configurar las variables de entorno

En tu máquina local cambiamos `settings.py` para que lea variables de entorno. Ahora hay que setearlas en PythonAnywhere.

### Opción A — Desde la pestaña Web (recomendada)

1. En PythonAnywhere, andá a **Web** → pestaña **Web**
2. Hacé scroll hasta **"Environment variables"**
3. Hacé clic en **"Add environment variable"** (agregá una por una):

| Variable | Valor |
|----------|-------|
| `DJANGO_SECRET_KEY` | Generalo con el Paso 6b de abajo |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `danilo2004.pythonanywhere.com` |
| `DJANGO_SETTINGS_MODULE` | `core.settings` |

### Paso 6b — Generar la SECRET_KEY

En la terminal de PythonAnywhere (con el venv activado):

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Te va a mostrar algo como `django-insecure-#$kj4...`. Copiá ESO y pegalo como valor de `DJANGO_SECRET_KEY`.

> 🔐 **Importante:** esa key es un secreto. No la subas a GitHub. Solo va en la variable de entorno de PythonAnywhere.

---

## Paso 7: Migraciones y archivos estáticos

Seguís en la terminal de PythonAnywhere, dentro de la carpeta `Peluqueria/`, con el venv activado:

```bash
# Asegurate de estar en la carpeta correcta
cd ~/Peluqueria

# Si no tenés el venv activado:
source venv/bin/activate

# Crear las tablas en la base de datos
python manage.py migrate
```

> ✅ Si ves un montón de líneas que dicen `OK`, las migraciones anduvieron.

```bash
# Recopilar archivos estáticos (CSS, JS, imágenes)
python manage.py collectstatic
```

Te va a preguntar `"Type 'yes' to attempt to overwrite..."`. Escribí **yes** y Enter.

---

## Paso 8: Configurar el WSGI file

Este es el archivo que PythonAnywhere usa para conectar la web con tu app Django.

1. Andá a **Web** → pestaña **Web**
2. En la sección **"Code"**, vas a ver un link **"WSGI configuration file"**
3. Hacé clic para editarlo
4. **Borrá TODO el contenido** y pegá esto:

```python
import os
import sys

# ─── Ruta al proyecto ────────────────────────────────────
path = '/home/danilo2004/Peluqueria'
if path not in sys.path:
    sys.path.append(path)

# ─── Settings module ──────────────────────────────────────
os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'

# ─── Activar el entorno virtual ───────────────────────────
venv_path = '/home/danilo2004/Peluqueria/venv/lib/python3.12/site-packages'
if venv_path not in sys.path:
    sys.path.append(venv_path)

# ─── Arrancar Django ───────────────────────────────────────
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

> ⚠️ **Cambiá `danilo2004` por TU usuario de PythonAnywhere** en las rutas.
>
> ⚠️ Si tu versión de Python no es 3.12, cambiá `python3.12` por la versión que corresponda (podés verificarlo con `python --version` en la consola).

5. Hacé clic en **Save**.

---

## Paso 9: Configurar archivos estáticos (Static files)

Django sirve los archivos estáticos (CSS, JS) desde la carpeta `staticfiles/`. Hay que decirle a PythonAnywhere dónde encontrarlos.

1. En **Web** → pestaña **Web**, bajá hasta **"Static files"**
2. En **"URL"** poné: `/static/`
3. En **"Path"** poné: `/home/danilo2004/Peluqueria/staticfiles`
4. Hacé clic en **"Add static file"**

---

## Paso 10: Recargar y probar

1. En **Web** → pestaña **Web**, arriba de todo, hacé clic en el botón verde **"Reload"**
2. Esperá 2-3 segundos
3. Andá a `https://danilo2004.pythonanywhere.com`

Si ves el login de Studio Salta, **felicidades, está en producción** 🎉

---

## Verificación rápida

Una vez que funcione, verificá que todo esté bien:

- [ ] Ingresá con tu usuario y contraseña
- [ ] El dashboard carga sin errores
- [ ] Los turnos se ven
- [ ] Andá a Facturación → los gráficos cargan
- [ ] Andá a Clientes → la lista se muestra
- [ ] Creá un turno de prueba

---

## 💥 Solución de problemas comunes

### Error 500 — Internal Server Error
**Causa más probable:** las variables de entorno no están configuradas o el WSGI tiene la ruta incorrecta.

**Qué hacer:**
1. En la terminal de PythonAnywhere, corré:
   ```bash
   cd ~/Peluqueria
   source venv/bin/activate
   python manage.py check --deploy
   ```
   Te va a decir qué falta.

2. Andá a **Web** → **Error log** (a la derecha de la página). Ahí está el error real. Copialo y busca ayuda.

### Error 404 en estáticos (CSS sin estilo)
**Causa:** No configuraste los **Static files** en la pestaña Web, o no corriste `collectstatic`.

**Fix:** Revisá el Paso 9. Asegurate de que la ruta de `Path` sea la correcta.

### "DisallowedHost" en el error log
**Causa:** `DJANGO_ALLOWED_HOSTS` no está configurado o tiene el valor incorrecto.

**Fix:** Andá a **Web** → **Environment variables** y verificá que `DJANGO_ALLOWED_HOSTS` sea exactamente `danilo2004.pythonanywhere.com` (sin espacios, sin `https://`).

### Error al hacer `migrate` — "No module named..."
**Causa:** No activaste el venv o no instalaste las dependencias.

**Fix:**
```bash
cd ~/Peluqueria
source venv/bin/activate
pip install -r requirements.txt
```

### El reloj no se actualiza

**Causa:** La primera vez que recargás, Django tarda un poco. Los turnos de hoy pueden aparecer atrasados.

**Fix:** No pasa nada — es normal. Usá el botón de "Hoy" en el dashboard.

---

## ¿Y si quiero actualizar después?

Cada vez que hagas cambios en tu máquina local y los quieras subir:

```bash
# En tu máquina local
git add .
git commit -m "lo-que-cambiaste"
git push origin main

# En la consola de PythonAnywhere
cd ~/Peluqueria
git pull origin main
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
```

Y después hacé clic en **Reload** en la pestaña Web.

---

## Próximos pasos (cuando quieras avanzar)

- **Dominio propio:** en PythonAnywhere podés configurar un dominio tipo `studiosalta.com.ar` (es un servicio pago)
- **Base de datos:** si crece mucho, migrar de SQLite a PostgreSQL (PythonAnywhere lo soporta)
- **Backups:** programar backups semanales de `db.sqlite3`
- **SSL:** con dominio propio, podés configurar HTTPS automático

---

> ✨ **¿Alguna duda?** Mandame un mensaje y te ayudo a debuggear. Nunca nadie nace sabiendo deploy — todos arrancamos desde acá.
