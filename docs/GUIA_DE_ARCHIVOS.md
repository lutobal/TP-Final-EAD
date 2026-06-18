# Guía de archivos del proyecto (explicado simple)

Este documento explica qué hace cada archivo de código que existe hasta ahora,
en lenguaje simple, para alguien que no programa. La idea es que puedas
entender "para qué sirve esto" sin tener que leer el código.

El proyecto está hecho a propósito con **pocos archivos y sin piezas
"compartidas"**: cada archivo se puede abrir y leer de arriba a abajo sin
tener que saltar a otro lado para entender qué hace. Esto significa que hay
algo de código repetido entre páginas (por ejemplo, la barra superior se
escribe en cada página en vez de "compartirse" entre todas), pero a cambio
cada archivo se entiende solo.

---

## 1. Las dos mitades del proyecto

Todo el proyecto se divide en dos partes que viven en carpetas separadas:

- **`backend/`** = el "cerebro" que corre en la computadora servidor. Guarda
  los datos (médicos, pacientes, y en el futuro resultados de tests), valida
  cosas (¿la contraseña es correcta?, ¿el ID de paciente ya existe?), y le
  contesta a quien le pregunte. Es **un solo archivo**: `server.py`.
- **`frontend/`** = lo que ves en la pantalla del navegador. Son los archivos
  que tu navegador (Chrome, Edge, etc.) descarga y dibuja: botones, textos,
  colores, formularios.

Pensalo como un restaurante: el **frontend** es el salón y el menú que ve el
cliente; el **backend** es la cocina, que recibe el pedido, lo prepara y lo
manda de vuelta. La comunicación entre ambos se hace pidiendo cosas por
internet (técnicamente, "peticiones HTTP" — pedidos con una dirección, como
`/api/tests`, que el backend entiende y contesta).

---

## 2. Backend (`backend/`)

### `requirements.txt`
Es una lista de compras. Dice qué herramientas externas de Python hace falta
instalar para que el programa funcione: **FastAPI** (el motor que entiende
pedidos por internet) y **Uvicorn** (lo que efectivamente lo pone en
marcha — ver la pregunta "¿Qué es uvicorn?" más abajo si te la perdiste).

### `server.py`
Todo el backend está en este único archivo, dividido en 4 bloques (están
marcados con comentarios `# ---` adentro del archivo, en este mismo orden):

1. **Base de datos**: abre/crea el archivo `backend/data/neurorehab.db`
   (una base de datos SQLite — pensalo como un Excel con hojas) y define
   cuatro hojas: `medicos` (id, usuario, contraseña en código, nombre),
   `pacientes` (id, nombre, apellido, fecha de nacimiento, comentarios),
   `resultados` (un intento de un test: paciente, qué test, fecha/hora,
   parámetros usados, métricas resumidas, comentario del médico) y
   `resultados_detalle` (una fila por cada estímulo/ensayo dentro de un
   resultado: qué se mostró, qué respondió el paciente, si estuvo bien, y
   el tiempo de reacción).
2. **Contraseñas**: nunca guarda la contraseña tal cual la escribís (sería
   inseguro); la transforma en un código indescifrable (un "hash") antes de
   guardarla, y cuando alguien intenta entrar, vuelve a transformar lo que
   escribió y compara los dos códigos.
3. **Datos fijos y pedidos que atiende**: la ficha técnica de los 5 tests
   clínicos (Faro, Stroop, N-Back, Tracking, Laberinto), y las funciones que
   atienden cada pedido concreto:
   - **Iniciar sesión / registrarse**: el usuario del médico no puede tener
     espacios, y no distingue mayúsculas de minúsculas ("Luana" y "luana"
     son el mismo usuario — se guarda siempre en minúsculas por dentro).
   - **Listar tests** y **traer los datos de un test puntual**.
   - **Dar de alta un paciente nuevo**: rechaza ID vacío o no numérico, ID
     ya usado, y también nombre+apellido ya usados por otro paciente (con
     otro ID) — esto último tampoco distingue mayúsculas/minúsculas.
   - **Buscar/listar pacientes existentes**: la búsqueda tampoco distingue
     mayúsculas de minúsculas, y entiende nombre y apellido juntos (por
     ejemplo "Carla Diaz") aunque sean dos columnas separadas en la base de
     datos.
   - **Traer los datos de un paciente puntual** (por su ID): es lo que usa
     `pages/paciente-detalle.html` para mostrar fecha de nacimiento y
     comentarios, que no aparecen en el listado.
   - **Guardar el resultado de un test**: recibe el resultado completo
     (parámetros usados, métricas, y el detalle de cada estímulo) y lo
     guarda en `resultados` + `resultados_detalle` de una sola vez.
   - **Listar los resultados de un paciente**, **traer el detalle completo
     de un resultado puntual** (estímulo por estímulo), **borrar un
     resultado puntual**, o **borrar todo el historial de un paciente**.
4. **El servidor en sí**: la parte que efectivamente prende todo y, al
   final del archivo, le dice al programa "todo lo que esté en la carpeta
   `frontend/` mostralo tal cual" (por eso cuando entrás a la página, ves
   el login).

---

## 3. Frontend (`frontend/`)

### `css/style.css`
El único archivo que sí se comparte entre todas las páginas, porque es
puramente visual (colores, tipografía, tamaños, bordes) — no tiene ninguna
lógica de la aplicación, así que no hace falta entenderlo para entender cómo
funciona la plataforma. Sirve para que todas las pantallas se vean
consistentes entre sí.

Tiene una regla especial cerca del principio del archivo:
`[hidden] { display: none !important; }`. Sin ella, cualquier elemento que
JavaScript intente ocultar (poniéndole el atributo `hidden`) seguiría
apareciendo en pantalla si tiene una clase que le fija un `display` propio
(por ejemplo `.form { display: flex }`) — nos pasó tres veces antes de
agregar esta regla. Si en algún momento algo "oculto" sigue interceptando
clics o se sigue viendo, esta es la primera línea a revisar.

### `index.html`
La primera pantalla que ves al entrar a la página: el login. Tiene dos
pestañas (Iniciar sesión / Registrarse) con sus formularios, y un bloque
`<script>` al final con toda la lógica de esa pantalla: cambiar de pestaña,
revisar que no falten datos, mandarle los datos al backend, y guardar quién
inició sesión (en la memoria temporal del navegador) para llevarte a la
página de inicio.

### `pages/home.html`
La página de inicio. Arriba tiene la barra superior y el menú hamburguesa
(siempre el mismo bloque de HTML, repetido en cada página interna). Abajo,
su `<script>` propio: revisa que haya una sesión activa (si no, te manda al
login), y le pide al backend la lista de los 5 tests para dibujarla como
tarjetas.

### `pages/test-detail.html`
La página de detalle de un test. Sirve para los 5 tests por igual: mira en
la dirección web (URL) cuál test hay que mostrar (por ejemplo
`?slug=stroop`), le pide al backend los datos de ese test puntual, y los
muestra (qué evalúa, cómo funciona, variables, etc.). El botón "Realizar
este test" lleva a la pantalla real del test si ya existe (por ahora, Stroop,
Faro, Tracking y Laberinto); para N-Back, el único que falta, todavía
muestra el cartel de "no implementado".

Si el test tiene el campo `metricas_detalle` (por ahora, Faro, Stroop,
Tracking y Laberinto — se define en `server.py`, dentro de su entrada en
`TESTS`), esta página agrega
una sección extra "Métricas calculadas y cómo se interpretan" con un
acordeón desplegable (`<details>`/`<summary>`, sin necesidad de JavaScript
para abrir/cerrar) por cada métrica: qué mide, cómo se calcula, y su tabla
de interpretación. Si un test no tiene ese campo todavía, esta sección
simplemente no aparece — la página sigue
funcionando igual que antes.

### `pages/test-stroop.html`
La pantalla real del test de Stroop — el primero de los 5 tests
implementado. Es una sola página, pero por dentro tiene 5 "pantallas" que se
muestran de a una (se ocultan/muestran con JavaScript, no son páginas
separadas):

1. **Gate de paciente**: si no hay paciente activo, te ofrece elegir uno
   existente, crear uno nuevo, o cancelar (sección 9.7 del documento de
   especificación). Si ya hay paciente activo, esta pantalla se salta.
2. **Instrucciones**: un carrusel de pasos cortos, igual al patrón del
   prototipo (sección 2.1a), con la navegación típica de un carrusel
   (Anterior a la izquierda, Siguiente a la derecha, Saltear en el medio) y
   un dibujo ilustrativo distinto en cada paso (la palabra de ejemplo, los
   niveles coloreados, los botones de colores, las opciones de pausa, etc.,
   reproduciendo los dibujos que tenía `main_prototipo.py`). Describe cómo
   se usa el control físico (los botones de colores), no el teclado. Es lo
   primero que se ve (antes de elegir nivel/cantidad), a pedido explícito.
3. **Configuración**: elegís el nivel (fácil/intermedio/difícil) y la
   cantidad de estímulos, con un solo número entre 10 y 200 (a propósito:
   ese único valor es el que más adelante se va a poder fijar con el
   encoder rotativo del control físico, en vez de con este campo de texto).
   Si tocás "Iniciar" sin haber elegido un nivel, aparece un aviso pidiendo
   que elijas uno — recién ahí arranca el test directamente.
4. **El test**: aparece una palabra de color en una tinta de otro color;
   hay que indicar el color de la *tinta*. Por ahora, mientras no existe el
   dispositivo físico, se responde con las teclas 1/2/3/4 del teclado (cada
   botón en pantalla muestra su número), además de poder clickear los
   botones con el mouse. Cada respuesta llama a la misma función
   (`registrarRespuesta`) sin importar de dónde vino — eso es lo que va a
   permitir, más adelante, sumar los eventos del dispositivo real sin tocar
   el resto de la lógica del test. Si no se responde en 5 segundos, se
   cuenta como "omisión" y se pasa al siguiente estímulo. Arriba a la
   derecha hay un botón circular con el ícono de pausa (dos barras
   verticales, no texto) que abre las 3 opciones de siempre
   (Reanudar/Reiniciar/Volver al menú).
5. **Resultados**: precisión, clasificación (Normal/Limítrofe/Patológico),
   tiempo de reacción promedio, y efecto de interferencia (solo en nivel
   intermedio). Desde ahí se puede guardar el resultado (con un comentario
   clínico opcional) o descartarlo sin guardar nada. Una vez guardado,
   aparecen dos botones nuevos: "Volver al inicio" o "Realizar otro
   intento" (este último te manda de nuevo a la pantalla de Configuración,
   con el nivel sin elegir, para repetir el test con el mismo paciente).

### `pages/test-faro.html`
La pantalla real del test de Exploración de Faro — el segundo de los 5 tests
implementado. Misma estructura que `test-stroop.html` (una sola página, varias
"pantallas" internas que se muestran de a una), pero el test en sí usa un
`<canvas>` en vez de tarjetas de texto:

1. **Gate de paciente** e **instrucciones**: igual patrón que Stroop, con
   ilustraciones propias (un círculo de luz sobre un fondo oscuro) que
   explican la metáfora de la linterna. Igual que Stroop describe sus
   botones de colores y nunca menciona el teclado, las instrucciones del
   Faro hablan del joystick y su botón (el control físico final) y no
   mencionan el mouse ni el clic, aunque por ahora el mouse es lo que
   realmente está conectado por dentro.
2. **Configuración**: a diferencia de Stroop (que tiene niveles
   fácil/intermedio/difícil), el Faro expone directamente los 5 parámetros
   que menciona el documento de especificación de este test: cantidad de
   objetivos, tiempo disponible, radio de la linterna, tamaño de los
   objetivos y contraste entre objetivos y fondo (este último ya viene
   preseleccionado en "Alto", así que tocar "Iniciar" sin cambiar nada ya
   arranca el test con valores razonables).
3. **El test**: el paciente mueve el mouse (haciendo de joystick, todavía no
   existe el dispositivo físico) sobre un `<canvas>` oscuro; solo se ve lo
   que cae dentro de un círculo de "luz" alrededor del cursor. Hacer clic (o
   presionar la barra espaciadora) marca como encontrado el objetivo más
   cercano que esté iluminado en ese momento. El test termina cuando se
   encuentran todos los objetivos o se agota el tiempo configurado; lo que
   no se encontró cuenta como omitido. Mientras se juega, el sistema también
   registra qué celdas de una grilla invisible fueron "iluminadas" en algún
   momento, para calcular después qué porcentaje de cada mitad de la
   pantalla se exploró.
4. **Resultados**: calcula las 5 métricas clínicas del documento de
   especificación de este test (todas comparando el lado izquierdo contra el
   derecho, pensadas para detectar *neglect* espacial post-ACV):
   - **Índice de omisión izquierda**: qué porcentaje de los objetivos del
     lado izquierdo no se encontraron.
   - **Asimetría izquierda-derecha**: si se encontraron más objetivos de un
     lado que del otro.
   - **Center of Cancellation** (Rorden & Karnath, 2010): la posición
     horizontal promedio de los objetivos encontrados, comparada contra el
     centro de todos los objetivos que había en pantalla; un valor por
     encima de 0,081 (en valor absoluto) se considera patológico. La fórmula
     exacta no estaba en el resumen que me pasaste, así que la confirmé
     contra el repositorio de software del propio autor (Chris Rorden)
     antes de programarla.
   - **Latencia al primer objetivo izquierdo**: cuánto tardó en encontrar el
     primer objetivo de la izquierda comparado con el de la derecha.
   - **Cobertura espacial izquierda**: qué porcentaje del lado izquierdo de
     la pantalla llegó a iluminar, aunque no haya encontrado nada ahí.

   Cada nivel de severidad (Normal/Leve/Moderado/Severo) tiene su color
   (verde/amarillo/naranja/rojo) — una escala de 4 niveles distinta a la de
   3 niveles (Normal/Limítrofe/Patológico) que usa Stroop, porque así es como
   está definida en el documento de este test. El resto del flujo (guardar
   con comentario clínico, descartar, otro intento) es idéntico a Stroop.

### `pages/test-tracking.html`
La pantalla real del test de Tracking Visomotor — el tercer test
implementado. Mismo patrón de pantallas que Faro y Stroop, pero a diferencia
de esos dos (que avanzan de a un estímulo/objetivo por vez), este test es
**continuo**: un objetivo se mueve solo por la pantalla siguiendo una curva
(matemáticamente, una curva de Lissajous: dos movimientos tipo onda, uno
horizontal y otro vertical, combinados) y el paciente tiene que mantener su
cursor lo más cerca posible todo el tiempo, sin que haya "estímulos"
individuales que aparezcan y desaparezcan.

1. **Gate de paciente** e **instrucciones**: mismo patrón que los otros dos,
   con ilustraciones propias (un objetivo naranja, un cursor azul que se
   pone verde cuando está dentro del círculo punteado de tolerancia).
2. **Configuración**: duración del test (segundos), velocidad de la
   trayectoria (un multiplicador) y complejidad (Simple/Media/Compleja, que
   cambia qué tan intrincada es la curva que sigue el objetivo) —
   "Complejidad" ya viene en "Simple" preseleccionada.
3. **El test**: un `<canvas>` con fondo claro (a diferencia del fondo oscuro
   de Faro, porque aquí no hay nada que esconder) donde se ve el objetivo
   naranja moviéndose y el cursor azul siguiendo al mouse (haciendo de
   joystick). Hay una zona de tolerancia de 15 px alrededor del objetivo: si
   el cursor está dentro, se pone verde y arriba a la derecha aparece "En
   zona" en vez de "Fuera de zona". El test no tiene "encontrar" ni "hacer
   clic" en nada — simplemente corre durante el tiempo configurado.
4. **Resultados**: calcula las métricas del documento de especificación de
   este test — error promedio, error máximo, variabilidad del movimiento
   (desvío estándar del error) y porcentaje de tiempo dentro de la zona de
   tolerancia, cada una con su clasificación Normal/Leve/Moderado/Severo —
   más una **clasificación global** que suma puntos de las 4 anteriores
   (Normal=0, Leve=1, Moderado=2, Severo=3) para dar una sola lectura
   resumen. El detalle que se guarda no es uno por cada muestra de
   animación (sería miles de filas): se agrupa en un resumen por segundo,
   que alcanza para que el terapeuta vea cómo varió el error a lo largo del
   test.

### `pages/test-laberinto.html`
La pantalla real del test de Laberinto con Acelerómetro — el cuarto test
implementado, y el último que no usa botones ni clic en nada (es continuo,
igual que Tracking). La diferencia clave con los otros tests: en este, el
control físico no se sostiene quieto para apretar algo, sino que se inclina
con las dos manos — por eso las instrucciones (y el subtítulo que se ve
durante el test) dicen explícitamente "sostené el control con las dos manos
e inclinalo", nunca "mouse" ni "clic".

1. **Gate de paciente** e **instrucciones**: mismo patrón que los otros
   tres, con una ilustración propia de la consola (un rectángulo oscuro con
   las dos manijas laterales, como en el diseño físico real, con una mira
   en el centro marcando dónde va el acelerómetro) inclinándose para
   mostrar cómo empuja a la bolita.
2. **Configuración**: complejidad del laberinto (Simple/Media/Compleja —
   cambia el laberinto que se usa, no solo un parámetro numérico) y tiempo
   máximo en segundos (si se agota, el test termina igual, marcado como "no
   completado").
3. **El test**: un `<canvas>` con fondo claro donde se ve un laberinto
   hecho de paredes rectangulares oscuras, una bolita plateada y una zona
   de meta verde punteada. A la derecha del laberinto hay un **control
   circular aparte** (un segundo `<canvas>` más chico, con un punto azul
   que se mueve dentro de un círculo, ambos visibles a la vez): ahí es
   donde se mueve el mouse para simular la inclinación, no sobre el
   laberinto en sí. El centro del círculo es el reposo; cuánto más lejos
   del centro muevas el mouse *dentro de ese círculo*, más fuerte "empuja"
   a la bolita en esa dirección, y si el mouse sale del círculo la
   inclinación vuelve a cero sola (como si soltaras un joystick). La
   primera versión usaba el centro del canvas del laberinto (invisible,
   sin ninguna referencia) y al usuario no le funcionaba bien por eso —
   este control aparte, con un punto de referencia visible, fue el
   arreglo. La bolita tiene fricción (frena sola si no inclinás) y rebota
   contra las paredes; cada choque cuenta y la bolita parpadea en rojo un
   instante. Llegar a la zona verde termina el test antes de que se acabe
   el tiempo.

   El laberinto **se genera al azar** (función `generarLaberinto`) cada
   vez que se toca "Iniciar" — no es siempre el mismo. Cada "pared" en
   realidad son dos franjas que tocan los dos bordes de la pantalla
   (arriba y abajo), dejando un único hueco angosto como paso — así nunca
   se puede esquivar pasando todo por arriba o todo por abajo (la primera
   versión confinaba las paredes a una banda con margen libre en los
   bordes, y eso permitía precisamente esa trampa). La altura de cada
   hueco varía respecto al hueco anterior con un desplazamiento mínimo
   (nunca queda igual de alto que el anterior, así que siempre hay que
   corregir un poco) y máximo (esa corrección nunca es un salto enorme de
   arriba a abajo) — el resultado es que el movimiento dominante sigue
   siendo de izquierda a derecha, con ajustes verticales chicos para
   encontrar cada hueco. El inicio y la meta están a la misma altura.
   "Reiniciar" desde la pausa repite el mismo laberinto del intento
   actual (no genera uno nuevo); "Realizar otro intento" sí genera uno
   nuevo, porque vuelve a la pantalla de configuración y desde ahí cada
   "Iniciar" llama a `generarLaberinto` de nuevo.
4. **Resultados**: las 5 métricas del documento de especificación de este
   test — tiempo respecto a un tiempo ideal de referencia (cada laberinto
   tiene el suyo, calculado a partir de su camino más corto posible),
   cantidad de choques, desviación respecto a esa trayectoria ideal
   (cuánto más recorrió la bolita comparado con el camino más corto),
   movimientos bruscos (cambios repentinos de inclinación, pensados para
   detectar temblor) y precisión del control (% del tiempo sin tocar
   paredes) — cada una Normal/Leve/Moderado/Severo. Si no llegó a la meta
   a tiempo, los resultados lo aclaran arriba de todo ("No completado")
   para que el resto de los números se lean en ese contexto.

### `pages/pacientes.html`
Permite dos cosas: **buscar** pacientes ya creados (por nombre, apellido o
ID, en cualquier combinación — al entrar a la página ya muestra todos) y
**crear** un paciente nuevo. El formulario de alta está oculto por defecto:
aparece un botón "+ Crear paciente nuevo" que lo despliega, y vuelve a
ocultarse solo después de crear un paciente con éxito. Cada resultado de la
búsqueda tiene dos botones: "Usar este paciente" (lo "activa" para el resto
de la sesión: lo guarda en la memoria temporal del navegador, y a partir de
ahí aparece en la barra superior de todas las páginas) y "Ver detalle" (te
lleva a `paciente-detalle.html`). Si se llega a esta página desde el "gate"
de un test (por ejemplo `?volver=stroop`), elegir o crear un paciente te
devuelve directamente a ese test en vez de quedarte en Pacientes.

### `pages/paciente-detalle.html`
Muestra toda la información de un paciente puntual (nombre, apellido, ID,
fecha de nacimiento, comentarios) — los datos que no se ven en el listado de
`pacientes.html`. Tiene los mismos dos botones que el listado ("Usar este
paciente") más uno nuevo: "Ver historial de este paciente", que te lleva a
`historial.html`, pasándole el paciente para que cargue su historial
directamente.

### `pages/historial.html`
Dos partes: un buscador de pacientes (igual al de `pacientes.html`) y, una
vez elegido uno, la lista de sus intentos guardados. Cada intento muestra el
nombre del test, fecha y hora, un resumen de métricas (distinto según el
test, con TODAS las métricas que ese test calcula — ver la función
`resumenMetricas` dentro del `<script>`, que decide qué mostrar según
`test_slug`) y el comentario clínico si tiene. Por cada intento hay dos botones: "Ver
detalle" (despliega una tabla con cada estímulo, fila por fila, pidiéndola
al backend recién en ese momento) y "Eliminar este intento" (pide
confirmación). Arriba de la lista hay un botón para eliminar todo el
historial del paciente de una vez. Si se llega acá con `?paciente_id=` en
la URL (por ejemplo desde `paciente-detalle.html`), el historial de ese
paciente se carga solo, sin tener que buscarlo de nuevo.

### `pages/configuracion.html`, `pages/estado-dispositivo.html`
Páginas "en construcción". Tienen la barra superior y el menú funcionando,
pero el contenido todavía es solo un cartel de "esta sección no está
implementada todavía". Existen para que la navegación no quede rota mientras
se construyen esas funciones más adelante.

---

## 4. El bloque que se repite en cada página interna

Todas las páginas menos `index.html` empiezan con este mismo patrón (se
repite tal cual, a propósito, en vez de compartirse en un archivo aparte):

```html
<div class="topbar">...</div>      <!-- la barra de arriba: incluye el botón
                                         🏠 (siempre lleva a home.html) y el
                                         botón ☰ -->
<nav class="hamburger-menu">...</nav>  <!-- el menú que se abre con ☰ -->
```

y su `<script>` arranca siempre revisando lo mismo:

```js
const medicoGuardado = sessionStorage.getItem("medico");
if (!medicoGuardado) {
  window.location.href = "/index.html";   // sin sesión, no se puede estar acá
} else {
  // ... acá adentro va lo propio de cada página
}
```

Si entendés este bloque una vez, ya entendiste el principio de las 9
páginas internas — lo único que cambia entre una y otra es lo que hay
*después* de ese bloque.

Lo mismo pasa con el **paciente activo**: cada página revisa si hay un
paciente guardado en `sessionStorage` (bajo la clave `"paciente"`) y, si
hay, lo muestra en la barra superior en vez de "Sin paciente activo". El
menú hamburguesa tiene un botón "Cerrar paciente" que solo borra esa clave
(no afecta la sesión del médico) — es lo opuesto a "Usar este paciente" de
`pages/pacientes.html`.

---

## 5. Un ejemplo concreto: qué pasa cuando iniciás sesión

Para ver cómo se conectan todas estas piezas, este es el recorrido completo
de una sola acción:

1. Escribís tu usuario y contraseña en `index.html` y tocás "Iniciar sesión".
2. El `<script>` de esa misma página agarra esos datos, los revisa (¿están
   vacíos?) y si están bien los manda por internet a la dirección
   `/api/auth/login` (usando `fetch`, la función del navegador para pedir
   cosas a un servidor).
3. En `backend/server.py`, la función `login(...)` recibe ese pedido, busca
   el usuario en la base de datos y compara la contraseña (en código, no en
   texto plano).
4. Si todo coincide, el backend contesta "OK, este es el médico" (id,
   usuario, nombre). Si algo no coincide, contesta con un mensaje de error
   específico (usuario inexistente, contraseña incorrecta, etc.).
5. De vuelta en el navegador, si la respuesta fue OK, `index.html` guarda
   esos datos en `sessionStorage` (la memoria temporal del navegador) y te
   lleva a `pages/home.html`; si fue un error, lo muestra en pantalla.
6. Ya en `pages/home.html`, su `<script>` confirma que hay sesión activa,
   dibuja la barra superior con tu nombre, y le pide al backend (de nuevo
   con `fetch`, esta vez a `/api/tests`) la lista de tests para mostrarla
   como tarjetas.

Todo lo demás del sitio sigue este mismo patrón: una página `.html` con su
`<script>` adentro, hablando directamente con una función de
`backend/server.py`, que a su vez consulta la base de datos si hace falta.

---

## 6. Preguntas que ya surgieron

**¿Qué es Uvicorn?**
FastAPI (el código de `server.py`) es la receta: dice "si llega este pedido,
hacé esto". Pero una receta escrita en un papel no le sirve a nadie si no
hay alguien parado en la cocina, atento, que reciba los pedidos y los vaya
ejecutando. Uvicorn es ese "alguien": un programa que agarra el código de
`server.py` y lo pone a escuchar en una dirección de internet
(`127.0.0.1:8000`), recibe cada pedido que llega del navegador, se lo pasa a
`server.py` para que lo resuelva, y devuelve la respuesta.
