# =============================================================================
# Servidor de NeuroRehab Platform.
#
# Este es el UNICO archivo de backend. De arriba a abajo, hace 5 cosas:
#   1. Conectarse a la base de datos SQLite (un solo archivo en disco) donde
#      se guardan los médicos y los pacientes.
#   2. Transformar contraseñas en un código (hash) para no guardarlas tal cual.
#   3. Atender los pedidos que llegan del navegador: login, registro, lista
#      de los 5 tests clínicos, alta/búsqueda de pacientes, y el puente con
#      el dispositivo ESP32 (UDP <-> WebSocket/HTTP, ver sección 3c más abajo).
#   4. Servir los archivos de la carpeta frontend/ (las páginas web en sí).
#
# Se levanta con: uvicorn server:app --reload
# =============================================================================

import asyncio
import hashlib
import json
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# -----------------------------------------------------------------------------
# 1. Base de datos
# -----------------------------------------------------------------------------

DB_PATH = Path(__file__).resolve().parent / "data" / "neurorehab.db"


def conectar_db() -> sqlite3.Connection:
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion


def inicializar_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conexion = conectar_db()
    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS medicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            nombre TEXT NOT NULL
        )
        """
    )
    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            fecha_nacimiento TEXT,
            comentarios TEXT
        )
        """
    )
    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            test_slug TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            parametros_json TEXT NOT NULL,
            metricas_json TEXT NOT NULL,
            comentarios_medico TEXT
        )
        """
    )
    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS resultados_detalle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resultado_id INTEGER NOT NULL,
            numero_estimulo INTEGER NOT NULL,
            estimulo TEXT NOT NULL,
            respuesta TEXT,
            correcto INTEGER NOT NULL,
            tipo_error TEXT,
            rt_ms INTEGER
        )
        """
    )
    conexion.commit()
    conexion.close()


# -----------------------------------------------------------------------------
# 2. Contraseñas: se transforman en un código (hash) antes de guardarlas.
# -----------------------------------------------------------------------------

def hashear_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    codigo = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${codigo}"


def password_es_correcta(password: str, hash_guardado: str) -> bool:
    salt, _, _ = hash_guardado.partition("$")
    return hashear_password(password, salt) == hash_guardado


# -----------------------------------------------------------------------------
# 3a. Catálogo fijo de los 5 tests clínicos (sección 10 del documento de spec).
# -----------------------------------------------------------------------------

TESTS = [
    {
        "slug": "faro",
        "nombre": "Exploración de Faro",
        "evalua": "Exploración visual activa, atención espacial y neglect espacial.",
        "funcionamiento": (
            "El paciente controla una linterna con el joystick sobre una pantalla "
            "oscurecida; solo una región circular está iluminada. Debe localizar "
            "objetivos ocultos en la escena."
        ),
        "variables": [
            "Tiempo total",
            "Tiempo al primer hallazgo",
            "Cobertura espacial",
            "Omisiones",
            "Objetivos encontrados",
            "Trayectoria",
        ],
        "metricas_detalle": [
            {
                "nombre": "Índice de omisión izquierda",
                "que_mide": "Qué porcentaje de los objetivos del lado izquierdo el paciente no encontró.",
                "como_se_calcula": "Objetivos izquierdos omitidos dividido objetivos izquierdos totales.",
                "interpretacion": [
                    {"rango": "Menor a 10%", "nivel": "Normal"},
                    {"rango": "10% a 20%", "nivel": "Leve"},
                    {"rango": "20% a 40%", "nivel": "Moderado"},
                    {"rango": "Mayor a 40%", "nivel": "Severo"},
                ],
            },
            {
                "nombre": "Asimetría izquierda-derecha",
                "que_mide": "Si el paciente encontró más objetivos de un lado que del otro.",
                "como_se_calcula": (
                    "(Encontrados a la derecha menos encontrados a la izquierda) "
                    "dividido la suma de ambos."
                ),
                "interpretacion": [
                    {"rango": "Menor a 0,10", "nivel": "Normal"},
                    {"rango": "0,10 a 0,20", "nivel": "Leve"},
                    {"rango": "0,20 a 0,40", "nivel": "Moderado"},
                    {"rango": "Mayor a 0,40", "nivel": "Severo"},
                ],
            },
            {
                "nombre": "Center of Cancellation (Rorden & Karnath, 2010)",
                "que_mide": (
                    "El sesgo espacial general, considerando en qué posición exacta "
                    "estaba cada objetivo encontrado (más sensible que la asimetría simple)."
                ),
                "como_se_calcula": (
                    "Posición horizontal promedio de los objetivos encontrados, comparada "
                    "contra el centro de todos los objetivos generados, normalizada para "
                    "que el resultado quede siempre entre -1 y 1."
                ),
                "interpretacion": [
                    {"rango": "Menor a 0,081", "nivel": "Normal"},
                    {"rango": "0,081 a 0,20", "nivel": "Leve"},
                    {"rango": "0,20 a 0,40", "nivel": "Moderado"},
                    {"rango": "Mayor a 0,40", "nivel": "Severo"},
                ],
            },
            {
                "nombre": "Latencia al primer objetivo izquierdo",
                "que_mide": (
                    "Cuánto tarda el paciente en \"romper\" el sesgo inicial hacia la "
                    "derecha y empezar a encontrar objetivos de la izquierda."
                ),
                "como_se_calcula": (
                    "Tiempo hasta encontrar el primer objetivo izquierdo dividido el "
                    "tiempo hasta encontrar el primer objetivo derecho."
                ),
                "interpretacion": [
                    {"rango": "Menor a 2", "nivel": "Normal"},
                    {"rango": "2 a 4", "nivel": "Leve"},
                    {"rango": "4 a 8", "nivel": "Moderado"},
                    {"rango": "Mayor a 8", "nivel": "Severo"},
                ],
            },
            {
                "nombre": "Cobertura espacial izquierda",
                "que_mide": (
                    "Qué porcentaje del lado izquierdo de la pantalla llegó a iluminar "
                    "con la linterna, más allá de si encontró objetivos ahí."
                ),
                "como_se_calcula": (
                    "Porcentaje de la mitad izquierda de la pantalla que fue recorrida "
                    "con el círculo de luz en algún momento del test."
                ),
                "interpretacion": [
                    {"rango": "Mayor a 80%", "nivel": "Normal"},
                    {"rango": "60% a 80%", "nivel": "Leve"},
                    {"rango": "40% a 60%", "nivel": "Moderado"},
                    {"rango": "Menor a 40%", "nivel": "Severo"},
                ],
            },
        ],
        "hardware": "Joystick (streaming continuo de posición).",
        "bibliografia_estado": (
            "Índices de omisión y asimetría inspirados en Albert's Test y Star "
            "Cancellation; Center of Cancellation según Rorden & Karnath (2010)."
        ),
    },
    {
        "slug": "stroop",
        "nombre": "Efecto Stroop",
        "evalua": "Atención selectiva y control inhibitorio.",
        "funcionamiento": (
            "Se muestra una palabra de color (por ejemplo, 'ROJO') escrita en una "
            "tinta de color distinto; el paciente responde con los botones de "
            "colores (rojo, verde, azul, amarillo)."
        ),
        "variables": [
            "Tiempo de reacción",
            "Errores",
            "Aciertos",
            "Efecto Stroop (interferencia)",
        ],
        "hardware": "Botones de colores con LED.",
        "metricas_detalle": [
            {
                "nombre": "Precisión (nivel fácil)",
                "que_mide": (
                    "Qué porcentaje de las respuestas fueron correctas, cuando la "
                    "palabra y el color de tinta siempre coinciden (100% congruente)."
                ),
                "como_se_calcula": "Respuestas correctas dividido el total de estímulos evaluados.",
                "interpretacion": [
                    {"rango": "Mayor o igual a 98%", "nivel": "Normal"},
                    {"rango": "96% a 98%", "nivel": "Limítrofe"},
                    {"rango": "Menor a 96%", "nivel": "Patológico"},
                ],
            },
            {
                "nombre": "Precisión (nivel intermedio o difícil)",
                "que_mide": (
                    "Qué porcentaje de las respuestas fueron correctas, cuando hay "
                    "palabras que no coinciden con el color de la tinta."
                ),
                "como_se_calcula": "Respuestas correctas dividido el total de estímulos evaluados.",
                "interpretacion": [
                    {"rango": "Mayor o igual a 90%", "nivel": "Normal"},
                    {"rango": "80% a 90%", "nivel": "Limítrofe"},
                    {"rango": "Menor a 80%", "nivel": "Patológico"},
                ],
            },
            {
                "nombre": "Efecto Stroop (interferencia)",
                "que_mide": (
                    "Cuánto más tarda el paciente en responder a un estímulo "
                    "incongruente (la palabra no coincide con el color) comparado "
                    "con uno congruente. Solo se calcula en el nivel intermedio, que "
                    "mezcla estímulos de los dos tipos."
                ),
                "como_se_calcula": (
                    "Tiempo de reacción promedio en estímulos incongruentes menos "
                    "tiempo de reacción promedio en estímulos congruentes."
                ),
                "interpretacion": [
                    {"rango": "150 a 350 ms", "nivel": "Esperado en adultos sin lesión"},
                ],
            },
        ],
        "bibliografia_estado": (
            "Clasificación de precisión por nivel de congruencia (Brysbaert & "
            "Stevens, 2018), e interferencia esperada de 150 a 350 ms entre "
            "ensayos congruentes e incongruentes (MacLeod, 1991)."
        ),
    },
    {
        "slug": "nback",
        "nombre": "N-Back de Colores",
        "evalua": "Memoria de trabajo y atención sostenida.",
        "funcionamiento": (
            "Se le muestra al paciente una secuencia de uno o más colores con "
            "los LEDs del control (uno por vez, con una pausa entre cada uno). "
            "Cuando la secuencia termina, el paciente debe reproducirla "
            "apretando los botones de colores en el mismo orden en que se "
            "prendieron los LEDs. En el nivel fácil la secuencia es de un solo "
            "color; en el medio, de dos; en el difícil, el médico elige de "
            "antemano cuántos colores (hasta 6)."
        ),
        "variables": [
            "Precisión de las respuestas",
            "Tiempo de reacción",
            "Errores de omisión",
            "Errores de comisión",
        ],
        "hardware": "4 LEDs de colores (estímulo) y 4 botones de colores (respuesta).",
        "metricas_detalle": [
            {
                "nombre": "Precisión",
                "que_mide": (
                    "Qué porcentaje de los colores individuales de las secuencias "
                    "fueron reproducidos correctamente, en la posición correcta."
                ),
                "como_se_calcula": (
                    "Respuestas correctas dividido el total de estímulos evaluados "
                    "(cantidad de intentos × colores por secuencia)."
                ),
                "interpretacion": [
                    {"rango": "Hasta 5 puntos porcentuales por debajo de la referencia del nivel", "nivel": "Normal"},
                    {"rango": "Entre 5 y 15 puntos por debajo", "nivel": "Leve"},
                    {"rango": "Entre 15 y 30 puntos por debajo", "nivel": "Moderado"},
                    {"rango": "Más de 30 puntos por debajo", "nivel": "Severo"},
                ],
            },
            {
                "nombre": "Tiempo de reacción",
                "que_mide": "Cuánto tarda el paciente en presionar cada botón de respuesta, en promedio.",
                "como_se_calcula": (
                    "Promedio del tiempo entre que el paciente puede empezar a "
                    "responder y el momento en que presiona cada botón, solo en "
                    "las respuestas correctas."
                ),
                "interpretacion": [
                    {
                        "rango": "Se muestra junto al valor de referencia del nivel (697 ms en fácil, 827 ms en medio, 859 ms en difícil)",
                        "nivel": "Informativo, sin clasificación propia",
                    },
                ],
            },
        ],
        "bibliografia_estado": (
            "Valores de referencia de precisión y tiempo de reacción para 1-back "
            "(91.1%, 697.1 ms), 2-back (83.9%, 827.2 ms) y 3-back (77.0%, 858.9 ms) "
            "provistos por la cátedra. La fuente no incluye una tabla de severidad "
            "Normal/Leve/Moderado/Severo: se deriva comparando la precisión del "
            "paciente contra el valor de referencia del nivel jugado (fácil → "
            "1-back, medio → 2-back, difícil → 3-back, incluso con más de 3 "
            "colores por secuencia, ya que es la referencia más exigente "
            "disponible)."
        ),
    },
    {
        "slug": "tracking",
        "nombre": "Tracking Visomotor",
        "evalua": "Coordinación visomotora, control motor fino y temblor.",
        "funcionamiento": (
            "El paciente controla un cursor con el joystick y debe seguir un "
            "objetivo móvil en pantalla."
        ),
        "variables": [
            "Error promedio",
            "Error máximo",
            "Variabilidad",
            "Tiempo dentro del objetivo",
        ],
        "metricas_detalle": [
            {
                "nombre": "Error promedio",
                "que_mide": "Distancia promedio entre el cursor y el objetivo durante todo el test.",
                "como_se_calcula": "Promedio de la distancia (en píxeles) entre cursor y objetivo, medida muchas veces por segundo.",
                "interpretacion": [
                    {"rango": "Menor a 10 px", "nivel": "Normal"},
                    {"rango": "10 a 20 px", "nivel": "Leve"},
                    {"rango": "20 a 35 px", "nivel": "Moderado"},
                    {"rango": "Mayor a 35 px", "nivel": "Severo"},
                ],
            },
            {
                "nombre": "Error máximo",
                "que_mide": (
                    "La mayor separación observada entre cursor y objetivo en algún "
                    "instante del test (detecta pérdidas bruscas del seguimiento que "
                    "el promedio puede ocultar)."
                ),
                "como_se_calcula": "Distancia (en píxeles) más grande registrada entre cursor y objetivo.",
                "interpretacion": [
                    {"rango": "Menor a 30 px", "nivel": "Normal"},
                    {"rango": "30 a 60 px", "nivel": "Leve"},
                    {"rango": "60 a 100 px", "nivel": "Moderado"},
                    {"rango": "Mayor a 100 px", "nivel": "Severo"},
                ],
            },
            {
                "nombre": "Variabilidad del movimiento",
                "que_mide": (
                    "Qué tan estable es el seguimiento. Valores altos sugieren temblor, "
                    "movimientos correctivos excesivos o falta de control fino."
                ),
                "como_se_calcula": "Desvío estándar de la distancia entre cursor y objetivo a lo largo del test.",
                "interpretacion": [
                    {"rango": "Menor a 5 px", "nivel": "Normal"},
                    {"rango": "5 a 12 px", "nivel": "Leve"},
                    {"rango": "12 a 25 px", "nivel": "Moderado"},
                    {"rango": "Mayor a 25 px", "nivel": "Severo"},
                ],
            },
            {
                "nombre": "Tiempo dentro de la zona objetivo",
                "que_mide": (
                    "Qué porcentaje del tiempo el cursor permaneció dentro de una zona "
                    "de tolerancia de 15 px alrededor del objetivo."
                ),
                "como_se_calcula": "Tiempo con el cursor a 15 px o menos del objetivo, dividido el tiempo total del test.",
                "interpretacion": [
                    {"rango": "Mayor a 90%", "nivel": "Normal"},
                    {"rango": "75% a 90%", "nivel": "Leve"},
                    {"rango": "50% a 75%", "nivel": "Moderado"},
                    {"rango": "Menor a 50%", "nivel": "Severo"},
                ],
            },
            {
                "nombre": "Clasificación global (score combinado)",
                "que_mide": "Un resumen único de las 4 métricas anteriores, para tener una sola lectura rápida.",
                "como_se_calcula": (
                    "Cada una de las 4 métricas anteriores suma puntos según su nivel "
                    "(Normal=0, Leve=1, Moderado=2, Severo=3); se suman los 4 puntajes "
                    "(rango total: 0 a 12)."
                ),
                "interpretacion": [
                    {"rango": "0 a 2 puntos", "nivel": "Normal"},
                    {"rango": "3 a 5 puntos", "nivel": "Leve"},
                    {"rango": "6 a 8 puntos", "nivel": "Moderado"},
                    {"rango": "9 a 12 puntos", "nivel": "Severo"},
                ],
            },
        ],
        "hardware": "Joystick (streaming continuo de alta frecuencia).",
        "bibliografia_estado": (
            "Umbrales de error, variabilidad y tiempo en zona definidos para este "
            "sistema; score global combina las 4 métricas en una sola clasificación."
        ),
    },
    {
        "slug": "laberinto",
        "nombre": "Laberinto con Acelerómetro",
        "evalua": "Coordinación visomotora, estabilidad motora y control fino.",
        "funcionamiento": (
            "El paciente inclina toda la consola; el acelerómetro interno "
            "controla una bolita dentro de un laberinto virtual."
        ),
        "variables": [
            "Tiempo total",
            "Colisiones",
            "Desviación",
            "Movimientos bruscos",
            "Precisión",
        ],
        "metricas_detalle": [
            {
                "nombre": "Tiempo total para completar el laberinto",
                "que_mide": "Cuánto tarda el paciente en llegar desde el inicio hasta la meta, comparado con un tiempo ideal de referencia.",
                "como_se_calcula": "Tiempo del paciente dividido el tiempo ideal del recorrido, expresado como porcentaje.",
                "interpretacion": [
                    {"rango": "Menor a 120%", "nivel": "Normal"},
                    {"rango": "120% a 150%", "nivel": "Leve"},
                    {"rango": "150% a 200%", "nivel": "Moderado"},
                    {"rango": "Mayor a 200%", "nivel": "Severo"},
                ],
            },
            {
                "nombre": "Cantidad de choques contra paredes",
                "que_mide": "Cuántas veces la bolita tocó una pared del laberinto.",
                "como_se_calcula": "Conteo directo de colisiones detectadas durante el recorrido.",
                "interpretacion": [
                    {"rango": "0 a 2", "nivel": "Normal"},
                    {"rango": "3 a 5", "nivel": "Leve"},
                    {"rango": "6 a 10", "nivel": "Moderado"},
                    {"rango": "Mayor a 10", "nivel": "Severo"},
                ],
            },
            {
                "nombre": "Desviación respecto a la trayectoria ideal",
                "que_mide": "Cuánto más largo fue el camino que recorrió la bolita, comparado con el camino más corto posible.",
                "como_se_calcula": "Distancia total recorrida por la bolita dividida la distancia del camino ideal.",
                "interpretacion": [
                    {"rango": "Menor a 1,2", "nivel": "Normal"},
                    {"rango": "1,2 a 1,5", "nivel": "Leve"},
                    {"rango": "1,5 a 2,0", "nivel": "Moderado"},
                    {"rango": "Mayor a 2,0", "nivel": "Severo"},
                ],
            },
            {
                "nombre": "Movimientos bruscos o inestables",
                "que_mide": "Cantidad de cambios repentinos en la inclinación del control, asociados a temblor o falta de control fino.",
                "como_se_calcula": "Conteo de cambios abruptos en la inclinación detectada entre instantes consecutivos.",
                "interpretacion": [
                    {"rango": "0 a 5", "nivel": "Normal"},
                    {"rango": "6 a 15", "nivel": "Leve"},
                    {"rango": "16 a 30", "nivel": "Moderado"},
                    {"rango": "Mayor a 30", "nivel": "Severo"},
                ],
            },
            {
                "nombre": "Precisión del control",
                "que_mide": "Qué porcentaje del recorrido se hizo sin tocar ninguna pared.",
                "como_se_calcula": "Tiempo sin contacto con paredes dividido el tiempo total del recorrido, expresado como porcentaje.",
                "interpretacion": [
                    {"rango": "Mayor a 90%", "nivel": "Normal"},
                    {"rango": "75% a 90%", "nivel": "Leve"},
                    {"rango": "50% a 75%", "nivel": "Moderado"},
                    {"rango": "Menor a 50%", "nivel": "Severo"},
                ],
            },
        ],
        "hardware": "Acelerómetro ADXL345 (streaming continuo).",
        "bibliografia_estado": (
            "Inspirado en escalas funcionales usadas en rehabilitación post-ACV "
            "(Fugl-Meyer Assessment, Wolf Motor Function Test, Box and Block Test, "
            "Nine Hole Peg Test); umbrales propios definidos para este sistema."
        ),
    },
]


# -----------------------------------------------------------------------------
# 3b. Forma esperada de los datos que manda el navegador (FastAPI los valida
#     automáticamente: si falta un campo, devuelve un error solo).
# -----------------------------------------------------------------------------

class LoginRequest(BaseModel):
    usuario: str
    password: str


class RegistroRequest(BaseModel):
    usuario: str
    password: str
    confirmar_password: str
    nombre: str


class PacienteRequest(BaseModel):
    id: str
    nombre: str
    apellido: str
    fecha_nacimiento: str | None = None
    comentarios: str | None = None


class ResultadoDetalleItem(BaseModel):
    numero_estimulo: int
    estimulo: str
    respuesta: str | None = None
    correcto: bool
    tipo_error: str | None = None
    rt_ms: int | None = None


class ResultadoRequest(BaseModel):
    paciente_id: int
    test_slug: str
    parametros: dict
    metricas: dict
    detalle: list[ResultadoDetalleItem]
    comentarios_medico: str | None = None


# -----------------------------------------------------------------------------
# 3c. Puente con el dispositivo (ESP32): UDP <-> WebSocket/HTTP.
#
# Dirección ESP32 -> backend -> navegador (eventos, ej. botones):
# el ESP32 manda eventos por UDP (ver firmware/src/main.cpp). Este bloque
# escucha esos paquetes y los reenvía, tal cual llegan, a todos los
# navegadores conectados por WebSocket a /ws/dispositivo. Así un test como
# Stroop puede reaccionar a un botón físico exactamente igual que reacciona
# a un click o una tecla (mismo handler, otra fuente de eventos).
#
# Dirección backend -> ESP32 (comandos, ej. prender un LED puntual):
# no hay una IP del ESP32 configurada a mano en el backend. En cambio, cada
# vez que llega un paquete UDP del ESP32 guardamos de qué dirección vino
# (`direccion_esp32`); para mandarle un comando, el backend reusa ese mismo
# socket UDP (el `transport`) y le contesta a esa dirección. El ESP32 avisa
# su dirección apenas se conecta al WiFi (manda "ESP32_ONLINE"), así que no
# hace falta esperar a que alguien apriete un botón físico primero.
# -----------------------------------------------------------------------------

PUERTO_UDP_DISPOSITIVO = 4210

conexiones_websocket: list[WebSocket] = []

transporte_udp_dispositivo: asyncio.DatagramTransport | None = None
direccion_esp32: tuple[str, int] | None = None


async def avisar_a_navegadores(mensaje: str) -> None:
    for ws in list(conexiones_websocket):
        try:
            await ws.send_text(mensaje)
        except Exception:
            pass


class _ProtocoloUDPDispositivo(asyncio.DatagramProtocol):
    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        global transporte_udp_dispositivo
        transporte_udp_dispositivo = transport

    def datagram_received(self, data: bytes, addr) -> None:
        global direccion_esp32
        direccion_esp32 = addr
        mensaje = data.decode("utf-8", errors="replace")
        asyncio.create_task(avisar_a_navegadores(mensaje))


async def iniciar_escucha_udp() -> None:
    loop = asyncio.get_event_loop()
    await loop.create_datagram_endpoint(
        _ProtocoloUDPDispositivo,
        local_addr=("0.0.0.0", PUERTO_UDP_DISPOSITIVO),
    )


class ComandoDispositivoRequest(BaseModel):
    comando: str


# -----------------------------------------------------------------------------
# 4. El servidor en sí: arranca, atiende pedidos, sirve el frontend.
# -----------------------------------------------------------------------------

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="NeuroRehab Platform")


@app.on_event("startup")
async def al_arrancar() -> None:
    inicializar_db()
    asyncio.create_task(iniciar_escucha_udp())


@app.websocket("/ws/dispositivo")
async def websocket_dispositivo(websocket: WebSocket) -> None:
    await websocket.accept()
    conexiones_websocket.append(websocket)
    try:
        while True:
            # No esperamos nada del navegador; solo mantenemos la conexión
            # abierta para poder mandarle avisos cuando llegue algo por UDP.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        conexiones_websocket.remove(websocket)


@app.post("/api/dispositivo/comando")
def enviar_comando_dispositivo(datos: ComandoDispositivoRequest):
    if transporte_udp_dispositivo is None or direccion_esp32 is None:
        raise HTTPException(
            503,
            "Todavía no se recibió ningún mensaje del ESP32: no se conoce su dirección en la red.",
        )
    transporte_udp_dispositivo.sendto(datos.comando.encode("utf-8"), direccion_esp32)
    return {
        "ok": True,
        "comando": datos.comando,
        "destino": f"{direccion_esp32[0]}:{direccion_esp32[1]}",
    }


@app.post("/api/auth/login")
def login(datos: LoginRequest):
    usuario = datos.usuario.strip()
    if not usuario or not datos.password:
        raise HTTPException(400, "Usuario y contraseña son obligatorios.")
    if any(caracter.isspace() for caracter in usuario):
        raise HTTPException(400, "El usuario no puede contener espacios.")

    # El usuario se guarda en minúsculas, así que comparamos en minúsculas:
    # "Luana" y "luana" tienen que ser el mismo usuario.
    usuario_normalizado = usuario.lower()

    conexion = conectar_db()
    fila = conexion.execute("SELECT * FROM medicos WHERE usuario = ?", (usuario_normalizado,)).fetchone()
    conexion.close()

    if fila is None:
        raise HTTPException(404, "El usuario no existe.")
    if not password_es_correcta(datos.password, fila["password_hash"]):
        raise HTTPException(401, "Contraseña incorrecta.")

    return {"id": fila["id"], "usuario": fila["usuario"], "nombre": fila["nombre"]}


@app.post("/api/auth/registro", status_code=201)
def registro(datos: RegistroRequest):
    usuario = datos.usuario.strip()
    nombre = datos.nombre.strip()

    if not usuario or not datos.password or not nombre:
        raise HTTPException(400, "Todos los campos son obligatorios.")
    if any(caracter.isspace() for caracter in usuario):
        raise HTTPException(400, "El usuario no puede contener espacios.")
    if datos.password != datos.confirmar_password:
        raise HTTPException(400, "Las contraseñas no coinciden.")

    usuario_normalizado = usuario.lower()

    conexion = conectar_db()
    existente = conexion.execute("SELECT id FROM medicos WHERE usuario = ?", (usuario_normalizado,)).fetchone()
    if existente is not None:
        conexion.close()
        raise HTTPException(409, "Ese usuario ya existe.")

    cursor = conexion.execute(
        "INSERT INTO medicos (usuario, password_hash, nombre) VALUES (?, ?, ?)",
        (usuario_normalizado, hashear_password(datos.password), nombre),
    )
    conexion.commit()
    medico_id = cursor.lastrowid
    conexion.close()

    return {"id": medico_id, "usuario": usuario_normalizado, "nombre": nombre}


@app.get("/api/tests")
def listar_tests():
    return TESTS


@app.get("/api/tests/{slug}")
def obtener_test(slug: str):
    for test in TESTS:
        if test["slug"] == slug:
            return test
    raise HTTPException(404, "Test no encontrado.")


@app.post("/api/pacientes", status_code=201)
def crear_paciente(datos: PacienteRequest):
    id_texto = datos.id.strip()
    nombre = datos.nombre.strip()
    apellido = datos.apellido.strip()

    if not id_texto or not id_texto.isdigit():
        raise HTTPException(400, "El ID del paciente es obligatorio y debe ser numérico.")
    if not nombre or not apellido:
        raise HTTPException(400, "Nombre y apellido son obligatorios.")

    paciente_id = int(id_texto)

    conexion = conectar_db()
    existente = conexion.execute("SELECT id FROM pacientes WHERE id = ?", (paciente_id,)).fetchone()
    if existente is not None:
        conexion.close()
        raise HTTPException(409, "Ya existe un paciente con ese ID.")

    # Mismo nombre y apellido pero con otro ID: probablemente es la misma
    # persona, así que avisamos en vez de crear un duplicado. La comparación
    # no distingue mayúsculas/minúsculas ("Juan" y "juan" son lo mismo).
    for fila in conexion.execute("SELECT id, nombre, apellido FROM pacientes").fetchall():
        if fila["nombre"].lower() == nombre.lower() and fila["apellido"].lower() == apellido.lower():
            conexion.close()
            raise HTTPException(
                409, f"Ya existe un paciente con ese nombre y apellido, con el ID {fila['id']}."
            )

    conexion.execute(
        "INSERT INTO pacientes (id, nombre, apellido, fecha_nacimiento, comentarios) VALUES (?, ?, ?, ?, ?)",
        (paciente_id, nombre, apellido, datos.fecha_nacimiento, datos.comentarios),
    )
    conexion.commit()
    conexion.close()

    return {
        "id": paciente_id,
        "nombre": nombre,
        "apellido": apellido,
        "fecha_nacimiento": datos.fecha_nacimiento,
        "comentarios": datos.comentarios,
    }


@app.get("/api/pacientes")
def listar_pacientes(buscar: str = ""):
    conexion = conectar_db()
    filas = conexion.execute("SELECT * FROM pacientes ORDER BY apellido, nombre").fetchall()
    conexion.close()

    # El filtro se hace en Python (no con LIKE de SQL) para que la búsqueda
    # no distinga mayúsculas/minúsculas ni se confunda con acentos.
    pacientes = [dict(fila) for fila in filas]
    palabras = buscar.strip().lower().split()
    if not palabras:
        return pacientes

    # Cada palabra escrita tiene que aparecer en algún lado (nombre, apellido
    # o ID) para que el paciente cuente como resultado. Así "Marina Lopez"
    # encuentra al paciente aunque "nombre" y "apellido" sean campos separados.
    resultado = []
    for p in pacientes:
        texto_paciente = f"{p['nombre']} {p['apellido']} {p['id']}".lower()
        if all(palabra in texto_paciente for palabra in palabras):
            resultado.append(p)
    return resultado


@app.get("/api/pacientes/{paciente_id}")
def obtener_paciente(paciente_id: str):
    if not paciente_id.isdigit():
        raise HTTPException(404, "Paciente no encontrado.")

    conexion = conectar_db()
    fila = conexion.execute("SELECT * FROM pacientes WHERE id = ?", (int(paciente_id),)).fetchone()
    conexion.close()

    if fila is None:
        raise HTTPException(404, "Paciente no encontrado.")

    return dict(fila)


@app.post("/api/resultados", status_code=201)
def guardar_resultado(datos: ResultadoRequest):
    conexion = conectar_db()

    paciente = conexion.execute(
        "SELECT id FROM pacientes WHERE id = ?", (datos.paciente_id,)
    ).fetchone()
    if paciente is None:
        conexion.close()
        raise HTTPException(400, "El paciente indicado no existe.")

    ahora = datetime.now()
    cursor = conexion.execute(
        """
        INSERT INTO resultados
            (paciente_id, test_slug, fecha, hora, parametros_json, metricas_json, comentarios_medico)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datos.paciente_id,
            datos.test_slug,
            ahora.strftime("%Y-%m-%d"),
            ahora.strftime("%H:%M"),
            json.dumps(datos.parametros, ensure_ascii=False),
            json.dumps(datos.metricas, ensure_ascii=False),
            datos.comentarios_medico,
        ),
    )
    resultado_id = cursor.lastrowid

    for item in datos.detalle:
        conexion.execute(
            """
            INSERT INTO resultados_detalle
                (resultado_id, numero_estimulo, estimulo, respuesta, correcto, tipo_error, rt_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                resultado_id,
                item.numero_estimulo,
                item.estimulo,
                item.respuesta,
                1 if item.correcto else 0,
                item.tipo_error,
                item.rt_ms,
            ),
        )

    conexion.commit()
    conexion.close()

    return {"id": resultado_id}


def _resultado_con_json_decodificado(fila) -> dict:
    resultado = dict(fila)
    resultado["parametros"] = json.loads(resultado.pop("parametros_json"))
    resultado["metricas"] = json.loads(resultado.pop("metricas_json"))
    return resultado


@app.get("/api/resultados")
def listar_resultados(paciente_id: int):
    conexion = conectar_db()
    filas = conexion.execute(
        "SELECT * FROM resultados WHERE paciente_id = ? ORDER BY fecha DESC, hora DESC, id DESC",
        (paciente_id,),
    ).fetchall()
    conexion.close()

    return [_resultado_con_json_decodificado(fila) for fila in filas]


@app.get("/api/resultados/{resultado_id}")
def obtener_resultado(resultado_id: int):
    conexion = conectar_db()
    fila = conexion.execute("SELECT * FROM resultados WHERE id = ?", (resultado_id,)).fetchone()
    if fila is None:
        conexion.close()
        raise HTTPException(404, "Resultado no encontrado.")

    detalle_filas = conexion.execute(
        "SELECT * FROM resultados_detalle WHERE resultado_id = ? ORDER BY numero_estimulo",
        (resultado_id,),
    ).fetchall()
    conexion.close()

    resultado = _resultado_con_json_decodificado(fila)
    resultado["detalle"] = [dict(d) for d in detalle_filas]
    return resultado


@app.delete("/api/resultados/{resultado_id}", status_code=204)
def eliminar_resultado(resultado_id: int):
    conexion = conectar_db()
    existente = conexion.execute("SELECT id FROM resultados WHERE id = ?", (resultado_id,)).fetchone()
    if existente is None:
        conexion.close()
        raise HTTPException(404, "Resultado no encontrado.")

    conexion.execute("DELETE FROM resultados_detalle WHERE resultado_id = ?", (resultado_id,))
    conexion.execute("DELETE FROM resultados WHERE id = ?", (resultado_id,))
    conexion.commit()
    conexion.close()


@app.delete("/api/resultados", status_code=204)
def eliminar_historial_paciente(paciente_id: int):
    conexion = conectar_db()
    conexion.execute(
        "DELETE FROM resultados_detalle WHERE resultado_id IN (SELECT id FROM resultados WHERE paciente_id = ?)",
        (paciente_id,),
    )
    conexion.execute("DELETE FROM resultados WHERE paciente_id = ?", (paciente_id,))
    conexion.commit()
    conexion.close()


@app.delete("/api/pacientes/{paciente_id}", status_code=204)
def eliminar_paciente(paciente_id: int):
    conexion = conectar_db()
    existente = conexion.execute("SELECT id FROM pacientes WHERE id = ?", (paciente_id,)).fetchone()
    if existente is None:
        conexion.close()
        raise HTTPException(404, "Paciente no encontrado.")

    # Borra primero el historial de tests del paciente (detalle y resultados)
    # y recién después al paciente, para no dejar filas huérfanas.
    conexion.execute(
        "DELETE FROM resultados_detalle WHERE resultado_id IN (SELECT id FROM resultados WHERE paciente_id = ?)",
        (paciente_id,),
    )
    conexion.execute("DELETE FROM resultados WHERE paciente_id = ?", (paciente_id,))
    conexion.execute("DELETE FROM pacientes WHERE id = ?", (paciente_id,))
    conexion.commit()
    conexion.close()


# Esto va al final a propósito: cualquier dirección que no sea /api/algo se
# busca como archivo dentro de frontend/ (así se sirven las páginas web).
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
