# NeuroRehab Platform

Plataforma web de evaluación cognitivo-motora para rehabilitación
neurológica. Ver [docs/SPEC_NEURORREHAB_PLATFORM.md](docs/SPEC_NEURORREHAB_PLATFORM.md)
para la especificación completa, y [docs/GUIA_DE_ARCHIVOS.md](docs/GUIA_DE_ARCHIVOS.md)
para una explicación simple de qué hace cada archivo de código.

## Cómo correrlo (primera vez en una computadora nueva)

Necesitás tener **Python 3.12** o similar instalado
(<https://www.python.org/downloads/>, marcar la opción "Add Python to PATH"
durante la instalación).

Después, abrí una terminal en la carpeta del proyecto y ejecutá estos pasos
**una sola vez**:

**Windows:**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Mac / Linux:**

```bash
cd backend
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

Esto crea una carpeta `backend/.venv` con una copia aislada de Python y le
instala únicamente lo que este proyecto necesita (no afecta nada más de la
computadora).

## Cómo correrlo (todas las veces siguientes)

Desde la carpeta del proyecto:

**Windows:**

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn server:app --reload
```

**Mac / Linux:**

```bash
cd backend
./.venv/bin/python -m uvicorn server:app --reload
```

Vas a ver un mensaje como `Uvicorn running on http://127.0.0.1:8000`. Dejá
esa terminal abierta — mientras esté abierta, el servidor sigue corriendo —
y abrí en el navegador:

```
http://127.0.0.1:8000/
```

Para apagarlo, `Ctrl+C` en esa misma terminal.

## Estructura del proyecto

- `backend/server.py` — un solo archivo de Python: la base de datos, el
  login/registro, la lista de tests, y el servidor que entrega las páginas.
- `frontend/` — la página web (HTML, CSS, JavaScript). Sin pasos de
  compilación ni piezas "compartidas": cada página `.html` tiene su propio
  `<script>` adentro con todo lo que necesita, de arriba a abajo, sin saltar
  a otro archivo (a costa de repetir un poco de código entre páginas).
- `firmware/` — proyecto de PlatformIO con el código C++ que corre en el
  ESP32 (lee botones/joystick/encoder/acelerómetro, controla LEDs y la
  pantalla OLED). Los 4 botones de colores ya mandan sus eventos por UDP al
  backend, que los reenvía en vivo al navegador por WebSocket — Stroop ya
  reacciona al botón físico real. El backend también puede mandarle comandos
  al ESP32 por el mismo canal UDP (por ejemplo, prender un LED puntual como
  estímulo de un test). El resto (joystick, encoder, acelerómetro) todavía
  no está conectado de esa forma. Ver `docs/GUIA_DE_ARCHIVOS.md` sección 7.
- `docs/` — documentación del proyecto.
- `references/` — prototipo previo en Python/Pygame, usado solo como
  referencia conceptual (no es código que se reutilice).
