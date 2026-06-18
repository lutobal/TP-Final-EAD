# NeuroRehab Platform — Documento Maestro de Especificación Funcional y Técnica

**Proyecto final — Electrónica Analógica y Digital orientada a Bioingeniería**
**Versión:** 1.0 — Documento base para desarrollo con Claude Code en Visual Studio Code

---

## 0. Propósito de este documento

Este archivo es la especificación funcional y técnica completa del proyecto. Está pensado para
usarse como contexto de referencia durante el desarrollo asistido con Claude Code: describe la
arquitectura completa, las decisiones de diseño, los riesgos identificados, las mejoras propuestas
y el detalle de cada pantalla, test y flujo. No contiene código de implementación; ese es un paso
posterior.

El documento se basa en dos fuentes:

1. El brief original del proyecto (descripción funcional entregada por el usuario).
2. El análisis de `main.py`, un prototipo previo en Python/Pygame que implementa una versión de
   escritorio de tres de los tests cognitivos. La sección 2 detalla qué se reutiliza de ese
   prototipo (conceptos de UX, lógica clínica, métricas) y qué **no** se reutiliza (el código en sí,
   ya que el stack es completamente distinto).

---

## 1. Resumen del sistema

NeuroRehab Platform es una plataforma de evaluación cognitivo-motora y exploración visual para
pacientes en rehabilitación neurológica, principalmente post-ACV (accidente cerebrovascular).
Combina:

- Una **consola física basada en ESP32** que actúa exclusivamente como periférico de entrada/salida
  (lee sensores y controles, da feedback en OLED/buzzer, y transmite eventos por red).
- Una **aplicación web** usada por médicos/terapeutas, con apariencia de software clínico
  profesional, que contiene toda la lógica de los tests, la gestión de pacientes y el historial de
  resultados.

El sistema debe percibirse como una herramienta clínica real, no como un prototipo académico,
tanto en diseño visual como en robustez de los flujos (validaciones, persistencia, manejo de
errores).

---

## 2. Código existente analizado (`main.py`) — qué se aprovecha y qué no

`main.py` es una aplicación de escritorio en **Python + Pygame** (no web, sin red, sin base de
datos, ejecución en pantalla completa a 60 FPS) que implementa un menú de áreas de rehabilitación
(solo el área "Cognición y Lenguaje" está activa) con tres tests funcionando: **Memoria N-Back**,
**Efecto Stroop** y **Secuenciación AVD** (este último, "Actividades de la Vida Diaria", no figura
en el brief del proyecto nuevo — ver nota al final de esta sección).

### 2.1 Qué se reutiliza (conceptos, no código)

**a) Patrón de pantallas de instrucciones tipo carrusel.**
Cada test tiene una clase `Instrucciones<Test>` con una lista `SLIDES` de 5 a 7 pasos, cada uno
con título corto, 2-3 líneas de texto y una ilustración simple dibujada a medida (figuras
geométricas, no imágenes). Incluye barra de progreso, botones Anterior/Siguiente y un botón
"Saltear". Este patrón responde exactamente al requisito del brief de evitar bloques largos de
texto y dar una experiencia "tipo videojuego o aplicación educativa". Se recomienda **reproducir
esta estructura de datos** (slide = título + líneas + ayuda visual) para los 5 tests nuevos.

**b) Patrón de pausa con tres opciones.**
Durante un test, un botón de pausa abre un menú con exactamente tres acciones: *Reanudar*,
*Reiniciar* y *Volver al menú*. El cronómetro descuenta el tiempo en pausa (se acumula
`t_pausa_acum` y se resta del tiempo transcurrido). Esto coincide con lo que pide el brief
("al pausar aparecen tres opciones") y es un patrón a preservar tal cual en la versión web.

**c) Medición rigurosa de tiempos de reacción.**
El prototipo mide el tiempo de reacción (RT) desde el instante exacto en que aparece el estímulo
(no desde un evento separado), usando un reloj monótono (`pygame.time.get_ticks()`), y descuenta
explícitamente cualquier tiempo en pausa ocurrido durante la medición. Esta disciplina de timing es
crítica para tests como Stroop y N-Back, y debe trasladarse al diseño de la nueva plataforma
(sección 9.4 explica cómo, dado que ahora hay una capa de red de por medio).

**d) Lógica y umbrales clínicos ya validados para dos de los tests.**
El prototipo no solo calcula métricas crudas, sino que las clasifica clínicamente contra rangos de
bibliografía:

| Test | Variable clasificada | Umbrales | Fuente citada en el código |
|---|---|---|---|
| N-Back 1 | Precisión | Normal ≥85%, Limítrofe ≥75%, Patológico <75% | Kane et al. (2007) |
| N-Back 2 | Precisión | Normal ≥75%, Limítrofe ≥65%, Patológico <65% | Owen et al. (2005) |
| N-Back 3 | Precisión | Normal ≥65%, Limítrofe ≥55%, Patológico <55% | Vermeij et al. (2012) |
| Stroop fácil (congruente) | Precisión | Normal ≥98%, Limítrofe ≥96%, Patológico <96% | Brysbaert & Stevens (2018) |
| Stroop intermedio/difícil | Precisión | Normal ≥90%, Limítrofe ≥80%, Patológico <80% | Brysbaert & Stevens (2018) |
| Stroop (interferencia) | RT incongruente − RT congruente | Normal 150–350 ms en adultos sanos | MacLeod (1991) |
| AVD (no está en el brief nuevo) | Precisión de secuenciación | Normal ≥80%, Limítrofe ≥60%, Patológico <60% | Baum et al. (2008), EFPT |

Estos umbrales y citas se trasladan directamente al diseño clínico de los tests homólogos del
nuevo sistema (N-Back espacial y Stroop). Para los tres tests sin antecedente en el código
(Exploración de Faro, Tracking visomotor, Laberinto con acelerómetro) **no hay rango clínico
bibliográfico definido todavía**; queda como tarea pendiente (sección 11.3) buscar o definir esos
rangos antes de mostrarlos como "normal/limítrofe/patológico" en el informe del médico.

**e) Esquema de guardado de resultados (a adaptar, no a copiar literal).**
Cada intento se guarda como un diccionario con: paciente, ID, fecha, hora, test, resultados
resumidos, detalle por ensayo, guía de interpretación de errores para el terapeuta, y
opcionalmente observaciones clínicas. Los intentos de un mismo paciente se acumulan en una lista
(historial) en un único archivo nombrado `{id}_{nombre_normalizado}.json`. Este modelo conceptual
(un registro por intento, con resumen + detalle + observaciones, agrupado por paciente) es el que
se traslada a la base de datos relacional de la nueva plataforma (sección 7), aunque la
implementación cambia de "un JSON decorativo por paciente" a tablas normalizadas, ya que el
formato actual no es consultable ni escalable (no permite filtrar, ordenar ni hacer reportes sin
parsear texto).

**f) Validación de pacientes.**
El formulario de alta de paciente valida: nombre vacío, ID vacío, ID no numérico, y — el punto más
relevante — que un ID no quede asignado a dos nombres distintos (evita mezclar resultados de dos
pacientes en el mismo archivo). Esta misma regla de integridad (un ID de paciente es único) se
traslada como constraint de base de datos en el diseño nuevo.

**g) Flujo de fin de test: guardar / descartar / agregar observación.**
Al terminar un test, el médico puede guardar el resultado, descartarlo (no se persiste) o abrir un
panel para escribir una observación clínica que se adjunta al intento antes de guardarlo. Este
flujo coincide exactamente con lo pedido en el brief ("Guardar resultado", "Agregar comentario
clínico", "Descartar resultado") y se preserva como está.

### 2.2 Qué NO se reutiliza

- **El código en sí.** Está escrito en Python/Pygame para escritorio, con un loop de renderizado a
  60 FPS y dibujo manual de cada pantalla. El proyecto nuevo es 100% web (HTML/CSS/JS), por lo que
  no hay una migración directa posible; sirve solo como referencia de comportamiento.
- **El modelo de un solo proceso sin red.** El prototipo no tiene concepto de cliente/servidor,
  base de datos, login ni multiusuario. Toda la capa de autenticación, sesión de médico/paciente,
  navegación libre por home, gestión de pacientes con historial buscable, barra superior con
  estado del dispositivo y menú hamburguesa **es enteramente nueva** y no tiene antecedente en
  `main.py`.
- **El test de Secuenciación AVD.** Está implementado en el prototipo, pero queda **fuera del
  alcance del proyecto**: el usuario confirmó que los únicos tests a desarrollar son los 5
  definidos en el brief (Faro, Stroop, N-Back, Tracking, Laberinto). El cambio de set de tests
  entre el prototipo y el brief nuevo (se agregaron Faro, Tracking y Laberinto; se quitó AVD) es
  una decisión de diseño deliberada del usuario, no un olvido.
- **Los tres tests sin entrada/salida hardware.** Ninguno de los tests del prototipo usa joystick,
  encoder, acelerómetro ni botones físicos: todo es mouse/teclado. La integración con la consola
  ESP32 (sección 6 y 9) es enteramente nueva.

---

## 3. Arquitectura general

```
┌─────────────────────┐        UDP (WiFi)        ┌───────────────────────────┐
│   Consola física      │ ───────────────────────▶ │   Backend / Bridge          │
│   (ESP32)             │ ◀─────────────────────── │   (Python o Node.js)        │
│                        │      (opcional: ack)      │                              │
│  - Joystick + pulsador │                           │  - Listener UDP             │
│  - 4 botones + LEDs    │                           │  - Deduplicación por ID     │
│  - Encoder rotativo    │                           │  - API REST / WebSocket     │
│  - OLED                │                           │  - Lógica de negocio        │
│  - Buzzer              │                           │  - Persistencia (SQLite)    │
│  - Acelerómetro ADXL345│                           └──────────────┬────────────-─┘
│  - Batería             │                                          │ WebSocket / HTTP
└─────────────────────┘                                          ▼
                                                       ┌───────────────────────────┐
                                                       │   Frontend web (navegador) │
                                                       │   HTML + CSS + JS           │
                                                       │   - UI clínica               │
                                                       │   - Lógica de los tests      │
                                                       │   - Render OLED-mirror (web) │
                                                       └───────────────────────────┘
```

Esta arquitectura introduce un componente que **no estaba en el brief original pero es
imprescindible**: un backend/bridge entre el ESP32 y el navegador. La justificación está en la
sección 4 (problema técnico #1). El backend cumple tres roles a la vez: puente UDP↔web,
servidor de la lógica de persistencia, y API para el frontend. Esto evita levantar tres procesos
separados y es coherente con "evitar servicios externos" pedido en el brief.

---

## 4. Problemas técnicos identificados

### 4.1 Un navegador no puede recibir UDP directamente (crítico)

La especificación pide que la comunicación sea por WiFi/UDP y prohíbe explícitamente TCP y
WebSockets para esa comunicación. Sin embargo, **JavaScript en el navegador no tiene acceso a
sockets UDP crudos** por razones de seguridad del sandbox web; esto es una limitación de la
plataforma, no una opción de diseño. Es imposible que un frontend HTML/CSS/JS "puro" reciba
paquetes UDP del ESP32 sin intermediarios.

**Resolución propuesta:** la restricción de UDP (y la prohibición de TCP/WebSockets) aplica al
enlace **ESP32 ↔ PC**, que es el tramo que el profesor pidió evaluar explícitamente como parte de
la materia de electrónica. Ese tramo se implementa en UDP puro, tal como se pidió. El tramo
**backend ↔ navegador** (dentro de la misma PC, o LAN) es un problema de software estándar y no
está cubierto por esa restricción; ahí se recomienda WebSocket (latencia mínima, bidireccional) o,
si se prefiere minimalismo, Server-Sent Events para eventos unidireccionales del dispositivo hacia
la UI. Esto debe confirmarse explícitamente con el profesor para evitar malentendidos, pero es la
única arquitectura técnicamente viable dado el requisito de frontend 100% web.

### 4.2 SQLite no es accesible directamente desde JavaScript de navegador

Un frontend que corre en el navegador no puede leer ni escribir un archivo `.sqlite` en disco por
sí mismo (de nuevo, restricción del sandbox del navegador, no del lenguaje). Hay tres caminos:

1. **Backend con SQLite real** (recomendado): el mismo proceso que actúa de bridge UDP expone una
   API (REST y/o WebSocket) y persiste en SQLite. Es robusto, evita servicios externos, y permite
   más adelante backups simples (un solo archivo `.db`).
2. **SQLite compilado a WebAssembly (`sql.js`) corriendo en el navegador**, persistiendo a
   IndexedDB. Evita tener backend, pero no resuelve el problema 4.1 (igual se necesita un proceso
   intermedio para el UDP), así que en este proyecto no aporta una simplificación real.
3. **JSON persistente** (como hace el prototipo actual) servido también por un backend mínimo.
   Más simple de implementar, pero no escala bien para consultas de historial con filtros
   (buscar paciente, ordenar por fecha, borrar un intento puntual), que el brief sí pide.

**Recomendación:** opción 1. El mismo backend que resuelve 4.1 resuelve esto sin agregar
infraestructura adicional ("evitar servicios externos" sigue cumplido: todo corre local).

### 4.3 Deduplicación de eventos UDP por ID: diseño insuficientemente especificado

El brief indica que el ESP32 reenvía el mismo evento varias veces y que la app debe descartar
duplicados por ID, pero no define cómo se genera ese ID (¿correlativo por botón? ¿global? ¿se
reinicia al reiniciar el ESP32?) ni durante cuánto tiempo hay que recordar IDs ya vistos.

**Recomendación:** usar un contador global monótono por sesión de dispositivo (incrementado en
cada evento, sin reiniciarse entre botones distintos) y mantener en el backend una ventana
deslizante de los últimos N IDs vistos (por ejemplo, los últimos 50, suficiente para cubrir
reenvíos de ráfaga) en lugar de guardar todos los IDs históricos. Si el ESP32 se reinicia, conviene
emitir un evento de "handshake"/`boot_id` para que el backend sepa que el contador volvió a cero y
no descarte erróneamente eventos nuevos con IDs bajos.

### 4.4 Precisión de tiempos de reacción a través de la red

A diferencia del prototipo (todo en un solo proceso, mismo reloj), en la versión web el estímulo se
muestra en el navegador y la respuesta puede llegar por dos vías distintas: clic en pantalla
(mismo reloj que el estímulo) o botón físico vía ESP32→UDP→backend→WebSocket→navegador (con
latencia de red variable). Si no se diseña con cuidado, el tiempo de reacción medido para
respuestas físicas quedará inflado por la latencia de la cadena de transmisión, lo que invalida la
comparación con los rangos clínicos de la sección 2.1.

**Recomendación:** el ESP32 debe timestampear el evento en el momento exacto de la pulsación
(ya lo hace, ver el campo `time` del ejemplo del brief) y el backend/frontend deben calcular el RT
como `timestamp_evento_dispositivo − timestamp_inicio_estimulo`, ambos en el dominio de tiempo del
backend (que es quien también dispara el inicio del estímulo o se sincroniza con el frontend vía
WebSocket). Esto requiere sincronizar el reloj del ESP32 con el del backend al conectar (un simple
intercambio de "ping" para estimar el offset es suficiente para esta aplicación, no se necesita
NTP de precisión militar).

### 4.5 Falta de especificación de qué pasa si se pierde la conexión

El brief pide mostrar "estado del dispositivo" y "último paquete UDP recibido", pero no define qué
debe pasar con un test en curso si la consola se desconecta a mitad de una prueba (por ejemplo,
durante el test de Tracking visomotor, que depende del joystick en tiempo real). Se recomienda
definir un timeout (p. ej. 2 segundos sin paquetes) que pause automáticamente el test y muestre un
aviso, en lugar de dejarlo correr con datos faltantes.

### 4.6 Ambigüedad en "tracking en tiempo real" sobre una arquitectura basada en eventos

Los botones funcionan bien como eventos discretos (flanco de presión), pero el joystick durante el
test de Tracking visomotor y el acelerómetro durante el Laberinto necesitan **streaming continuo**
de posición, no eventos puntuales. Esto implica una tasa de envío UDP mucho más alta (por ejemplo,
30-60 Hz) que la de los botones, lo cual debe dimensionarse explícitamente (tamaño de paquete,
frecuencia, y si conviene enviar deltas en lugar de posición absoluta) para no saturar la red WiFi
ni el bridge.

---

## 5. Mejoras propuestas (resumen)

| # | Mejora | Justificación |
|---|---|---|
| 1 | Backend único (Python o Node) que actúa de bridge UDP + servidor de API + persistencia SQLite | Resuelve 4.1 y 4.2 sin infraestructura adicional |
| 2 | Ventana deslizante de IDs recientes para deduplicación, no lista histórica completa | Evita crecimiento de memoria indefinido (4.3) |
| 3 | Timestamping en el ESP32 + sincronización de reloj con el backend | Mantiene válidos los rangos clínicos de RT (4.4) |
| 4 | Esquema de base de datos relacional en vez de "JSON decorativo por paciente" | Permite búsquedas, filtros y borrado selectivo del historial, tal como pide el brief |
| 5 | Reutilizar el patrón de carrusel de instrucciones y el menú de pausa de 3 opciones del prototipo | Ya validado en el prototipo, cumple el requisito de UX "tipo videojuego" |
| 6 | Definir timeout de desconexión que pause tests en curso | Evita registrar datos inválidos por pérdida de señal (4.5) |
| 7 | Confirmar con el profesor el alcance exacto de la restricción UDP (solo tramo ESP32↔PC) | Evita un bloqueo de diseño irresoluble (4.1) |
| 8 | Buscar bibliografía de rangos clínicos para Faro, Tracking y Laberinto (no existen en el prototipo) | Los 3 tests nuevos no tienen aún clasificación clínica definida |
| 9 | Excluir la Secuenciación AVD del alcance (confirmado por el usuario) | El set de tests final es el de los 5 del brief; AVD no se implementa |

---

## 6. Hardware

### 6.1 Componentes de la consola

- ESP32 (controlador principal)
- Joystick analógico tipo PlayStation, con pulsador integrado
- 4 botones arcade de 30 mm (rojo, verde, azul, amarillo), cada uno con un LED individual encima
- Encoder rotativo
- Display OLED
- Buzzer
- Acelerómetro ADXL345, integrado dentro de la carcasa (oculto, detecta inclinación del dispositivo
  completo, no es un joystick adicional)
- Batería interna

### 6.2 Diseño físico

Consola rectangular con dos manijas laterales para sostener con ambas manos. Distribución:

- OLED: arriba al centro
- Encoder: arriba a la derecha
- Buzzer: arriba a la izquierda
- 4 botones de colores: alineados horizontalmente, parte inferior izquierda
- Joystick: parte inferior derecha
- Acelerómetro: oculto dentro de la carcasa

### 6.3 Rol del ESP32

El ESP32 **no ejecuta lógica de tests**. Únicamente:

- Lee joystick (posición analógica + pulsador)
- Lee botones (con detección de flanco)
- Lee encoder (incrementos/decrementos)
- Lee acelerómetro
- Controla OLED (feedback resumido, no reemplaza la interfaz principal)
- Controla buzzer
- Envía eventos por UDP

Toda la lógica de evaluación, puntuación y clasificación clínica corre en el backend/frontend web.

---

## 7. Comunicación y modelo de eventos

### 7.1 Protocolo

WiFi + UDP entre ESP32 y la PC (tramo restringido explícitamente por el profesor; ver 4.1 para la
aclaración sobre el resto de la cadena).

### 7.2 Formato de evento (botones)

Detección de flanco: cada pulsación genera un evento con ID único, timestamp y tipo de evento.

```json
{
  "id": 152,
  "type": "button",
  "button": "red",
  "event": "press",
  "time": 38452
}
```

El ESP32 reenvía el mismo evento varias veces para evitar pérdidas por UDP (protocolo no
confiable); el backend descarta duplicados por `id` (ver 4.3 para el diseño de la ventana de
deduplicación).

### 7.3 Eventos adicionales a definir (no estaban en el brief, surgen del análisis)

Siguiendo el mismo formato, se necesitan tipos de evento análogos para:

- `joystick`: posición analógica (x, y) y estado del pulsador — streaming continuo durante tests
  de tracking/exploración, evento discreto para navegación de menús.
- `encoder`: delta de incremento/decremento, evento discreto.
- `accelerometer`: orientación/inclinación (x, y, z) — streaming continuo durante el test de
  Laberinto.
- `device_status` / `heartbeat`: paquete periódico (p. ej. cada 1 s) con nivel de batería y estado
  de sensores, para alimentar la pantalla de "Estado del dispositivo" del brief.

---

## 8. Modelo de datos (backend)

Reemplaza el esquema de "un JSON por paciente con claves decorativas" del prototipo por tablas
normalizadas, preservando los mismos conceptos de información:

- **medicos**: id, usuario, contraseña (hash simple, ya que el brief aclara que no se requiere
  seguridad real), nombre.
- **pacientes**: id, nombre, apellido, fecha_nacimiento (opcional), comentarios. ID único
  (constraint, igual que la validación del prototipo en 2.1g).
- **tests**: catálogo fijo de los 5 tests con nombre, descripción, qué
  evalúa, variables registradas, duración estimada.
- **resultados**: id, paciente_id, test_id, fecha, hora, parámetros_usados (JSON o columnas según
  el test), métricas_resumen (precisión, clasificación, fuente bibliográfica — igual que el
  prototipo), comentarios_medico.
- **resultados_detalle**: una fila por ensayo/estímulo dentro de un resultado (forma/color o
  palabra/tinta, respuesta, correcto/incorrecto, tipo de error, RT en ms) — replica el nivel de
  detalle que ya guarda el prototipo en `self.respuestas`.

Esta normalización es lo que permite cumplir, sin parsear texto, los requisitos de historial:
buscar pacientes, ver resultados anteriores, eliminar un intento específico o el historial completo
de un paciente.

---

## 9. Aplicación web — flujo y pantallas

### 9.1 Login y sesiones

Pantalla inicial con "Iniciar sesión" / "Registrarse". Sin seguridad real (prototipo académico),
pero con las validaciones pedidas: usuario inexistente, contraseña incorrecta, usuario ya
existente, campos vacíos, contraseñas distintas.

Dos sesiones independientes:

- **Sesión del médico**: se inicia con login, permanece activa mientras se usa la plataforma.
- **Sesión del paciente**: solo se activa cuando se va a ejecutar una prueba. No se solicita
  paciente inmediatamente después del login.

### 9.2 Flujo general

```
Login médico → Home → Navegación libre → (solo al ejecutar una prueba) → Selección de paciente
```

### 9.3 Home del médico

Disponible sin necesidad de paciente activo: ver tests disponibles, leer su descripción, revisar
historiales, buscar pacientes, ver estado del dispositivo, acceder a configuración, iniciar
evaluaciones.

### 9.4 Menú y barra superior

Menú hamburguesa (si la barra superior se sobrecarga) con: Inicio, Tests disponibles, Historial,
Pacientes, Configuración, Estado del dispositivo, Cerrar paciente, Cerrar sesión.

Barra superior: nombre del software, médico logueado, paciente activo (si existe), estado del
dispositivo, menú hamburguesa.

### 9.5 Estado del dispositivo

Pantalla/sección con: ESP32 conectado, OLED OK, Joystick OK, Botones OK, Encoder OK, Acelerómetro
OK, último paquete UDP recibido, nivel de batería. Alimentada por el evento `device_status` de la
sección 7.3.

### 9.6 Página de cada test

Nombre, imagen ilustrativa, qué evalúa, cómo funciona, variables registradas, duración estimada, y
botón "Realizar este test".

### 9.7 Acceso a un test sin paciente activo

Si se presiona "Realizar este test" sin paciente activo: mostrar aviso con opciones Seleccionar
paciente existente / Crear paciente nuevo / Cancelar. Si ya hay paciente activo: ir directo a la
configuración del test.

### 9.8 Pantallas de instrucciones

Carrusel tipo videojuego (ver patrón reutilizable en 2.1a): título breve, texto corto, ayuda visual,
navegación sencilla. Flujo completo de un test: descripción → selección de paciente (si
corresponde) → configuración → instrucciones → test → resultados.

### 9.9 Navegación híbrida (mouse + consola)

| Control | Acción |
|---|---|
| Joystick izquierda | Página anterior |
| Joystick derecha | Página siguiente |
| Joystick arriba/abajo | Navegación por listas |
| Pulsador del joystick | Confirmar / Aceptar / Iniciar / Guardar |
| Botón rojo | Volver / Cancelar / Saltear instrucciones |
| Encoder horario | Aumentar valor |
| Encoder antihorario | Disminuir valor |
| Botones de colores | Respuestas de tests específicos (p. ej. Stroop) |

### 9.10 Configuración de los tests

Selección de cantidad de estímulos, dificultad y duración, principalmente con el encoder. El valor
seleccionado se refleja simultáneamente en la web y en la OLED; se confirma con el pulsador del
joystick.

### 9.11 OLED

No reemplaza la interfaz principal; da feedback resumido (nivel, estímulo actual, cantidad de
estímulos, tiempo restante, aciertos, errores, correcto/incorrecto), variable según el test.

### 9.12 Resultados finales

Al terminar: métricas principales, resumen, gráficos cuando corresponda. Opciones: guardar
resultado, agregar comentario clínico, descartar resultado (si se descarta, no se persiste). Este
flujo replica 1:1 el del prototipo (2.1g).

### 9.13 Historial de pacientes

Buscar pacientes, ver resultados anteriores, fechas, comentarios, métricas; eliminar intentos
específicos o el historial completo de un paciente. Todo accesible sin paciente activo.

### 9.14 Cierre de sesiones

- **Cerrar paciente**: elimina el paciente activo, no afecta la sesión del médico.
- **Cerrar sesión**: cierra la sesión del médico por completo, vuelve al login.

---

## 10. Especificación de los 5 tests

### 10.1 Test 1 — Exploración de Faro

**Evalúa:** exploración visual activa, atención espacial, neglect espacial.
**Funcionamiento:** el paciente controla una linterna con el joystick sobre una pantalla
oscurecida; solo una región circular está iluminada. Debe localizar objetivos ocultos.
**Variables:** tiempo total, tiempo al primer hallazgo, cobertura espacial, omisiones, objetivos
encontrados, trayectoria.
**Hardware usado:** joystick (streaming continuo de posición, ver 4.6 y 7.3).
**Estado de bibliografía clínica:** sin antecedente en el prototipo; pendiente (ver 11.3).

### 10.2 Test 2 — Stroop

**Evalúa:** atención selectiva, control inhibitorio.
**Funcionamiento:** se muestra una palabra de color (ej. "ROJO") escrita en una tinta de color
distinto; el paciente responde con los botones de colores (rojo, verde, azul, amarillo), sin usar
el joystick.
**Variables:** tiempo de reacción, errores, aciertos, efecto Stroop (interferencia).
**Hardware usado:** botones de colores con LED.
**Bibliografía clínica disponible (del prototipo, ver 2.1d):** clasificación de precisión por
nivel de congruencia (Brysbaert & Stevens, 2018) e interferencia normal de 150–350 ms (MacLeod,
1991). Niveles sugeridos, replicando el prototipo: fácil (100% congruente), intermedio (50/50),
difícil (100% incongruente). Tiempo de respuesta ampliado respecto al estándar de adultos sanos
(el prototipo usa 5000 ms en vez de los ~2000 ms estándar, para compensar la lentitud de reacción
post-ACV); se recomienda mantener ese criterio.

### 10.3 Test 3 — N-Back Espacial

**Evalúa:** memoria de trabajo, atención sostenida.
**Funcionamiento:** se presentan secuencias de estímulos; el paciente responde con botones.
Modos: 0-back, 1-back (el brief menciona estos dos; el prototipo implementa 1/2/3-back — confirmar
con el usuario cuál escala de niveles usar en la versión final).
**Variables:** aciertos, errores, tiempo de reacción.
**Hardware usado:** botones (probablemente SI/NO, o dos de los botones de colores).
**Bibliografía clínica disponible (del prototipo, ver 2.1d):** rangos de precisión por nivel
(Kane et al. 2007; Owen et al. 2005; Vermeij et al. 2012), clasificación Normal/Limítrofe/
Patológico, y guía de interpretación de errores de omisión vs. comisión para el terapeuta —
reutilizable casi sin cambios, ajustando los niveles a 0-back/1-back si así se define.

### 10.4 Test 4 — Tracking Visomotor

**Evalúa:** coordinación visomotora, control motor fino, temblor.
**Funcionamiento:** el paciente controla un cursor con el joystick y debe seguir un objetivo móvil.
**Variables:** error promedio, error máximo, variabilidad, tiempo dentro del objetivo.
**Hardware usado:** joystick (streaming continuo de alta frecuencia, ver 4.6).
**Estado de bibliografía clínica:** sin antecedente en el prototipo; pendiente (ver 11.3). Nota de
diseño: a diferencia de Stroop/N-Back (eventos discretos), este test necesita una arquitectura de
muestreo continuo y debe diseñarse la tasa de envío UDP antes de implementar.

### 10.5 Test 5 — Laberinto con Acelerómetro

**Evalúa:** coordinación visomotora, estabilidad motora, control fino.
**Funcionamiento:** el paciente inclina toda la consola; el acelerómetro interno controla una
bolita dentro de un laberinto virtual.
**Variables:** tiempo total, colisiones, desviación, movimientos bruscos, precisión.
**Hardware usado:** acelerómetro ADXL345 (streaming continuo, ver 4.6).
**Estado de bibliografía clínica:** sin antecedente en el prototipo; pendiente (ver 11.3).

El sistema final tiene exactamente estos 5 tests. La Secuenciación AVD del prototipo (sección
2.2) queda fuera del alcance por decisión confirmada del usuario.

---

## 11. Tecnologías y stack

### 11.1 Evaluación de la propuesta inicial del usuario

| Capa | Propuesta inicial | Evaluación |
|---|---|---|
| Frontend | HTML, CSS, JavaScript | Adecuado, sin observaciones |
| Comunicación | UDP | Adecuado solo en el tramo ESP32↔PC (ver 4.1); falta el tramo backend↔frontend |
| Persistencia | SQLite local o equivalente | Adecuado, pero requiere un backend que lo sirva (ver 4.2); no es accesible directamente desde JS de navegador |

### 11.2 Stack recomendado

- **Frontend:** HTML + CSS + JavaScript (vanilla o un framework liviano, a definir según
  preferencia del usuario), consumiendo una API REST para datos y WebSocket para eventos en
  tiempo real del dispositivo.
- **Backend:** un único proceso (Python con FastAPI/Flask, o Node.js con Express) responsable de:
  escuchar UDP del ESP32, deduplicar eventos, exponer REST + WebSocket, ejecutar la lógica de
  negocio que el ESP32 no ejecuta, y persistir en SQLite.
- **Persistencia:** SQLite, con el esquema relacional de la sección 8.
- **Firmware ESP32:** Arduino framework o ESP-IDF, con una librería UDP estándar.

### 11.3 Pendientes a resolver antes de programar

1. Confirmar con el profesor el alcance exacto de la restricción UDP (sección 4.1).
2. Decidir el lenguaje del backend (Python o Node.js) según preferencia/familiaridad del usuario.
3. Buscar o definir rangos clínicos de referencia para Exploración de Faro, Tracking Visomotor y
   Laberinto (no existen en el prototipo, a diferencia de Stroop y N-Back).
4. Definir si 0-back/1-back (brief) o 1/2/3-back (prototipo) es la escala de niveles final del
   N-Back.
5. Dimensionar la frecuencia de streaming UDP para joystick (Faro, Tracking) y acelerómetro
   (Laberinto).

---

## 12. Próximos pasos sugeridos para el desarrollo

1. Definir el esquema SQLite final (tablas de la sección 8) y los endpoints REST/WebSocket del
   backend.
2. Implementar el bridge UDP del backend con deduplicación (sección 4.3) y el mecanismo de
   sincronización de reloj (sección 4.4), antes de tocar cualquier pantalla.
3. Construir el shell de la app web (login, home, barra superior, menú hamburguesa, estado del
   dispositivo) sin lógica de tests todavía.
4. Implementar gestión de pacientes e historial (CRUD + búsqueda + borrado selectivo).
5. Portar el patrón de carrusel de instrucciones y el menú de pausa de 3 opciones del prototipo
   (reutilizable casi 1:1 como estructura de datos + componente UI).
6. Implementar Stroop y N-Back primero (tienen lógica clínica y umbrales ya validados en el
   prototipo) antes que los tres tests nuevos basados en streaming continuo (Faro, Tracking,
   Laberinto), que requieren resolver primero la arquitectura de eventos de alta frecuencia.
7. Implementar firmware del ESP32 en paralelo, empezando por los eventos discretos (botones,
   encoder) y dejando el streaming continuo (joystick, acelerómetro) para una segunda etapa.
