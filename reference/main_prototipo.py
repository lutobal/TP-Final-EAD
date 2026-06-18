# ============================================================
#  main.py  -  OpenRehab ACV
# ============================================================
#  Para correr:
#    1. pip install pygame
#    2. python main.py
# ============================================================


import pygame 
import sys
import json
import os
import random
import math
import re
from datetime import datetime

# ════════════════════════════════════════════════════════════
#  CONFIGURACION: pantalla adaptable al monitor. Usamos el tamaño real del monitor
#  y escalamos todo proporcionalmente.
# ════════════════════════════════════════════════════════════
pygame.init()
info_monitor  = pygame.display.Info()
ANCHO         = info_monitor.current_w
ALTO          = info_monitor.current_h
# Escala relativa a 1024x768 (resolucion base de diseño)
ESCALA_X      = ANCHO / 1024
ESCALA_Y      = ALTO  / 768
ESCALA        = min(ESCALA_X, ESCALA_Y)   # Usamos la menor para no distorsionar
FPS           = 60

def s(px):
    """Escala un valor de pixeles segun la resolucion del monitor."""
    return int(px * ESCALA)


# ════════════════════════════════════════════════════════════
#  PALETA DE COLORES
# ════════════════════════════════════════════════════════════
COLOR_FONDO          = (18,  45,  30)
COLOR_TITULO         = (255, 255, 255)
COLOR_SUBTITULO      = (185, 225, 195)
COLOR_BOTON_ACTIVO   = (39,  119,  75)
COLOR_BOTON_HOVER    = (52,  160, 100)
COLOR_BOTON_GRIS     = (70,  80,   72)
COLOR_TEXTO_BOTON    = (255, 255, 255)
COLOR_TEXTO_GRIS     = (140, 155, 140)
COLOR_PIE            = (120, 145, 120)
COLOR_DESCRIPCION    = (185, 225, 195)
COLOR_CASA_FONDO     = (30,  75,  48)
COLOR_CASA_HOVER     = (45,  110, 70)
COLOR_LINEA          = (52,  160, 100)
COLOR_VERDE          = (39,  119,  75)
COLOR_VERDE_HOVER    = (52,  160, 100)
COLOR_ROJO           = (160,  35,  35)
COLOR_ROJO_HOVER     = (200,  50,  50)
COLOR_AMARILLO       = (160, 120,   0)
COLOR_AMARILLO_HOVER = (200, 155,   0)
COLOR_AZUL           = ( 40, 100, 175)   # Azul (botón de observaciones del terapeuta)
COLOR_AZUL_HOVER     = ( 55, 130, 215)   # Azul claro (hover del botón de observaciones)


# ════════════════════════════════════════════════════════════
#  CARPETA DE RESULTADOS
#  Siempre junto al archivo main.py, sin importar en que
#  computadora se ejecute. os.path.dirname(__file__) devuelve
#  la carpeta donde esta este archivo.
# ════════════════════════════════════════════════════════════
CARPETA_RESULTADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


# ════════════════════════════════════════════════════════════
#  FUENTES
# ════════════════════════════════════════════════════════════
def cargar_fuentes():
    # Creamos un diccionario con todas las fuentes que usa la app.
    # Cada clave tiene un tamaño y uso específico, y todas escalan con s().
    f = {}
    try:
        f["titulo"]      = pygame.font.SysFont("Arial", s(38), bold=True)  # encabezados de pantalla
        f["subtitulo"]   = pygame.font.SysFont("Arial", s(26))              # texto informativo grande
        f["boton"]       = pygame.font.SysFont("Arial", s(28), bold=True)  # texto dentro de los botones
        f["descripcion"] = pygame.font.SysFont("Arial", s(20))              # descripciones secundarias
        f["etiqueta"]    = pygame.font.SysFont("Arial", s(18))              # textos pequeños y etiquetas
        f["casa"]        = pygame.font.SysFont("Arial", s(22), bold=True)  # barra superior durante el test
        f["instruccion"] = pygame.font.SysFont("Arial", s(22))              # texto en pantallas de instrucciones
        f["grande"]      = pygame.font.SysFont("Arial", s(46), bold=True)  # estímulo principal (figura, palabra)
        f["input"]       = pygame.font.SysFont("Arial", s(26))              # texto que escribe el usuario en formularios
    except:
        # Si por alguna razón Arial no está disponible, usamos la fuente por defecto de pygame
        d = pygame.font.Font(None, s(36))
        f = {k: d for k in ["titulo","subtitulo","boton","descripcion","etiqueta",
                             "casa","instruccion","grande","input"]}
    return f

# ════════════════════════════════════════════════════════════
#  TEXTO MULTILINEA EN BOTONES
#  Cuando una descripcion es muy larga para el ancho del boton,
#  la divide en varias lineas para que no sobresalga.
# ════════════════════════════════════════════════════════════
def render_en_lineas(screen, fuente, texto, color, x_izq, y_centro, max_ancho):
    """
    Dibuja 'texto' dividido en lineas si no entra en 'max_ancho' pixeles.
    x_izq   : borde izquierdo del texto
    y_centro: centro vertical del bloque completo de texto
    """
    # Separamos el texto en palabras y armamos lineas que quepan
    palabras = texto.split()
    lineas = []
    linea_actual = ""
    for palabra in palabras:
        prueba = linea_actual + (" " if linea_actual else "") + palabra
        if fuente.size(prueba)[0] <= max_ancho:
            linea_actual = prueba
        else:
            if linea_actual:
                lineas.append(linea_actual)
            linea_actual = palabra
    if linea_actual:
        lineas.append(linea_actual)

    # Calculamos la altura total y dibujamos centrado verticalmente
    alto_linea = fuente.get_height() + s(3)
    total_alto = len(lineas) * alto_linea
    y_ini = y_centro - total_alto // 2
    for linea in lineas:
        sf = fuente.render(linea, True, color)
        screen.blit(sf, sf.get_rect(midleft=(x_izq, y_ini + alto_linea // 2)))
        y_ini += alto_linea


# ════════════════════════════════════════════════════════════
#  GUARDAR JSON  
# ════════════════════════════════════════════════════════════
def guardar_json(id_paciente, nombre_paciente, test_nombre, metricas, observaciones=""):
    """
    Guarda el resultado en CARPETA_RESULTADOS/ID_Nombre.json
    Si el archivo existe, agrega el intento al historial.
    Si se pasan observaciones del terapeuta, se incluyen al final del intento.
    """
    if not os.path.exists(CARPETA_RESULTADOS):
        os.makedirs(CARPETA_RESULTADOS)

    # Reemplazamos espacios por guion bajo y eliminamos caracteres invalidos
    # Usamos lower() para que no importe si el usuario ingresa mayúsculas o minusculas
    nombre_limpio  = re.sub(r"\s+", "_", nombre_paciente.strip().lower())
    nombre_limpio  = re.sub(r"[^a-zA-Z0-9_\-]", "", nombre_limpio)
    nombre_archivo = f"{id_paciente}_{nombre_limpio}.json"
    ruta           = os.path.join(CARPETA_RESULTADOS, nombre_archivo)

    # Nuevo intento en formato legible
    nuevo_intento = {
        "━━━ NUEVO INTENTO ━━━": "",
        "Paciente"             : nombre_paciente,
        "ID"                   : id_paciente,
        "Fecha"                : datetime.now().strftime("%d/%m/%Y"),
        "Hora"                 : datetime.now().strftime("%H:%M"),
        "Test"                 : test_nombre,
        "─── Resultados ───"   : "",
        "Precisión obtenida"   : f"{metricas.get('precision_porcentaje', '?')}%",
        "Rango normal esperado": metricas.get("rango_esperado_precision", "?"),
        "Clasificación"        : metricas.get("clasificacion", "?"),
        "Fuente bibliográfica" : metricas.get("fuente_rango", "?"),
        "Tiempo reacción prom" : f"{metricas.get('tiempo_reaccion_promedio_ms', '?')} ms",
        "─── Detalle ───"      : "",
        "Nivel N-Back"         : f"{metricas.get('nivel_nback', '?')}-Back",
        "Estímulos evaluados"  : metricas.get("estimulos_evaluados", "?"),
        "Respuestas correctas" : metricas.get("respuestas_correctas", "?"),
        "Errores de omisión"   : metricas.get("errores_omision", "?"),
        "Errores de comisión"  : metricas.get("errores_comision", "?"),
        "─── Guía de errores (para el terapeuta) ───": "",
        "Error de omisión"     : "El paciente NO respondió cuando debía hacerlo (no presionó SI ante una coincidencia). Sugiere dificultad para detectar o recuperar el estímulo objetivo de la memoria de trabajo.",
        "Error de comisión"    : "El paciente respondió SI cuando NO habia coincidencia (falsa alarma). Sugiere impulsividad o confusión en la memoria de trabajo; el paciente 'recuerda' algo que no estaba.",
    }

    # Cargamos historial existente o empezamos de cero
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f_:
                historial = json.load(f_)
            if not isinstance(historial, list):
                historial = []
        except:
            historial = []
    else:
        historial = []

    # Si el terapeuta escribió observaciones, se agregan al final del intento
    if observaciones and observaciones.strip():
        nuevo_intento["─── Observaciones del terapeuta ───"] = ""
        nuevo_intento["Observaciones"] = observaciones.strip()

    historial.append(nuevo_intento)

    with open(ruta, "w", encoding="utf-8") as f_:
        json.dump(historial, f_, ensure_ascii=False, indent=2)

    return ruta


# ════════════════════════════════════════════════════════════
#  GUARDAR JSON - EFECTO STROOP
#  Mismo mecanismo que el N-Back pero con campos propios del Stroop.
#  El archivo se guarda con el mismo nombre (ID_nombre.json) para
#  que todos los tests de un mismo paciente queden en un solo lugar.
# ════════════════════════════════════════════════════════════
def guardar_json_stroop(id_paciente, nombre_paciente, metricas, observaciones=""):
    """
    Guarda el resultado del Stroop en CARPETA_RESULTADOS/ID_Nombre.json
    Si el paciente ya tiene un archivo (por el N-Back u otro test),
    agrega el intento al historial existente.
    Si se pasan observaciones del terapeuta, se incluyen al final del intento.
    """
    if not os.path.exists(CARPETA_RESULTADOS):
        os.makedirs(CARPETA_RESULTADOS)

    nombre_limpio  = re.sub(r"\s+", "_", nombre_paciente.strip().lower())
    nombre_limpio  = re.sub(r"[^a-zA-Z0-9_\-]", "", nombre_limpio)
    nombre_archivo = f"{id_paciente}_{nombre_limpio}.json"
    ruta           = os.path.join(CARPETA_RESULTADOS, nombre_archivo)

    nivel_nombre = {"facil": "Fácil", "intermedio": "Intermedio", "dificil": "Dificil"}.get(
        metricas.get("nivel_stroop", ""), metricas.get("nivel_stroop", "?"))

    nuevo_intento = {
        "━━━ NUEVO INTENTO ━━━": "",
        "Paciente"             : nombre_paciente,
        "ID"                   : id_paciente,
        "Fecha"                : datetime.now().strftime("%d/%m/%Y"),
        "Hora"                 : datetime.now().strftime("%H:%M"),
        "Test"                 : "Efecto Stroop",
        "─── Resultados ───"   : "",
        "Precisión obtenida"   : f"{metricas.get('precision_porcentaje', '?')}%",
        "Rango normal esperado": metricas.get("rango_esperado_precision", "?"),
        "Clasificación"        : metricas.get("clasificacion", "?"),
        "Fuente bibliográfica" : metricas.get("fuente_rango", "?"),
        "Tiempo reacción prom (correctas)" : f"{metricas.get('tiempo_reaccion_promedio_ms', '?')} ms",
        "─── Detalle ───"      : "",
        "Nivel Stroop"         : nivel_nombre,
        "Estímulos evaluados"  : metricas.get("estimulos_evaluados", "?"),
        "Respuestas correctas" : metricas.get("respuestas_correctas", "?"),
        "Errores de omisión"   : metricas.get("errores_omision", "?"),
        "Errores de comisión"  : metricas.get("errores_comision", "?"),
        "─── Guía de errores (para el terapeuta) ───": "",
        "Glosario"             : "Ensayo CONGRUENTE: la palabra y el color de la tinta coinciden (ej. ROJO escrito en rojo). Ensayo INCONGRUENTE: la palabra y el color de la tinta son distintos (ej. ROJO escrito en azul).",
        "Error de omisión"     : "El paciente NO respondió dentro del tiempo límite. Puede indicar lentitud en el procesamiento o dificultad para tomar decisiones bajo presión de tiempo.",
        "Error de comisión"    : "El paciente hizo clic en el color incorrecto. Puede indicar dificultad para inhibir la respuesta automática de lectura (efecto de interferencia elevado).",
    }

    campos_resultados = {}
    for k, v in nuevo_intento.items():
        campos_resultados[k] = v
        if k == "Tiempo reacción prom (correctas)":
            if metricas.get("rt_congruente_prom_ms") is not None:
                campos_resultados["Tiempo reacción (congruentes)"]   = f"{metricas['rt_congruente_prom_ms']} ms"
            if metricas.get("rt_incongruente_prom_ms") is not None:
                campos_resultados["Tiempo reacción (incongruentes)"] = f"{metricas['rt_incongruente_prom_ms']} ms"
            if metricas.get("efecto_interferencia") is not None:
                campos_resultados["Efecto de interferencia"] = f"{metricas['efecto_interferencia']} ms"
                campos_resultados["Interferencia normal"]    = "150-350 ms en adultos sanos (MacLeod, 1991)"
    nuevo_intento = campos_resultados

    # Cargar historial existente (si hay datos del N-Back u otro test)
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f_:
                historial = json.load(f_)
            if not isinstance(historial, list):
                historial = []
        except:
            historial = []
    else:
        historial = []

    # Si el terapeuta escribió observaciones, se agregan al final del intento
    if observaciones and observaciones.strip():
        nuevo_intento["─── Observaciones del terapeuta ───"] = ""
        nuevo_intento["Observaciones"] = observaciones.strip()

    historial.append(nuevo_intento)

    with open(ruta, "w", encoding="utf-8") as f_:
        json.dump(historial, f_, ensure_ascii=False, indent=2)

    return ruta


# ════════════════════════════════════════════════════════════
#  UTILIDAD: texto multilinea
# ════════════════════════════════════════════════════════════
def dibujar_texto_multilinea(surface, texto, fuente, color, x, y, ancho_max):
    # Va construyendo líneas palabra por palabra.
    # Cuando una línea supera el ancho máximo, la dibuja y empieza una nueva.
    palabras  = texto.split(" ")
    linea     = ""
    y_cur     = y
    for p in palabras:
        prueba = linea + p + " "
        if fuente.size(prueba)[0] <= ancho_max:
            # La palabra entra en la línea actual, la acumulamos
            linea = prueba
        else:
            # La palabra no entra, dibujamos la línea actual y empezamos otra
            surf = fuente.render(linea.strip(), True, color)
            surface.blit(surf, (x, y_cur))
            y_cur += fuente.get_height() + s(4)
            linea  = p + " "
    # Dibujamos la última línea que quedó pendiente
    if linea.strip():
        surf = fuente.render(linea.strip(), True, color)
        surface.blit(surf, (x, y_cur))
        y_cur += fuente.get_height() + s(4)
    return y_cur  # devolvemos la posición Y donde terminó el texto (útil para continuar dibujando debajo)


# ════════════════════════════════════════════════════════════
#  OVERLAY DE OBSERVACIONES DEL TERAPEUTA
#  Función compartida por los tres tests (N-Back, Stroop, AVD).
#  Se llama desde el método dibujar() de cada test cuando
#  self.modo_observaciones es True.
# ════════════════════════════════════════════════════════════
def dibujar_overlay_observaciones(screen, fuentes, texto_obs, hov, btn_guardar_obs, btn_descartar_obs):
    """
    Dibuja un panel semitransparente encima de la pantalla de fin.
    El terapeuta puede escribir observaciones antes de guardar.

    Parámetros:
        screen: superficie de pygame donde se dibuja
        fuentes: diccionario de fuentes cargadas
        texto_obs: string con el texto que ya escribió el terapeuta
        hov: dict de hover; usa las claves "guardar_obs" y "descartar_obs"
        btn_guardar_obs: pygame.Rect del botón "Guardar resultados y observaciones"
        btn_descartar_obs: pygame.Rect del botón "Descartar observaciones"
    """
    # ── Fondo semitransparente ────────────────────────────────
    overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 185))          # negro con 73% de opacidad
    screen.blit(overlay, (0, 0))

    # ── Panel central ─────────────────────────────────────────
    panel_w = s(780)
    panel_h = s(490)
    panel_x = ANCHO // 2 - panel_w // 2
    panel_y = ALTO  // 2 - panel_h // 2
    panel   = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
    pygame.draw.rect(screen, (20, 55, 35), panel, border_radius=s(18))
    pygame.draw.rect(screen, COLOR_LINEA,  panel, 2, border_radius=s(18))

    # ── Título ────────────────────────────────────────────────
    sf = fuentes["subtitulo"].render("Observaciones del terapeuta", True, COLOR_TITULO)
    screen.blit(sf, sf.get_rect(center=(ANCHO // 2, panel_y + s(38))))

    # ── Instrucción ───────────────────────────────────────────
    sf = fuentes["descripcion"].render(
        "Escriba sus observaciones y luego elija cómo guardar.", True, COLOR_SUBTITULO)
    screen.blit(sf, sf.get_rect(center=(ANCHO // 2, panel_y + s(70))))

    # ── Área de texto (cuadro blanco con borde) ───────────────
    area_x = panel_x + s(25)
    area_y = panel_y + s(97)
    area_w = panel_w - s(50)
    area_h = s(195)
    area   = pygame.Rect(area_x, area_y, area_w, area_h)
    pygame.draw.rect(screen, (240, 248, 245), area, border_radius=s(8))   # fondo casi blanco
    pygame.draw.rect(screen, COLOR_LINEA, area, 2, border_radius=s(8))    # borde verde

    # ── Texto del terapeuta renderizado dentro del área ───────
    fuente_texto = fuentes["instruccion"]
    margen       = s(10)
    max_ancho    = area_w - margen * 2
    color_texto  = (18, 45, 30)   # verde muy oscuro (legible sobre fondo claro)

    # Separamos por saltos de línea explícitos y luego hacemos word-wrap
    lineas_renderizadas = []
    for segmento in texto_obs.split("\n"):
        palabras = segmento.split(" ")
        linea_actual = ""
        for palabra in palabras:
            prueba = linea_actual + palabra + " "
            if fuente_texto.size(prueba)[0] <= max_ancho:
                linea_actual = prueba
            else:
                lineas_renderizadas.append(linea_actual.rstrip())
                linea_actual = palabra + " "
        lineas_renderizadas.append(linea_actual.rstrip())

    # Cursor parpadeante: se muestra un '|' al final del último bloque
    cursor = "|" if int(pygame.time.get_ticks() / 500) % 2 == 0 else " "
    if lineas_renderizadas:
        lineas_renderizadas[-1] += cursor
    else:
        lineas_renderizadas = [cursor]

    # Dibujar cada línea dentro del área de texto
    y_texto = area_y + margen
    altura_linea = fuente_texto.get_height() + s(3)
    for linea in lineas_renderizadas:
        if y_texto + altura_linea > area_y + area_h - margen:
            break   # no salir del área
        sf = fuente_texto.render(linea, True, color_texto)
        screen.blit(sf, (area_x + margen, y_texto))
        y_texto += altura_linea

    # ── Botón "Guardar resultados y observaciones" (verde) ────
    cg = COLOR_VERDE_HOVER if hov.get("guardar_obs") else COLOR_VERDE
    pygame.draw.rect(screen, cg, btn_guardar_obs, border_radius=s(14))
    sf = fuentes["instruccion"].render("Guardar resultados y observaciones", True, COLOR_TITULO)
    screen.blit(sf, sf.get_rect(center=btn_guardar_obs.center))

    # ── Botón "Descartar observaciones" (amarillo) ────────────
    cd = COLOR_AMARILLO_HOVER if hov.get("descartar_obs") else COLOR_AMARILLO
    pygame.draw.rect(screen, cd, btn_descartar_obs, border_radius=s(14))
    sf = fuentes["instruccion"].render("Descartar observaciones", True, COLOR_TITULO)
    screen.blit(sf, sf.get_rect(center=btn_descartar_obs.center))


# ════════════════════════════════════════════════════════════
#  PANTALLA 1: MENÚ PRINCIPAL
# ════════════════════════════════════════════════════════════
class MenuPrincipal:
    def __init__(self, screen, fuentes):
        self.screen    = screen
        self.fuentes   = fuentes
        # self.siguiente es la variable que usa el loop principal para saber a qué pantalla ir.
        # Mientras sea None, la pantalla actual se mantiene. Cuando se le asigna un valor, el loop cambia de pantalla.
        self.siguiente = None

        # Dimensiones y posición de los botones, centrados horizontalmente
        ab = s(420); alt = s(90)
        xc = (ANCHO - ab) // 2; yi = s(290)

        # Lista de los tres botones de área. "activo" determina si se puede hacer clic.
        # Las áreas Visual y Motora están deshabilitadas por ahora, solo Cognitiva funciona.
        self.botones = [
            {"rect": pygame.Rect(xc, yi,          ab, alt), "texto": "Visión y Percepción",
             "activo": False, "etiqueta": "Proximamente"},
            {"rect": pygame.Rect(xc, yi + s(120), ab, alt), "texto": "Control Motor y Acceso",
             "activo": False, "etiqueta": "Proximamente"},
            {"rect": pygame.Rect(xc, yi + s(240), ab, alt), "texto": "Cognición y Lenguaje",
             "activo": True,  "etiqueta": None},
        ]
        # hover_index guarda qué botón tiene el mouse encima (-1 = ninguno)
        self.hover_index  = -1
        self.boton_cerrar = pygame.Rect(ANCHO - s(150), s(20), s(130), s(52))
        self.hover_cerrar = False

    def manejar_eventos(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            p = ev.pos
            # Reiniciamos el hover en cada movimiento del mouse
            self.hover_index  = -1
            self.hover_cerrar = self.boton_cerrar.collidepoint(p)
            for i, b in enumerate(self.botones):
                # Solo detectamos hover en botones activos
                if b["activo"] and b["rect"].collidepoint(p):
                    self.hover_index = i
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            p = ev.pos
            if self.boton_cerrar.collidepoint(p):
                pygame.quit(); sys.exit()
            for b in self.botones:
                # Solo respondemos al clic si el botón está activo
                if b["activo"] and b["rect"].collidepoint(p):
                    self.siguiente = "cognitivo"  # le indicamos al loop que cambie al menú cognitivo

    def dibujar(self):
        self.screen.fill(COLOR_FONDO)
        # Línea decorativa debajo del encabezado
        pygame.draw.line(self.screen, COLOR_LINEA, (s(60), s(105)), (ANCHO - s(60), s(105)), 2)

        # Botón X (cerrar app), cambia de color cuando el mouse está encima
        cc = (180,50,50) if self.hover_cerrar else (130,35,35)
        pygame.draw.rect(self.screen, cc, self.boton_cerrar, border_radius=s(10))
        sf = self.fuentes["casa"].render("X  Salir", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.boton_cerrar.center))

        # Título y subtítulo de la pantalla
        sf = self.fuentes["titulo"].render("TP 1 - Ingenieria de Rehabilitación", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, s(62))))

        sf = self.fuentes["subtitulo"].render("Selecciona el área que deseas evaluar", True, COLOR_SUBTITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, s(195))))

        for i, b in enumerate(self.botones):
            # Los botones deshabilitados se muestran en gris, sin cambiar al hacer hover
            c  = COLOR_BOTON_HOVER if (b["activo"] and self.hover_index==i) else (COLOR_BOTON_ACTIVO if b["activo"] else COLOR_BOTON_GRIS)
            ct = COLOR_TEXTO_BOTON if b["activo"] else COLOR_TEXTO_GRIS
            pygame.draw.rect(self.screen, c, b["rect"], border_radius=s(14))
            sf = self.fuentes["boton"].render(b["texto"], True, ct)
            self.screen.blit(sf, sf.get_rect(center=b["rect"].center))
            # Si el botón tiene etiqueta ("Proximamente"), la mostramos debajo del botón
            if b["etiqueta"]:
                sf = self.fuentes["etiqueta"].render(b["etiqueta"], True, COLOR_PIE)
                self.screen.blit(sf, sf.get_rect(midtop=(b["rect"].centerx, b["rect"].bottom+s(6))))

        # Pie de página con el nombre de la materia
        sf = self.fuentes["etiqueta"].render("Ingeniería en Rehabilitación - ITBA 2026", True, COLOR_PIE)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, ALTO - s(28))))


# ════════════════════════════════════════════════════════════
#  PANTALLA 2: MENÚ COGNITIVO
# ════════════════════════════════════════════════════════════
class MenuCognitivo:
    def __init__(self, screen, fuentes):
        self.screen    = screen
        self.fuentes   = fuentes
        self.siguiente = None
        # Botón para volver al menú principal
        self.boton_volver = pygame.Rect(s(20), s(20), s(130), s(52))
        self.hover_volver = False
        self.boton_cerrar = pygame.Rect(ANCHO - s(150), s(20), s(130), s(52))
        self.hover_cerrar = False

        # Los tres tests disponibles en el área cognitiva, con su posición en pantalla
        ab = s(620); alt = s(110); xc = (ANCHO-ab)//2; yi = s(220)
        self.tests = [
            {"nombre": "Memoria N-Back",
             "descripcion": "Evalúa la memoria de trabajo comparando estímulos secuenciales",
             "id": "nback",
             "rect": pygame.Rect(xc, yi,          ab, alt), "hover": False},
            {"nombre": "Efecto Stroop",
             "descripcion": "Evalúa la velocidad de procesamiento y el control de atención con colores",
             "id": "stroop",
             "rect": pygame.Rect(xc, yi+s(140),   ab, alt), "hover": False},
            {"nombre": "Secuenciación AVD",
             "descripcion": "Evalúa la capacidad de ordenar pasos de actividades cotidianas",
             "id": "avd",
             "rect": pygame.Rect(xc, yi+s(280),   ab, alt), "hover": False},
        ]

    def manejar_eventos(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            p = ev.pos
            self.hover_volver = self.boton_volver.collidepoint(p)
            self.hover_cerrar = self.boton_cerrar.collidepoint(p)
            # Actualizamos el hover de cada tarjeta de test
            for t in self.tests: t["hover"] = t["rect"].collidepoint(p)
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            p = ev.pos
            if self.boton_cerrar.collidepoint(p):
                pygame.quit(); sys.exit()
            if self.boton_volver.collidepoint(p):
                self.siguiente = "principal"; return
            # Detectamos en qué test hizo clic y enviamos a sus instrucciones
            for t in self.tests:
                if t["rect"].collidepoint(p):
                    if t["id"] == "nback":
                        self.siguiente = "instrucciones_nback"
                    elif t["id"] == "stroop":
                        self.siguiente = "instrucciones_stroop"
                    elif t["id"] == "avd":
                        self.siguiente = "instrucciones_avd"

    def dibujar(self):
        self.screen.fill(COLOR_FONDO)
        cv = COLOR_CASA_HOVER if self.hover_volver else COLOR_CASA_FONDO
        pygame.draw.rect(self.screen, cv, self.boton_volver, border_radius=s(10))
        sf = self.fuentes["casa"].render("Volver", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.boton_volver.center))
        cc = (180, 50, 50) if self.hover_cerrar else (130, 35, 35)
        pygame.draw.rect(self.screen, cc, self.boton_cerrar, border_radius=s(10))
        sf = self.fuentes["casa"].render("Salir X", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.boton_cerrar.center))
        pygame.draw.line(self.screen, COLOR_LINEA, (s(60),s(110)), (ANCHO-s(60),s(110)), 2)
        sf = self.fuentes["titulo"].render("Área Cognitiva", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, s(65))))
        sf = self.fuentes["subtitulo"].render("Selecciona el test que deseas realizar", True, COLOR_SUBTITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, s(160))))
        for t in self.tests:
            c = COLOR_BOTON_HOVER if t["hover"] else COLOR_BOTON_ACTIVO
            pygame.draw.rect(self.screen, c, t["rect"], border_radius=s(14))
            sf = self.fuentes["boton"].render(t["nombre"], True, COLOR_TEXTO_BOTON)
            self.screen.blit(sf, sf.get_rect(midleft=(t["rect"].left+s(30), t["rect"].centery-s(18))))
            # max_ancho deja margen izquierdo (30) + espacio para el ">" de la derecha (70)
            max_ancho_desc = t["rect"].width - s(30) - s(70)
            render_en_lineas(self.screen, self.fuentes["descripcion"], t["descripcion"],
                             COLOR_DESCRIPCION, t["rect"].left+s(30),
                             t["rect"].centery+s(20), max_ancho_desc)
            sf = self.fuentes["boton"].render(">", True, COLOR_TEXTO_BOTON)
            self.screen.blit(sf, sf.get_rect(midright=(t["rect"].right-s(25), t["rect"].centery)))


# ════════════════════════════════════════════════════════════
#  PANTALLA 3: INSTRUCCIONES N-BACK  (carrusel de slides)
#  Mostramos 5 slides cortos con un dibujo explicativo cada uno. 
#  Es más fácil de entender para pacientes post-ACV.
# ════════════════════════════════════════════════════════════
class InstruccionesNBack:

    # Contenido de cada slide: título corto + hasta 3 lineas de texto
    SLIDES = [
        {
            "titulo": "Memoria N-Back",
            "lineas": [
                "Se te mostrarán figuras una por una.",
                "Cada figura tiene forma y color.",
                "Debes recordar la figura que viste antes.",
            ]
        },
        {
            "titulo": "Compará con la figura ANTERIOR",
            "lineas": [
                "Aparece una figura. Luego aparece otra.",
                "¿Son iguales en forma y color?",
                "Presioná SI o NO.",
            ]
        },
        {
            "titulo": "Se considera igual si tiene misma forma y mismo color",
            "lineas": [
                "Solo cuenta si coinciden LOS DOS.",
                "Misma forma, distinto color  →  NO.",
                "Mismo color, distinta forma  →  NO.",
            ]
        },
        {
            "titulo": "Usás los botones SI y NO",
            "lineas": [
                "Los botones aparecen junto con cada figura.",
                "También podés usar las teclas: ← para SI,  → para NO.",
                "Se evaluará el tiempo de reacción promedio.",
            ]
        },
        {
            "titulo": "Elegí tu nivel de dificultad",
            "lineas": [
                "1-Back (Fácil):   recordás 1 figura atrás.",
                "2-Back (Medio):  recordás 2 figuras atrás.",
                "3-Back (Difícil):  recordás 3 figuras atrás.",
            ]
        },
        {
            "titulo": "El botón de pausa",
            "lineas": [
                "En cualquier momento podés pausar el test.",
                "Podés pausar con el botón II o con la barra espaciadora.",
                "Al pausar aparecen tres opciones.",
            ]
        },
        {
            "titulo": "¡Todo listo!",
            "lineas": [
                "El test tiene 25 figuras en total.",
                "Recordá: ← SI  |  → NO  |  Espacio = Pausa",
                "Cuando estés listo, presioná Iniciar.",
            ]
        },
    ]

    def __init__(self, screen, fuentes):
        self.screen    = screen
        self.fuentes   = fuentes
        self.siguiente = None

        # Slide actual (0 a 6)
        self.slide_actual = 0
        self.N_SLIDES     = 7

        # Boton X para volver al menu cognitivo
        self.boton_x = pygame.Rect(s(20), s(20), s(52), s(52))

        # Botones de navegacion fijos abajo de la pantalla
        self.boton_anterior  = pygame.Rect(s(60),           ALTO - s(120), s(200), s(60))
        self.boton_siguiente = pygame.Rect(ANCHO - s(260),  ALTO - s(120), s(200), s(60))
        self.boton_saltear   = pygame.Rect(ANCHO//2 - s(90), ALTO - s(120), s(180), s(60))

        # Estado hover para cada boton (para el efecto de color al pasar el mouse)
        self.hover_x    = False
        self.hover_ant  = False
        self.hover_sig  = False
        self.hover_salt = False

    def manejar_eventos(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            p = ev.pos
            self.hover_x    = self.boton_x.collidepoint(p)
            # El boton anterior solo tiene hover si no estamos en el primer slide
            self.hover_ant  = (self.slide_actual > 0) and self.boton_anterior.collidepoint(p)
            self.hover_sig  = self.boton_siguiente.collidepoint(p)
            self.hover_salt = (self.slide_actual < self.N_SLIDES - 1) and self.boton_saltear.collidepoint(p)

        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            p = ev.pos
            # X: volver al menu cognitivo
            if self.boton_x.collidepoint(p):
                self.siguiente = "cognitivo"; return
            # Saltear: ir directamente al ultimo slide
            if self.slide_actual < self.N_SLIDES - 1 and self.boton_saltear.collidepoint(p):
                self.slide_actual = self.N_SLIDES - 1; return
            # Anterior: retroceder al slide previo (solo si no somos el primero)
            if self.slide_actual > 0 and self.boton_anterior.collidepoint(p):
                self.slide_actual -= 1; return
            # Siguiente o Iniciar
            if self.boton_siguiente.collidepoint(p):
                if self.slide_actual < self.N_SLIDES - 1:
                    self.slide_actual += 1         # avanzar al siguiente slide
                else:
                    self.siguiente = "nivel_nback" # ultimo slide: iniciar el test

        # ── Atajos de teclado ──────────────────────────────────────
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RIGHT:               # → Siguiente / Iniciar
                if self.slide_actual < self.N_SLIDES - 1:
                    self.slide_actual += 1
                else:
                    self.siguiente = "nivel_nback"
            elif ev.key == pygame.K_LEFT:              # ← Anterior
                if self.slide_actual > 0:
                    self.slide_actual -= 1
            elif ev.key == pygame.K_SPACE:             # Espacio → Saltear al ultimo slide
                if self.slide_actual < self.N_SLIDES - 1:
                    self.slide_actual = self.N_SLIDES - 1

    def dibujar(self):
        self.screen.fill(COLOR_FONDO)
        slide = self.SLIDES[self.slide_actual]

        # ── ZONA A: Encabezado fijo ─────────────────────────────
        sf = self.fuentes["subtitulo"].render("Instrucciones - Memoria N-Back", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(50))))
        pygame.draw.line(self.screen, COLOR_LINEA, (s(60), s(82)), (ANCHO - s(60), s(82)), 2)

        # Boton X (esquina superior izquierda)
        cx_color = COLOR_ROJO_HOVER if self.hover_x else COLOR_ROJO
        pygame.draw.rect(self.screen, cx_color, self.boton_x, border_radius=s(10))
        sf = self.fuentes["boton"].render("X", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.boton_x.center))

        # ── ZONA C: Titulo y texto del slide ───────────────────
        y_texto = s(135)
        sf = self.fuentes["boton"].render(slide["titulo"], True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, y_texto)))
        y_texto += s(50)
        for linea in slide["lineas"]:
            sf = self.fuentes["subtitulo"].render(linea, True, COLOR_SUBTITULO)
            self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, y_texto)))
            y_texto += s(36)

        # ── ZONA B: Dibujo explicativo del slide actual ─────────
        self._dibujar_visual(self.slide_actual)

        # ── ZONA D: Puntos de progreso y botones de navegacion ──
        self._dibujar_progreso()
        pygame.draw.line(self.screen, COLOR_LINEA,
                         (s(60), ALTO - s(130)), (ANCHO - s(60), ALTO - s(130)), 1)
        self._dibujar_botones_nav()

    # ── Dispatcher: llama al metodo visual del slide correcto ──
    def _dibujar_visual(self, idx):
        metodos = [
            self._visual_slide_0,
            self._visual_slide_1,
            self._visual_slide_2,
            self._visual_slide_3,
            self._visual_slide_4,
            self._visual_slide_5,
            self._visual_slide_6,
        ]
        metodos[idx]()

    # ── Slide 0: tres tarjetas con figuras para mostrar la variedad ──
    def _visual_slide_0(self):
        cy        = s(430)
        figuras   = [
            ("circulo",   (220,  60,  60)),   # rojo
            ("cuadrado",  ( 60, 100, 220)),   # azul
            ("triangulo", (220, 200,  40)),   # amarillo
        ]
        separacion = s(190)
        cx_inicio  = ANCHO // 2 - separacion

        for i, (forma, color_rgb) in enumerate(figuras):
            cx = cx_inicio + i * separacion
            # Tarjeta de fondo redondeada
            tarjeta = pygame.Rect(cx - s(70), cy - s(70), s(140), s(140))
            pygame.draw.rect(self.screen, (30, 70, 45), tarjeta, border_radius=s(14))
            pygame.draw.rect(self.screen, COLOR_LINEA,  tarjeta, s(2), border_radius=s(14))
            # Figura geometrica dentro de la tarjeta
            dibujar_figura(self.screen, forma, color_rgb, cx, cy, s(40))

    # ── Slide 1: dos tarjetas iguales + flecha + boton SI ──────
    def _visual_slide_1(self):
        cy     = s(400)
        cx_izq = ANCHO // 2 - s(160)
        cx_der = ANCHO // 2 + s(160)
        color_f = (220, 60, 60)   # ambas figuras rojas (son iguales)

        # Las dos tarjetas con el mismo circulo rojo
        for cx in [cx_izq, cx_der]:
            tarjeta = pygame.Rect(cx - s(65), cy - s(65), s(130), s(130))
            pygame.draw.rect(self.screen, (30, 70, 45), tarjeta, border_radius=s(14))
            pygame.draw.rect(self.screen, COLOR_LINEA,  tarjeta, s(2), border_radius=s(14))
            dibujar_figura(self.screen, "circulo", color_f, cx, cy, s(38))

        # Flecha entre las dos tarjetas
        cx_m = ANCHO // 2
        pygame.draw.line(self.screen, COLOR_TITULO,
                         (cx_m - s(45), cy), (cx_m + s(30), cy), s(4))
        pygame.draw.polygon(self.screen, COLOR_TITULO, [   # punta de flecha
            (cx_m + s(30), cy - s(12)),
            (cx_m + s(50), cy),
            (cx_m + s(30), cy + s(12)),
        ])

        # Pregunta arriba
        sf = self.fuentes["instruccion"].render("¿Son iguales?", True, COLOR_SUBTITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, cy - s(88))))

        # Boton SI abajo (igual que en el test real para que lo reconozcan)
        btn_si = pygame.Rect(ANCHO // 2 - s(90), cy + s(85), s(180), s(60))
        pygame.draw.rect(self.screen, COLOR_VERDE, btn_si, border_radius=s(14))
        sf = self.fuentes["boton"].render("SI", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=btn_si.center))

    # ── Slide 2: ejemplos correcto vs incorrectos ───────────────
    def _visual_slide_2(self):
        # Fila 1: circulo rojo vs circulo rojo     → SI ✓ (igual forma e igual color)
        # Fila 2: circulo rojo vs triangulo rojo   → NO ✗ (distinta forma)
        # Fila 3: circulo rojo vs circulo verde    → NO ✗ (distinto color)
        cy1     = s(355)
        cy2     = s(460)
        cy3     = s(565)
        cx_a    = ANCHO // 2 - s(175)
        cx_b    = ANCHO // 2 + s(10)
        cx_etiq = ANCHO // 2 + s(155)

        ejemplos = [
            (cy1, "circulo",   (220, 60,  60),  "SI", COLOR_VERDE),
            (cy2, "triangulo", (220, 60,  60),  "NO", COLOR_ROJO),
            (cy3, "circulo",   (60,  200, 80),  "NO", COLOR_ROJO),
        ]

        for cy, forma_b, color_b, etiq, color_etiq in ejemplos:
            # Figura izquierda: siempre círculo rojo
            dibujar_figura(self.screen, "circulo", (220, 60, 60), cx_a, cy, s(32))
            # Figura derecha: varía en forma y/o color
            dibujar_figura(self.screen, forma_b, color_b, cx_b, cy, s(32))
            # Etiqueta de resultado a la derecha
            sf = self.fuentes["boton"].render(etiq, True, color_etiq)
            self.screen.blit(sf, sf.get_rect(midleft=(cx_etiq, cy)))

        # Lineas separadoras entre filas
        for y_sep in [(cy1 + cy2) // 2, (cy2 + cy3) // 2]:
            pygame.draw.line(self.screen, COLOR_LINEA,
                             (ANCHO // 2 - s(220), y_sep),
                             (ANCHO // 2 + s(210), y_sep), 1)

    # ── Slide 3: mockup de figura + botones SI/NO apareciando juntos ──
    def _visual_slide_3(self):
        cy_fig = s(360)
        cy_btn = s(470)

        # Figura en el centro (igual que en el test real)
        tarjeta = pygame.Rect(ANCHO // 2 - s(55), cy_fig - s(55), s(110), s(110))
        pygame.draw.rect(self.screen, (30, 70, 45), tarjeta, border_radius=s(14))
        pygame.draw.rect(self.screen, COLOR_LINEA,  tarjeta, s(2), border_radius=s(14))
        dibujar_figura(self.screen, "circulo", (220, 60, 60), ANCHO // 2, cy_fig, s(32))

        # Boton SI (verde, identico al del test real)
        btn_si = pygame.Rect(ANCHO // 2 - s(230), cy_btn - s(33), s(190), s(66))
        pygame.draw.rect(self.screen, COLOR_VERDE, btn_si, border_radius=s(14))
        sf = self.fuentes["grande"].render("SI", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=btn_si.center))

        # Boton NO (rojo, identico al del test real)
        btn_no = pygame.Rect(ANCHO // 2 + s(40), cy_btn - s(33), s(190), s(66))
        pygame.draw.rect(self.screen, COLOR_ROJO, btn_no, border_radius=s(14))
        sf = self.fuentes["grande"].render("NO", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=btn_no.center))

    # ── Slide 4: los tres niveles con mini-secuencias de figuras ──
    def _visual_slide_4(self):
        # Mostramos los 3 niveles en filas: etiqueta de dificultad + mini diagrama
        niveles = [
            ("1-Back", "Fácil",   COLOR_VERDE,   2),  # necesita recordar 2 figuras
            ("2-Back", "Medio",   COLOR_AMARILLO, 3),  # necesita recordar 3 figuras
            ("3-Back", "Difícil", COLOR_ROJO,     4),  # necesita recordar 4 figuras
        ]
        cy_inicio = s(340)
        sep_fila  = s(85)

        # Calculo de posiciones centradas horizontalmente
        # Tag: s(145) ancho. Diagrama maximo: 4 figuras con sep s(52) = s(156)+s(28) = s(184)
        # Total fila = tag + gap + diagrama_max = s(145+20+184) = s(349)
        tag_w      = s(145)
        gap_td     = s(20)
        sep_fig    = s(52)
        x_row      = ANCHO // 2 - s(175)   # inicio del tag (centrado para fila de 4 figs)
        cx_fig_0   = x_row + tag_w + gap_td + s(14)  # centro de la primera figura

        for i, (nivel, dificultad, color_tag, n_figuras) in enumerate(niveles):
            cy = cy_inicio + i * sep_fila

            # Etiqueta del nivel (con color de dificultad)
            tag_rect = pygame.Rect(x_row, cy - s(18), tag_w, s(36))
            pygame.draw.rect(self.screen, color_tag, tag_rect, border_radius=s(8))
            sf = self.fuentes["instruccion"].render(f"{nivel} ({dificultad})", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(midleft=(x_row + s(8), cy)))

            # Mini diagrama: n figuras pequenas, la primera y la ultima son iguales (circulo rojo)
            # las del medio son diferentes (cuadrado azul)
            formas_seq  = ["circulo"] + ["cuadrado"] * (n_figuras - 2) + ["circulo"]
            colores_seq = [(220, 60, 60)] + [(60, 100, 220)] * (n_figuras - 2) + [(220, 60, 60)]

            for j, (forma, color_f) in enumerate(zip(formas_seq, colores_seq)):
                cx_f = cx_fig_0 + j * sep_fig
                # Resaltamos la ultima figura (la que se compara) con borde blanco
                es_ultima = (j == n_figuras - 1)
                if es_ultima:
                    pygame.draw.circle(self.screen, COLOR_TITULO, (cx_f, cy), s(18))
                dibujar_figura(self.screen, forma, color_f, cx_f, cy, s(14))
                # Flecha entre figuras (excepto despues de la ultima)
                if j < n_figuras - 1:
                    x_flecha = cx_f + s(16)
                    pygame.draw.line(self.screen, COLOR_PIE,
                                     (x_flecha, cy), (x_flecha + s(18), cy), s(2))
                    pygame.draw.polygon(self.screen, COLOR_PIE, [
                        (x_flecha + s(18), cy - s(5)),
                        (x_flecha + s(26), cy),
                        (x_flecha + s(18), cy + s(5)),
                    ])

    # ── Slide 5: boton de pausa y opciones que aparecen ─────────
    def _visual_slide_5(self):
        # Boton II grande centrado arriba
        cx  = ANCHO // 2
        cy0 = s(310)
        btn_p = pygame.Rect(cx - s(45), cy0 - s(35), s(90), s(70))
        pygame.draw.rect(self.screen, COLOR_AMARILLO, btn_p, border_radius=s(14))
        sf = self.fuentes["grande"].render("II", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=btn_p.center))

        # Las tres opciones que aparecen al pausar
        opciones = [
            ("Reanudar",      COLOR_VERDE),
            ("Reiniciar",     COLOR_ROJO),
            ("Volver al menú", COLOR_AMARILLO),
        ]
        ancho_btn = s(210)
        alto_btn  = s(48)
        sep_btn   = s(58)
        cy_opciones = cy0 + s(85)

        for j, (texto, color) in enumerate(opciones):
            cy_b = cy_opciones + j * sep_btn
            rect = pygame.Rect(cx - ancho_btn // 2, cy_b - alto_btn // 2, ancho_btn, alto_btn)
            pygame.draw.rect(self.screen, color, rect, border_radius=s(10))
            sf = self.fuentes["instruccion"].render(texto, True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=rect.center))

    # ── Slide 6: círculo grande con tilde para indicar "listo" ──
    def _visual_slide_6(self):
        cx    = ANCHO // 2
        cy    = s(440)
        radio = s(80)

        # Círculo verde con borde iluminado
        pygame.draw.circle(self.screen, COLOR_BOTON_ACTIVO, (cx, cy), radio)
        pygame.draw.circle(self.screen, COLOR_LINEA,        (cx, cy), radio, s(4))

        # Tilde (checkmark) dibujada con dos segmentos de linea
        p1 = (cx - s(32), cy)
        p2 = (cx - s(10), cy + s(28))
        p3 = (cx + s(38), cy - s(28))
        pygame.draw.lines(self.screen, COLOR_TITULO, False, [p1, p2, p3], s(7))

    # ── Puntos de progreso tipo app movil ────────────────────────
    def _dibujar_progreso(self):
        total     = self.N_SLIDES
        sep       = s(28)
        cx_inicio = ANCHO // 2 - (total - 1) * sep // 2
        cy        = ALTO - s(143)

        for i in range(total):
            cx = cx_inicio + i * sep
            if i == self.slide_actual:
                pygame.draw.circle(self.screen, COLOR_TITULO,       (cx, cy), s(9))   # activo: blanco
            else:
                pygame.draw.circle(self.screen, COLOR_BOTON_ACTIVO, (cx, cy), s(6))   # inactivo: verde

    # ── Botones "Anterior", "Saltear" y "Siguiente" / "Iniciar" ──
    def _dibujar_botones_nav(self):
        # Boton ANTERIOR: solo se muestra si hay slides previos
        if self.slide_actual > 0:
            c = COLOR_BOTON_HOVER if self.hover_ant else COLOR_BOTON_ACTIVO
            pygame.draw.rect(self.screen, c, self.boton_anterior, border_radius=s(14))
            sf = self.fuentes["boton"].render("← Anterior", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.boton_anterior.center))

        # Boton SALTEAR: solo visible si no estamos en el ultimo slide
        if self.slide_actual < self.N_SLIDES - 1:
            c = COLOR_BOTON_GRIS if not self.hover_salt else (90, 100, 92)
            pygame.draw.rect(self.screen, c, self.boton_saltear, border_radius=s(14))
            sf = self.fuentes["boton"].render("Saltear", True, COLOR_PIE)
            self.screen.blit(sf, sf.get_rect(center=self.boton_saltear.center))

        # Boton SIGUIENTE (verde en el ultimo slide, donde cambia a "Iniciar")
        if self.slide_actual < self.N_SLIDES - 1:
            texto = "Siguiente →"
            color = COLOR_BOTON_HOVER if self.hover_sig else COLOR_BOTON_ACTIVO
        else:
            texto = "Iniciar"
            color = COLOR_VERDE_HOVER if self.hover_sig else COLOR_VERDE

        pygame.draw.rect(self.screen, color, self.boton_siguiente, border_radius=s(14))
        sf = self.fuentes["boton"].render(texto, True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.boton_siguiente.center))


# ════════════════════════════════════════════════════════════
#  PANTALLA 4: SELECTOR DE NIVEL
# ════════════════════════════════════════════════════════════
class SelectorNivelNBack:
    def __init__(self, screen, fuentes):
        self.screen        = screen
        self.fuentes       = fuentes
        self.siguiente     = None
        self.nivel_elegido = None  # se llena cuando el terapeuta hace clic en un nivel
        self.boton_x       = pygame.Rect(s(20), s(20), s(52), s(52))
        self.hover_x       = False

        # Los tres niveles disponibles: 1-Back (fácil), 2-Back (medio), 3-Back (difícil)
        ab = s(380); alt = s(100); xc = (ANCHO-ab)//2; yi = s(230)
        self.niveles = [
            {"nivel":1, "texto":"1-Back  (Fácil)",   "desc":"Compara con la figura anterior",
             "rect":pygame.Rect(xc, yi,          ab, alt), "hover":False},
            {"nivel":2, "texto":"2-Back  (Medio)",   "desc":"Compara con la figura de hace 2 pasos",
             "rect":pygame.Rect(xc, yi+s(130),   ab, alt), "hover":False},
            {"nivel":3, "texto":"3-Back  (Difícil)", "desc":"Compara con la figura de hace 3 pasos",
             "rect":pygame.Rect(xc, yi+s(260),   ab, alt), "hover":False},
        ]

    def manejar_eventos(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            p = ev.pos
            self.hover_x = self.boton_x.collidepoint(p)
            for n in self.niveles: n["hover"] = n["rect"].collidepoint(p)
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            p = ev.pos
            if self.boton_x.collidepoint(p):
                self.siguiente = "cognitivo"; return
            for n in self.niveles:
                if n["rect"].collidepoint(p):
                    # Guardamos el nivel elegido y pasamos al formulario de paciente
                    self.nivel_elegido = n["nivel"]
                    self.siguiente     = "form_paciente_nback"; return

    def dibujar(self):
        self.screen.fill(COLOR_FONDO)
        # Botón X para volver al menú cognitivo
        cx = COLOR_ROJO_HOVER if self.hover_x else COLOR_ROJO
        pygame.draw.rect(self.screen, cx, self.boton_x, border_radius=s(10))
        sf = self.fuentes["boton"].render("X", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.boton_x.center))
        pygame.draw.line(self.screen, COLOR_LINEA, (s(60),s(100)), (ANCHO-s(60),s(100)), 2)
        sf = self.fuentes["titulo"].render("Selecciona el nivel", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, s(60))))
        for n in self.niveles:
            # El color del botón cambia cuando el mouse está encima
            c = COLOR_BOTON_HOVER if n["hover"] else COLOR_BOTON_ACTIVO
            pygame.draw.rect(self.screen, c, n["rect"], border_radius=s(14))
            # Nombre del nivel en la parte superior del botón
            sf = self.fuentes["boton"].render(n["texto"], True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(midleft=(n["rect"].left+s(25), n["rect"].centery-s(16))))
            # Descripción breve debajo del nombre
            sf = self.fuentes["descripcion"].render(n["desc"], True, COLOR_DESCRIPCION)
            self.screen.blit(sf, sf.get_rect(midleft=(n["rect"].left+s(25), n["rect"].centery+s(18))))


# ════════════════════════════════════════════════════════════
#  PANTALLA 5: FORMULARIO DE PACIENTE
# ════════════════════════════════════════════════════════════
class FormularioPaciente:
    def __init__(self, screen, fuentes, nivel_nback, test_tipo="nback", cantidad=None):
        self.screen        = screen
        self.fuentes       = fuentes
        self.nivel_nback   = nivel_nback   # para nback: entero 1/2/3; para stroop: string "fácil"/"intermedio"/"dificil"
        self.test_tipo     = test_tipo     # "nback" o "stroop"
        self.cantidad      = cantidad      # solo usado por stroop (cantidad de estimulos)
        self.siguiente     = None
        self.nombre_texto  = ""
        self.id_texto      = ""
        self.campo_activo  = "nombre"
        self.rect_nombre   = pygame.Rect(ANCHO//2-s(200), s(300), s(400), s(55))
        self.rect_id       = pygame.Rect(ANCHO//2-s(200), s(420), s(400), s(55))
        self.boton_cont    = pygame.Rect(ANCHO//2-s(150), s(530), s(300), s(55))
        self.boton_x       = pygame.Rect(s(20), s(20), s(52), s(52))
        self.hover_cont    = False
        self.hover_x       = False
        self.mensaje_error = ""

    def manejar_eventos(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            p = ev.pos
            self.hover_cont = self.boton_cont.collidepoint(p)
            self.hover_x    = self.boton_x.collidepoint(p)
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            p = ev.pos
            if self.boton_x.collidepoint(p):
                self.siguiente = "cognitivo"; return
            if self.rect_nombre.collidepoint(p): self.campo_activo = "nombre"
            elif self.rect_id.collidepoint(p):   self.campo_activo = "id"
            if self.boton_cont.collidepoint(p):  self._validar()
        if ev.type == pygame.KEYDOWN:
            self._teclado(ev)

    def _teclado(self, ev):
        # TAB alterna entre el campo nombre y el campo ID
        if ev.key == pygame.K_TAB:
            self.campo_activo = "id" if self.campo_activo == "nombre" else "nombre"
        # ENTER actúa igual que hacer clic en "Continuar"
        elif ev.key == pygame.K_RETURN:
            self._validar()
        # BACKSPACE borra el último carácter del campo activo
        elif ev.key == pygame.K_BACKSPACE:
            if self.campo_activo == "nombre": self.nombre_texto = self.nombre_texto[:-1]
            else:                              self.id_texto     = self.id_texto[:-1]
        elif ev.unicode and ev.unicode.isprintable():
            # Campo nombre: acepta cualquier caracter imprimible, máximo 40
            if self.campo_activo == "nombre" and len(self.nombre_texto) < 40:
                self.nombre_texto += ev.unicode
            # Campo ID: solo acepta dígitos, máximo 10
            elif self.campo_activo == "id" and ev.unicode.isdigit() and len(self.id_texto) < 10:
                self.id_texto += ev.unicode

    def _validar(self):
        n = self.nombre_texto.strip()
        i = self.id_texto.strip()
        # Validaciones básicas: campos no vacíos y que el ID sea numérico
        if not n:  self.mensaje_error = "Por favor ingresa el nombre del paciente."; return
        if not i:  self.mensaje_error = "Por favor ingresa el ID (solo numeros).";   return
        if not i.isdigit(): self.mensaje_error = "El ID debe contener solo numeros."; return
        # Verificar que el ID no este registrado con otro nombre
        # Esto evita que dos pacientes distintos tengan el mismo ID,
        # lo que mezclaría sus resultados en el mismo archivo JSON.
        nombre_limpio = re.sub(r"\s+", "_", n.lower())
        nombre_limpio = re.sub(r"[^a-zA-Z0-9_\-]", "", nombre_limpio)
        archivo_esperado = f"{i}_{nombre_limpio}.json"
        if os.path.exists(CARPETA_RESULTADOS):
            for archivo in os.listdir(CARPETA_RESULTADOS):
                if archivo.startswith(i + "_") and archivo.endswith(".json"):
                    if archivo != archivo_esperado:
                        self.mensaje_error = f"El ID {i} ya pertenece a otro paciente. Verificá los datos."
                        return
        self.mensaje_error = ""
        # Dependiendo del tipo de test, la tupla que se pasa al loop tiene distintos campos.
        # El loop principal en main() lee self.siguiente para saber qué pantalla crear.
        if self.test_tipo == "stroop":
            self.siguiente = ("test_stroop", self.nivel_nback, self.cantidad, n, i)
        elif self.test_tipo == "avd":
            self.siguiente = ("test_avd", self.nivel_nback, n, i)
        else:
            self.siguiente = ("test_nback", self.nivel_nback, n, i)

    def dibujar(self):
        self.screen.fill(COLOR_FONDO)
        cx = COLOR_ROJO_HOVER if self.hover_x else COLOR_ROJO
        pygame.draw.rect(self.screen, cx, self.boton_x, border_radius=s(10))
        sf = self.fuentes["boton"].render("X", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.boton_x.center))
        pygame.draw.line(self.screen, COLOR_LINEA, (s(60),s(100)), (ANCHO-s(60),s(100)), 2)
        sf = self.fuentes["titulo"].render("Datos del paciente", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, s(60))))
        sf = self.fuentes["subtitulo"].render(
            "Estos datos se guardarán en el archivo de resultados", True, COLOR_SUBTITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, s(180))))

        for etiq, rect, texto, campo in [
            ("Nombre del paciente:", self.rect_nombre, self.nombre_texto, "nombre"),
            ("ID del paciente (sólo números):", self.rect_id, self.id_texto, "id"),
        ]:
            sf = self.fuentes["instruccion"].render(etiq, True, COLOR_TITULO)
            self.screen.blit(sf, (rect.x, rect.y - s(30)))
            borde = COLOR_VERDE if self.campo_activo == campo else (80,100,85)
            pygame.draw.rect(self.screen, (25,60,40), rect, border_radius=s(8))
            pygame.draw.rect(self.screen, borde, rect, 2, border_radius=s(8))
            sf = self.fuentes["input"].render(texto, True, COLOR_TITULO)
            self.screen.blit(sf, (rect.x+s(12), rect.y+s(14)))
            if self.campo_activo == campo and (pygame.time.get_ticks()//500)%2==0:
                cx2 = rect.x + s(12) + self.fuentes["input"].size(texto)[0]
                pygame.draw.line(self.screen, COLOR_TITULO, (cx2, rect.y+s(10)), (cx2, rect.y+s(42)), 2)

        if self.mensaje_error:
            sf = self.fuentes["instruccion"].render(self.mensaje_error, True, (220,80,80))
            self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, s(500))))

        cc = COLOR_VERDE_HOVER if self.hover_cont else COLOR_VERDE
        pygame.draw.rect(self.screen, cc, self.boton_cont, border_radius=s(14))
        sf = self.fuentes["boton"].render("Continuar", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.boton_cont.center))

        sf = self.fuentes["etiqueta"].render(
            "Usa TAB para cambiar de campo, ENTER para continuar", True, COLOR_PIE)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, ALTO-s(30))))


# ════════════════════════════════════════════════════════════
#  FIGURAS GEOMETRICAS
# ════════════════════════════════════════════════════════════
FORMAS = ["circulo","triangulo","cuadrado","ovalo","estrella"]
COLORES_FIGURA = [
    ("rojo",    (220, 60, 60)),
    ("azul",    ( 60,100,220)),
    ("amarillo",(220,200, 40)),
    ("naranja", (220,130, 40)),
    ("violeta", (150, 60,200)),
    ("celeste", ( 80,180,220)),
]

def dibujar_figura(surface, forma, color_rgb, cx, cy, tam=None):
    # Dibuja la figura geométrica indicada, centrada en (cx, cy), con tamaño tam.
    # Si no se pasa tam, usa el valor por defecto escalado.
    if tam is None: tam = s(80)
    if forma == "circulo":
        pygame.draw.circle(surface, color_rgb, (cx,cy), tam)
    elif forma == "cuadrado":
        # El cuadrado se construye a partir del centro, restando tam en cada dirección
        pygame.draw.rect(surface, color_rgb,
                         pygame.Rect(cx-tam, cy-tam, tam*2, tam*2), border_radius=s(10))
    elif forma == "triangulo":
        # Vértice arriba al centro, base en la parte inferior
        pygame.draw.polygon(surface, color_rgb,
                            [(cx, cy-tam),(cx-tam, cy+tam),(cx+tam, cy+tam)])
    elif forma == "ovalo":
        # El óvalo es un elipse más ancho que alto (ratio 2:1)
        pygame.draw.ellipse(surface, color_rgb,
                            pygame.Rect(cx-tam, cy-tam//2, tam*2, tam))
    elif forma == "estrella":
        # Dibujamos la estrella de 5 puntas con 10 vértices alternando radio externo e interno
        pts = []
        for i in range(10):
            ang = math.pi/5*i - math.pi/2
            r   = tam if i%2==0 else tam//2  # puntas externas (par) vs internas (impar)
            pts.append((cx + r*math.cos(ang), cy + r*math.sin(ang)))
        pygame.draw.polygon(surface, color_rgb, pts)

def generar_secuencia_nback(n, total=25):
    # Genera la secuencia de figuras para el test N-Back.
    # n     = nivel del test (1, 2 o 3): define cuántos pasos atrás debe recordar el paciente.
    # total = cantidad total de figuras en la secuencia (25 por defecto).

    # Los primeros n estímulos son "de calentamiento": el paciente no puede responder
    # porque todavía no tiene n figuras previas para comparar. Se marcan como None.
    # A partir del estímulo n, el paciente ya puede comparar con la figura de hace n pasos.
    posibles    = list(range(n, total))   # índices donde sí se puede evaluar

    # Aproximadamente el 30% de los estímulos evaluables serán coincidencias
    n_coinc     = round(len(posibles) * 0.30)
    coincidencias = set(random.sample(posibles, n_coinc))  # índices que serán iguales a la de n pasos antes

    secuencia   = []  # lista de dicts con la figura a mostrar en cada paso
    es_coinc    = []  # lista paralela: True si coincide, False si no, None si es calentamiento

    for i in range(total):
        if i < n:
            # Figuras de calentamiento: completamente aleatorias, no se evalúan
            f = random.choice(FORMAS); c = random.choice(COLORES_FIGURA)
            secuencia.append({"forma":f,"color_nombre":c[0],"color_rgb":c[1]})
            es_coinc.append(None)
        elif i in coincidencias:
            # Figura de coincidencia: exactamente igual a la de n pasos antes
            ref = secuencia[i-n]
            secuencia.append(dict(ref)); es_coinc.append(True)
        else:
            # Figura distinta: intentamos hasta 30 veces que sea diferente (forma O color)
            # para evitar coincidencias accidentales
            ref = secuencia[i-n]
            for _ in range(30):
                f = random.choice(FORMAS); c = random.choice(COLORES_FIGURA)
                if f != ref["forma"] or c[0] != ref["color_nombre"]: break
            secuencia.append({"forma":f,"color_nombre":c[0],"color_rgb":c[1]})
            es_coinc.append(False)

    return secuencia, es_coinc  # devolvemos ambas listas para usarlas en el test


# ════════════════════════════════════════════════════════════
#  COLORES DEL TEST STROOP
#  Los nombres de los colores que aparecen como palabras y
#  como tinta. Son distintos del COLOR_VERDE de la paleta de
#  la app (ese es el verde oscuro de los botones).
# ════════════════════════════════════════════════════════════
STROOP_NOMBRES  = ["ROJO", "AZUL", "VERDE", "AMARILLO"]
STROOP_TINTA_RGB = {
    "ROJO":     (220,  50,  50),   # rojo vivo
    "AZUL":     ( 50, 100, 230),   # azul medio
    "VERDE":    ( 50, 200, 100),   # verde claro (distinto al verde de la app)
    "AMARILLO": (220, 200,   0),   # amarillo dorado
}


# ════════════════════════════════════════════════════════════
#  PANTALLA 6: TEST N-BACK
# ════════════════════════════════════════════════════════════
class TestNBack:
    # Bibliografía: protocolo estándar usa 500ms de figura + 2500ms de respuesta
    # (Kirchner 1958; Owen et al. 2005). Para pacientes post-ACV: figura mostrada 1000ms,
    # sin límite de tiempo de respuesta. Los botones aparecen junto con la figura.
    TIEMPO_FIGURA_MS    = 1000   # ms que se muestra la figura (y desde cuándo se mide el TR)
    TOTAL               = 25

    def __init__(self, screen, fuentes, nivel, nombre, id_pac):
        self.screen   = screen
        self.fuentes  = fuentes
        self.nivel    = nivel
        self.nombre   = nombre
        self.id_pac   = id_pac
        self.siguiente = None
        self._reiniciar()

    def _reiniciar(self):
        # Genera una nueva secuencia aleatoria con el nivel actual
        self.secuencia, self.es_coinc = generar_secuencia_nback(self.nivel, self.TOTAL)
        self.idx         = 0
        self.estado      = "mostrando"   # estados posibles: mostrando | flash | fin
        self.pausado     = False

        # Sistema de temporizado:
        # t_inicio: momento en que empezó el estímulo actual
        # t_pausa_acum: suma de todos los milisegundos pausados en el estímulo actual
        # t_pausa_ini: momento en que se inició la última pausa (para calcular su duración)
        self.t_inicio    = pygame.time.get_ticks()
        self.t_pausa_acum = 0
        self.t_pausa_ini  = 0

        # El tiempo de reacción se mide desde que aparece la figura (no desde un estado aparte)
        # t_respuesta: momento exacto en que apareció la figura (inicio del cronómetro de RT)
        # t_pausa_acum_respuesta: snapshot de t_pausa_acum en ese momento, para descontar pausas posteriores
        self.t_respuesta  = pygame.time.get_ticks()
        self.t_pausa_acum_respuesta = 0
        self.respuestas   = []
        self.guardado     = False
        self.ruta_guardado = ""

        # Superficie de fondo negro para el "flash" entre figuras
        self.mostrando_flash = False
        self.t_flash_ini     = 0
        FLASH_MS             = 300   # ms de pantalla negra entre figuras (evita que dos figuras iguales parezcan estáticas)

        # Botones
        cx = ANCHO//2
        self.btn_si      = pygame.Rect(cx-s(220), ALTO-s(130), s(180), s(70))
        self.btn_no      = pygame.Rect(cx+s(40),  ALTO-s(130), s(180), s(70))
        self.btn_pausa   = pygame.Rect(ANCHO-s(90), s(20),     s(65),  s(55))
        bw = s(300)
        self.btn_reanudar  = pygame.Rect(ANCHO//2-bw//2, s(290), bw, s(65))
        self.btn_reiniciar = pygame.Rect(ANCHO//2-bw//2, s(375), bw, s(65))
        self.btn_menu      = pygame.Rect(ANCHO//2-bw//2, s(460), bw, s(65))
        self.btn_guardar   = pygame.Rect(ANCHO//2-s(320), s(440), s(280), s(65))
        self.btn_eliminar  = pygame.Rect(ANCHO//2+s(40),  s(440), s(280), s(65))
        # Botón de observaciones: centrado debajo de guardar/eliminar
        self.btn_observaciones = pygame.Rect(ANCHO//2-s(255), s(530), s(510), s(62))

        # Estado del panel de observaciones
        self.modo_observaciones  = False   # True cuando el overlay de obs está abierto
        self.texto_observaciones = ""      # texto que escribe el terapeuta
        # Botones dentro del overlay de observaciones (posición relativa al panel)
        panel_y = ALTO // 2 - s(245)
        self.btn_guardar_obs    = pygame.Rect(ANCHO//2-s(330), panel_y+s(325), s(660), s(62))
        self.btn_descartar_obs  = pygame.Rect(ANCHO//2-s(220), panel_y+s(407), s(440), s(58))

        self.hov = {k: False for k in
                    ["si","no","pausa","reanudar","reiniciar","menú","guardar","eliminar",
                     "observaciones","guardar_obs","descartar_obs"]}
        self.FLASH_MS = 300

    def _elapsed(self):
        # Devuelve el tiempo transcurrido en el estímulo actual, sin contar los milisegundos pausados.
        # Si estamos en pausa, calculamos hasta el momento en que se pausó (no seguimos contando).
        if self.pausado:
            return self.t_pausa_ini - self.t_inicio - self.t_pausa_acum
        return pygame.time.get_ticks() - self.t_inicio - self.t_pausa_acum

    def _registrar(self, resp):
        # Guarda la respuesta del paciente para el estímulo actual.
        # resp = True (dijo SI), False (dijo NO), o None (no respondió / estímulo de calentamiento)
        fig = self.secuencia[self.idx]
        era = self.es_coinc[self.idx]  # True si era coincidencia, False si no, None si era calentamiento

        # Calculamos el tiempo de reacción descontando las pausas que hubiera durante este estímulo
        if self.t_respuesta and resp is not None:
            # Solo restamos las pausas que ocurrieron desde que empezó "preguntando"
            rt = pygame.time.get_ticks() - self.t_respuesta - (self.t_pausa_acum - self.t_pausa_acum_respuesta)
        else:
            rt = None  # no hay RT para los estímulos de calentamiento o si no respondió

        # Clasificamos el tipo de error:
        # - era=None: estímulo de calentamiento, no se evalúa
        # - resp=None y era=True: el paciente no respondió cuando debía → OMISIÓN
        # - resp != era: el paciente respondió mal
        #   · dijo SI cuando no había coincidencia → COMISIÓN (falsa alarma)
        #   · dijo NO cuando sí había coincidencia → OMISIÓN
        if era is None:
            correcto = tipo = None
        elif resp is None:
            tipo     = "omisión" if era else None
            correcto = not era
        elif resp == era:
            tipo = None; correcto = True
        else:
            tipo     = "comisión" if resp else "omisión"
            correcto = False

        self.respuestas.append({
            "estimulo": self.idx+1,
            "forma": fig["forma"], "color": fig["color_nombre"],
            "era_coincidencia": era,
            "respuesta": resp, "correcto": correcto,
            "tipo_error": tipo, "rt_ms": rt,
        })

    def _siguiente(self):
        # Avanza al próximo estímulo o termina el test si ya se mostraron todos
        self.idx += 1
        if self.idx >= self.TOTAL:
            self.estado = "fin"
        else:
            # Antes de mostrar la siguiente figura, mostramos un flash breve (pantalla oscura)
            # para que dos figuras iguales seguidas no parezcan estáticas
            self.estado      = "flash"
            self.t_flash_ini = pygame.time.get_ticks()
            self.t_inicio    = pygame.time.get_ticks()
            self.t_pausa_acum = 0
            # t_respuesta se actualiza cuando termina el flash y empieza "mostrando"
            self.t_respuesta  = None

    def _metricas(self):
        # Calcula los resultados finales del test. Solo considera los estímulos evaluables
        # (los de calentamiento con era_coincidencia=None se excluyen).
        validas    = [r for r in self.respuestas if r["era_coincidencia"] is not None]
        total      = len(validas)
        if total == 0: return {}
        correctas  = sum(1 for r in validas if r["correcto"])
        omisiones  = sum(1 for r in validas if r["tipo_error"]=="omisión")
        comisiones = sum(1 for r in validas if r["tipo_error"]=="comisión")
        precision  = round(correctas/total*100, 1)

        # Tiempo de reacción promedio (solo para respuestas con RT medido, ignorando omisiones)
        tiempos    = [r["rt_ms"] for r in validas if r["rt_ms"] is not None]
        rt_prom    = round(sum(tiempos)/len(tiempos)) if tiempos else None

        # Rangos normales según bibliografía, uno por nivel
        rangos = {1:{"min":85,"max":95,"fuente":"Kane et al. (2007)"},
                  2:{"min":75,"max":85,"fuente":"Owen et al. (2005)"},
                  3:{"min":65,"max":75,"fuente":"Vermeij et al. (2012)"}}
        r = rangos[self.nivel]
        # Clasificación: Normal si está dentro del rango, Limítrofe si está hasta 10% debajo, Patológico si baja más
        clasif = "Normal" if precision>=r["min"] else ("Limítrofe" if precision>=r["min"]-10 else "Patológico")
        return {"nivel_nback":self.nivel,"estimulos_evaluados":total,
                "respuestas_correctas":correctas,"errores_omision":omisiones,
                "errores_comision":comisiones,"precision_porcentaje":precision,
                "tiempo_reaccion_promedio_ms":rt_prom,
                "rango_esperado_precision":f"{r['min']}-{r['max']}%",
                "fuente_rango":r["fuente"],"clasificacion":clasif}

    def manejar_eventos(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            p = ev.pos
            self.hov["si"]      = self.btn_si.collidepoint(p)
            self.hov["no"]      = self.btn_no.collidepoint(p)
            self.hov["pausa"]   = self.btn_pausa.collidepoint(p)
            if self.pausado:
                self.hov["reanudar"]  = self.btn_reanudar.collidepoint(p)
                self.hov["reiniciar"] = self.btn_reiniciar.collidepoint(p)
                self.hov["menú"]      = self.btn_menu.collidepoint(p)
            if self.estado == "fin":
                self.hov["guardar"]       = self.btn_guardar.collidepoint(p)
                self.hov["eliminar"]      = self.btn_eliminar.collidepoint(p)
                self.hov["observaciones"] = self.btn_observaciones.collidepoint(p)
            if self.modo_observaciones:
                self.hov["guardar_obs"]    = self.btn_guardar_obs.collidepoint(p)
                self.hov["descartar_obs"]  = self.btn_descartar_obs.collidepoint(p)

        # Captura de texto del teclado cuando el overlay de observaciones está abierto
        if ev.type == pygame.KEYDOWN and self.modo_observaciones:
            if ev.key == pygame.K_BACKSPACE:
                self.texto_observaciones = self.texto_observaciones[:-1]
            elif ev.key == pygame.K_RETURN:
                self.texto_observaciones += "\n"
            elif ev.unicode and ev.unicode.isprintable():
                self.texto_observaciones += ev.unicode
            return   # ninguna otra acción mientras se escribe

        # ── Atajos de teclado para el test N-Back ─────────────────────────
        if ev.type == pygame.KEYDOWN and not self.modo_observaciones:
            if self.pausado:
                # Espacio reanuda la pausa
                if ev.key == pygame.K_SPACE:
                    self.t_pausa_acum += pygame.time.get_ticks() - self.t_pausa_ini
                    self.pausado = False
            elif self.estado == "mostrando" and self.es_coinc[self.idx] is not None:
                # Flecha izquierda = SI, flecha derecha = NO
                if ev.key == pygame.K_LEFT:
                    self._registrar(True); self._siguiente()
                elif ev.key == pygame.K_RIGHT:
                    self._registrar(False); self._siguiente()
                elif ev.key == pygame.K_SPACE:
                    # Espacio también pausa durante el test
                    self.pausado = True; self.t_pausa_ini = pygame.time.get_ticks()
            elif self.estado not in ("fin",):
                # Espacio pausa el test en cualquier momento (no en pantalla de fin)
                if ev.key == pygame.K_SPACE:
                    self.pausado = True; self.t_pausa_ini = pygame.time.get_ticks()

        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            p = ev.pos

            # Si el overlay de observaciones está abierto, solo sus botones responden
            if self.modo_observaciones:
                if self.btn_guardar_obs.collidepoint(p):
                    # Guarda los resultados incluyendo las observaciones escritas
                    m = self._metricas()
                    self.ruta_guardado = guardar_json(
                        self.id_pac, self.nombre, "Memoria N-Back", m,
                        observaciones=self.texto_observaciones)
                    self.guardado = True
                    self.modo_observaciones = False
                    # Reposicionar el botón "Volver al menú" al centro
                    self.btn_eliminar = pygame.Rect(ANCHO//2 - s(140), s(440), s(280), s(65))
                elif self.btn_descartar_obs.collidepoint(p):
                    # Descarta solo el texto de observaciones; vuelve a la pantalla de fin
                    self.texto_observaciones = ""
                    self.modo_observaciones  = False
                return

            if self.pausado:
                if self.btn_reanudar.collidepoint(p):
                    self.t_pausa_acum += pygame.time.get_ticks() - self.t_pausa_ini
                    self.pausado = False
                elif self.btn_reiniciar.collidepoint(p): self._reiniciar()
                elif self.btn_menu.collidepoint(p):      self.siguiente = "cognitivo"
                return
            if self.estado == "fin":
                if self.btn_guardar.collidepoint(p) and not self.guardado:
                    m = self._metricas()
                    self.ruta_guardado = guardar_json(self.id_pac, self.nombre, "Memoria N-Back", m)
                    self.guardado = True
                    # Reposicionar el botón al centro ahora que es el único botón
                    self.btn_eliminar = pygame.Rect(ANCHO//2 - s(140), s(440), s(280), s(65))
                elif self.btn_eliminar.collidepoint(p):
                    self.siguiente = "cognitivo"
                elif self.btn_observaciones.collidepoint(p) and not self.guardado:
                    # Abre el overlay para que el terapeuta escriba observaciones
                    self.modo_observaciones = True
                return
            # Boton pausa solo si el test está corriendo
            if self.btn_pausa.collidepoint(p) and self.estado not in ("fin",):
                self.pausado = True; self.t_pausa_ini = pygame.time.get_ticks(); return
            if self.estado == "mostrando" and self.es_coinc[self.idx] is not None:
                if self.btn_si.collidepoint(p):
                    self._registrar(True); self._siguiente()
                elif self.btn_no.collidepoint(p):
                    self._registrar(False); self._siguiente()

    def actualizar(self):
        # Esta función se llama en cada frame del loop principal para avanzar el estado interno del test.
        # Si el test está pausado o terminado, no hace nada.
        if self.pausado or self.estado == "fin": return
        t = self._elapsed()

        if self.estado == "flash":
            # Esperamos FLASH_MS milisegundos antes de mostrar la siguiente figura
            if pygame.time.get_ticks() - self.t_flash_ini >= self.FLASH_MS:
                self.estado   = "mostrando"
                self.t_inicio = pygame.time.get_ticks()
                self.t_pausa_acum = 0
                # El TR se mide desde que aparece la figura
                self.t_respuesta = pygame.time.get_ticks()
                self.t_pausa_acum_respuesta = 0

        elif self.estado == "mostrando":
            # Los primeros N estímulos son de calentamiento: el paciente los ve pero no responde.
            # Después de TIEMPO_FIGURA_MS, avanzan solos (registramos None como respuesta).
            if self.es_coinc[self.idx] is None and t >= self.TIEMPO_FIGURA_MS:
                self._registrar(None); self._siguiente()
            # Los estímulos evaluables esperan la respuesta del paciente sin límite de tiempo

    def dibujar(self):
        self.screen.fill(COLOR_FONDO)

        # Encabezado
        pygame.draw.line(self.screen, COLOR_LINEA, (s(60),s(75)), (ANCHO-s(60),s(75)), 2)
        sf = self.fuentes["casa"].render(
            f"Memoria N-Back  |  Nivel: {self.nivel}-Back  |  "
            f"Figura: {min(self.idx+1,self.TOTAL)}/{self.TOTAL}",
            True, COLOR_SUBTITULO)
        self.screen.blit(sf, sf.get_rect(midleft=(s(60), s(45))))

        # Boton pausa (solo si el test no termino)
        if self.estado != "fin":
            cp = COLOR_AMARILLO_HOVER if self.hov["pausa"] else COLOR_AMARILLO
            pygame.draw.rect(self.screen, cp, self.btn_pausa, border_radius=s(10))
            sf = self.fuentes["boton"].render("II", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.btn_pausa.center))

        if self.estado == "fin":
            self._dibujar_fin()
            # Si está abierto el overlay de observaciones, lo dibuja encima de todo
            if self.modo_observaciones:
                dibujar_overlay_observaciones(
                    self.screen, self.fuentes, self.texto_observaciones,
                    self.hov, self.btn_guardar_obs, self.btn_descartar_obs)
            return

        # Estado flash: pantalla oscura entre figuras, sin mostrar nada
        if self.estado == "flash":
            if self.pausado:
                self._dibujar_pausa()
            return   # Fondo verde oscuro vacío (el flash es simplemente la pantalla de fondo)

        # Dibujamos la figura del estímulo actual en el centro de la pantalla
        if self.idx < self.TOTAL:
            fig = self.secuencia[self.idx]
            dibujar_figura(self.screen, fig["forma"], fig["color_rgb"], ANCHO//2, s(300))
            # Acuerdo de género: "estrella" es femenina → rojo→roja, amarillo→amarilla
            color_display = fig['color_nombre']
            if fig['forma'] == "estrella":
                color_display = {"rojo": "roja", "amarillo": "amarilla"}.get(color_display, color_display)
            # Mostramos el nombre de la figura debajo, como referencia para el paciente
            sf = self.fuentes["descripcion"].render(
                f"{fig['forma'].capitalize()}  {color_display}", True, COLOR_PIE)
            self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, s(430))))

        # Botones SI / NO: solo aparecen para los estímulos evaluables (no para los de calentamiento)
        if self.estado == "mostrando" and self.es_coinc[self.idx] is not None and not self.pausado:
            sf = self.fuentes["subtitulo"].render(
                f"Es igual a la figura de hace {self.nivel} paso(s)?", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, ALTO-s(165))))

            cs = COLOR_VERDE_HOVER if self.hov["si"] else COLOR_VERDE
            pygame.draw.rect(self.screen, cs, self.btn_si, border_radius=s(14))
            sf = self.fuentes["boton"].render("SI", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.btn_si.center))

            cn = COLOR_ROJO_HOVER if self.hov["no"] else COLOR_ROJO
            pygame.draw.rect(self.screen, cn, self.btn_no, border_radius=s(14))
            sf = self.fuentes["boton"].render("NO", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.btn_no.center))

        if self.pausado:
            self._dibujar_pausa()

    def _dibujar_pausa(self):
        ov = pygame.Surface((ANCHO,ALTO), pygame.SRCALPHA)
        ov.fill((0,0,0,160)); self.screen.blit(ov,(0,0))
        caja = pygame.Rect(ANCHO//2-s(210), s(195), s(420), s(370))
        pygame.draw.rect(self.screen, (20,55,35), caja, border_radius=s(18))
        pygame.draw.rect(self.screen, COLOR_LINEA, caja, 2, border_radius=s(18))
        sf = self.fuentes["titulo"].render("Test pausado", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, s(245))))

        for btn, color, hover_color, etiq in [
            (self.btn_reanudar,  COLOR_VERDE,    COLOR_VERDE_HOVER,    "Reanudar"),
            (self.btn_reiniciar, COLOR_ROJO,     COLOR_ROJO_HOVER,     "Reiniciar"),
            (self.btn_menu,      COLOR_AMARILLO, COLOR_AMARILLO_HOVER, "Volver al menú"),
        ]:
            key = etiq.lower().replace(" al menú","").replace(" ","")
            c   = hover_color if self.hov.get(key, False) else color
            pygame.draw.rect(self.screen, c, btn, border_radius=s(12))
            sf = self.fuentes["boton"].render(etiq, True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=btn.center))

    def _dibujar_fin(self):
        sf = self.fuentes["grande"].render("Test finalizado", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, s(185))))

        m = self._metricas()
        if m:
            prec  = m.get("precision_porcentaje",0)
            clas  = m.get("clasificacion","")
            # El color de la clasificación depende del resultado: verde=normal, amarillo=limítrofe, rojo=patológico
            cc    = {"Normal":COLOR_VERDE,"Limítrofe":COLOR_AMARILLO,"Patológico":COLOR_ROJO}.get(clas,COLOR_TITULO)
            sf = self.fuentes["subtitulo"].render(
                f"Precisión: {prec}%     Clasificación: {clas}", True, cc)
            self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, s(265))))
            # Referencia del rango normal con la fuente bibliográfica
            sf = self.fuentes["descripcion"].render(
                f"Rango normal para {self.nivel}-Back: {m.get('rango_esperado_precision','')}  "
                f"({m.get('fuente_rango','')})", True, COLOR_SUBTITULO)
            self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, s(305))))

        pygame.draw.line(self.screen, COLOR_LINEA,
                         (s(60), s(335)), (ANCHO-s(60), s(335)), 1)

        if self.guardado:
            # Una vez guardado, mostramos la ruta del archivo y solo el botón para volver al menú
            sf = self.fuentes["instruccion"].render(
                f"Guardado en: {self.ruta_guardado}", True, COLOR_VERDE)
            self.screen.blit(sf, sf.get_rect(center=(ANCHO//2, s(375))))
            cv = COLOR_VERDE_HOVER if self.hov["eliminar"] else COLOR_VERDE
            pygame.draw.rect(self.screen, cv, self.btn_eliminar, border_radius=s(14))
            sf = self.fuentes["boton"].render("Volver al menú", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.btn_eliminar.center))
        else:
            # Antes de guardar mostramos las tres opciones: guardar, eliminar y agregar observaciones
            cg = COLOR_VERDE_HOVER if self.hov["guardar"] else COLOR_VERDE
            pygame.draw.rect(self.screen, cg, self.btn_guardar, border_radius=s(14))
            sf = self.fuentes["boton"].render("Guardar resultados", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.btn_guardar.center))

            ce = COLOR_ROJO_HOVER if self.hov["eliminar"] else COLOR_ROJO
            pygame.draw.rect(self.screen, ce, self.btn_eliminar, border_radius=s(14))
            sf = self.fuentes["boton"].render("Eliminar intento", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.btn_eliminar.center))

            # Botón azul para agregar observaciones del terapeuta antes de guardar
            co = COLOR_AZUL_HOVER if self.hov["observaciones"] else COLOR_AZUL
            pygame.draw.rect(self.screen, co, self.btn_observaciones, border_radius=s(14))
            sf = self.fuentes["instruccion"].render("Agregar observaciones del terapeuta", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.btn_observaciones.center))


# ════════════════════════════════════════════════════════════
#  PANTALLA 7: INSTRUCCIONES EFECTO STROOP  (carrusel 6 slides)
#  Misma estructura que InstruccionesNBack.
# ════════════════════════════════════════════════════════════
class InstruccionesStroop:

    SLIDES = [
        {
            "titulo": "Efecto Stroop",
            "lineas": [
                "Aparece una palabra escrita en un color.",
                "Tu tarea: indicar el COLOR DE LA TINTA,",
                "no lo que dice la palabra.",
            ]
        },
        {
            "titulo": "Ejemplo: ignora la palabra",
            "lineas": [
                'La palabra dice "VERDE" pero está escrita en AMARILLO.',
                "La respuesta correcta es AMARILLO.",
                "¡El color de la tinta, no lo que dice!",
            ]
        },
        {
            "titulo": "Niveles de dificultad",
            "lineas": [
                "Fácil: la palabra y el color siempre coinciden.",
                "Intermedio: la mitad de las veces no coinciden.",
                "Difícil: nunca coinciden.",
            ]
        },
        {
            "titulo": "Cómo responder",
            "lineas": [
                "Hacé clic en el botón del color de la TINTA,",
                "o usá las teclas V · B · N · M del teclado.",
            ]
        },
        {
            "titulo": "El botón de pausa",
            "lineas": [
                "En cualquier momento podés pausar el test.",
                "Podés pausar con el botón II o con la barra espaciadora.",
                "Al pausar aparecen tres opciones.",
            ]
        },
        {
            "titulo": "¡Todo listo!",
            "lineas": [
                "Vas a ver las palabras de a una.",
                "Recordá: V / B / N / M = colores  |  Espacio = Pausa",
                "Cuando estés listo, presioná Iniciar.",
            ]
        },
    ]

    def __init__(self, screen, fuentes):
        self.screen    = screen
        self.fuentes   = fuentes
        self.siguiente = None
        self.slide_actual = 0
        self.N_SLIDES     = 6

        self.boton_x         = pygame.Rect(s(20), s(20), s(52), s(52))
        self.boton_anterior  = pygame.Rect(s(60),            ALTO - s(120), s(200), s(60))
        self.boton_siguiente = pygame.Rect(ANCHO - s(260),   ALTO - s(120), s(200), s(60))
        self.boton_saltear   = pygame.Rect(ANCHO//2 - s(90), ALTO - s(120), s(180), s(60))

        self.hover_x    = False
        self.hover_ant  = False
        self.hover_sig  = False
        self.hover_salt = False

    def manejar_eventos(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            p = ev.pos
            self.hover_x    = self.boton_x.collidepoint(p)
            self.hover_ant  = (self.slide_actual > 0) and self.boton_anterior.collidepoint(p)
            self.hover_sig  = self.boton_siguiente.collidepoint(p)
            self.hover_salt = (self.slide_actual < self.N_SLIDES - 1) and self.boton_saltear.collidepoint(p)
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            p = ev.pos
            if self.boton_x.collidepoint(p):
                self.siguiente = "cognitivo"; return
            if self.slide_actual < self.N_SLIDES - 1 and self.boton_saltear.collidepoint(p):
                self.slide_actual = self.N_SLIDES - 1; return
            if self.slide_actual > 0 and self.boton_anterior.collidepoint(p):
                self.slide_actual -= 1; return
            if self.boton_siguiente.collidepoint(p):
                if self.slide_actual < self.N_SLIDES - 1:
                    self.slide_actual += 1
                else:
                    self.siguiente = "nivel_stroop"

        # ── Atajos de teclado ──────────────────────────────────────
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RIGHT:               # → Siguiente / Iniciar
                if self.slide_actual < self.N_SLIDES - 1:
                    self.slide_actual += 1
                else:
                    self.siguiente = "nivel_stroop"
            elif ev.key == pygame.K_LEFT:              # ← Anterior
                if self.slide_actual > 0:
                    self.slide_actual -= 1
            elif ev.key == pygame.K_SPACE:             # Espacio → Saltear al ultimo slide
                if self.slide_actual < self.N_SLIDES - 1:
                    self.slide_actual = self.N_SLIDES - 1

    def dibujar(self):
        self.screen.fill(COLOR_FONDO)
        slide = self.SLIDES[self.slide_actual]

        # Encabezado
        sf = self.fuentes["subtitulo"].render("Instrucciones - Efecto Stroop", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(50))))
        pygame.draw.line(self.screen, COLOR_LINEA, (s(60), s(82)), (ANCHO - s(60), s(82)), 2)

        # Boton X
        cx_color = COLOR_ROJO_HOVER if self.hover_x else COLOR_ROJO
        pygame.draw.rect(self.screen, cx_color, self.boton_x, border_radius=s(10))
        sf = self.fuentes["boton"].render("X", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.boton_x.center))

        # Titulo y texto
        y_texto = s(135)
        sf = self.fuentes["boton"].render(slide["titulo"], True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, y_texto)))
        y_texto += s(50)
        for linea in slide["lineas"]:
            sf = self.fuentes["subtitulo"].render(linea, True, COLOR_SUBTITULO)
            self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, y_texto)))
            y_texto += s(36)

        # Visual del slide
        self._dibujar_visual(self.slide_actual)

        # Progreso y navegacion
        self._dibujar_progreso()
        pygame.draw.line(self.screen, COLOR_LINEA,
                         (s(60), ALTO - s(130)), (ANCHO - s(60), ALTO - s(130)), 1)
        self._dibujar_botones_nav()

    def _dibujar_visual(self, idx):
        metodos = [
            self._visual_slide_0,
            self._visual_slide_1,
            self._visual_slide_2,
            self._visual_slide_3,
            self._visual_slide_4,
            self._visual_slide_5,
        ]
        metodos[idx]()

    def _visual_slide_0(self):
        # Palabra "ROJO" escrita en color azul, con flecha señalando la tinta
        cx = ANCHO // 2
        cy = s(400)
        # Tarjeta blanca para contraste
        tarjeta = pygame.Rect(cx - s(160), cy - s(55), s(320), s(110))
        pygame.draw.rect(self.screen, (255, 255, 255), tarjeta, border_radius=s(14))
        # La palabra "ROJO" escrita en tinta azul
        sf = self.fuentes["grande"].render("ROJO", True, STROOP_TINTA_RGB["AZUL"])
        self.screen.blit(sf, sf.get_rect(center=(cx, cy)))
        # Flecha hacia abajo + etiqueta "color de la tinta"
        pygame.draw.line(self.screen, COLOR_PIE, (cx, cy + s(60)), (cx, cy + s(80)), s(3))
        pygame.draw.polygon(self.screen, COLOR_PIE, [
            (cx - s(8), cy + s(77)), (cx, cy + s(90)), (cx + s(8), cy + s(77))
        ])
        sf = self.fuentes["instruccion"].render("color de la TINTA (azul)", True, STROOP_TINTA_RGB["AZUL"])
        self.screen.blit(sf, sf.get_rect(center=(cx, cy + s(105))))

    def _visual_slide_1(self):
        # Palabra "VERDE" en tinta amarilla + 4 botones + flecha al correcto
        cx = ANCHO // 2
        cy_palabra = s(340)
        # Tarjeta blanca para contraste
        tarjeta = pygame.Rect(cx - s(150), cy_palabra - s(48), s(300), s(96))
        pygame.draw.rect(self.screen, (255, 255, 255), tarjeta, border_radius=s(14))
        sf = self.fuentes["grande"].render("VERDE", True, STROOP_TINTA_RGB["AMARILLO"])
        self.screen.blit(sf, sf.get_rect(center=(cx, cy_palabra)))
        # Los 4 botones de respuesta en miniatura
        cy_btns = s(480)
        ancho_b = s(120); alto_b = s(44); sep = s(130)
        x_inicio = cx - sep * 1.5
        for i, nombre in enumerate(STROOP_NOMBRES):
            xb = int(x_inicio + i * sep)
            rect_b = pygame.Rect(xb - ancho_b // 2, cy_btns - alto_b // 2, ancho_b, alto_b)
            # El correcto (AMARILLO) se resalta con borde blanco
            es_correcto = (nombre == "AMARILLO")
            color_fondo = COLOR_BOTON_HOVER if es_correcto else COLOR_BOTON_ACTIVO
            pygame.draw.rect(self.screen, color_fondo, rect_b, border_radius=s(8))
            if es_correcto:
                pygame.draw.rect(self.screen, COLOR_TITULO, rect_b, s(2), border_radius=s(8))
            sf = self.fuentes["descripcion"].render(nombre, True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=rect_b.center))
            # Flecha hacia el boton correcto
            if es_correcto:
                tip_y = rect_b.top - s(4)
                pygame.draw.line(self.screen, COLOR_TITULO, (xb, tip_y - s(22)), (xb, tip_y - s(4)), s(3))
                pygame.draw.polygon(self.screen, COLOR_TITULO, [
                    (xb - s(7), tip_y - s(6)), (xb, tip_y + s(6)), (xb + s(7), tip_y - s(6))
                ])

    def _visual_slide_2(self):
        # 3 botones con el nombre del nivel y su descripcion (sin recuadros de ejemplo)
        niveles_desc = [
            ("Fácil",       "La palabra y el color siempre coinciden",  COLOR_VERDE),
            ("Intermedio",  "La mitad de las veces no coinciden",        COLOR_AMARILLO),
            ("Difícil",     "Las palabras y el color nunca coinciden",   COLOR_ROJO),
        ]
        bw = s(460); bh = s(68); sep_y = s(88)
        cx = ANCHO // 2
        cy_ini = s(360)
        for i, (nivel, desc, color) in enumerate(niveles_desc):
            cy = cy_ini + i * sep_y
            rect = pygame.Rect(cx - bw // 2, cy - bh // 2, bw, bh)
            pygame.draw.rect(self.screen, color, rect, border_radius=s(12))
            sf = self.fuentes["boton"].render(nivel, True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(midleft=(rect.left + s(20), rect.centery - s(10))))
            sf = self.fuentes["descripcion"].render(desc, True, COLOR_DESCRIPCION)
            self.screen.blit(sf, sf.get_rect(midleft=(rect.left + s(20), rect.centery + s(14))))

    def _visual_slide_3(self):
        # Los 4 botones en una sola fila, cada uno con el nombre del color y su tecla asignada
        teclas = ["V", "B", "N", "M"]   # corresponden a ROJO, AZUL, VERDE, AMARILLO
        cx = ANCHO // 2
        ancho_b = s(150); alto_b = s(80); gap = s(16)
        total_ancho = len(STROOP_NOMBRES) * ancho_b + (len(STROOP_NOMBRES) - 1) * gap
        x_inicio = cx - total_ancho // 2
        cy = s(430)
        for i, nombre in enumerate(STROOP_NOMBRES):
            xb = x_inicio + i * (ancho_b + gap)
            rect_b = pygame.Rect(xb, cy - alto_b // 2, ancho_b, alto_b)
            pygame.draw.rect(self.screen, COLOR_BOTON_ACTIVO, rect_b, border_radius=s(12))
            # Nombre del color en la parte superior del botón
            sf = self.fuentes["instruccion"].render(nombre, True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=(rect_b.centerx, rect_b.centery - s(12))))
            # Tecla correspondiente en la parte inferior, en verde claro
            sf = self.fuentes["instruccion"].render(teclas[i], True, COLOR_SUBTITULO)
            self.screen.blit(sf, sf.get_rect(center=(rect_b.centerx, rect_b.centery + s(16))))

    def _visual_slide_4(self):
        # Igual que slide 5 del N-Back: boton pausa y 3 opciones
        cx  = ANCHO // 2
        cy0 = s(300)
        btn_p = pygame.Rect(cx - s(45), cy0 - s(35), s(90), s(70))
        pygame.draw.rect(self.screen, COLOR_AMARILLO, btn_p, border_radius=s(14))
        sf = self.fuentes["grande"].render("II", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=btn_p.center))

        opciones = [
            ("Reanudar",       COLOR_VERDE),
            ("Reiniciar",      COLOR_ROJO),
            ("Volver al menú", COLOR_AMARILLO),
        ]
        ancho_btn = s(210); alto_btn = s(48); sep_btn = s(58)
        cy_opciones = cy0 + s(85)
        for j, (texto, color) in enumerate(opciones):
            cy_b = cy_opciones + j * sep_btn
            rect = pygame.Rect(cx - ancho_btn // 2, cy_b - alto_btn // 2, ancho_btn, alto_btn)
            pygame.draw.rect(self.screen, color, rect, border_radius=s(10))
            sf = self.fuentes["instruccion"].render(texto, True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=rect.center))

    def _visual_slide_5(self):
        # Circulo verde con tilde (igual que slide 6 del N-Back)
        cx = ANCHO // 2; cy = s(440); radio = s(80)
        pygame.draw.circle(self.screen, COLOR_BOTON_ACTIVO, (cx, cy), radio)
        pygame.draw.circle(self.screen, COLOR_LINEA,        (cx, cy), radio, s(4))
        p1 = (cx - s(32), cy)
        p2 = (cx - s(10), cy + s(28))
        p3 = (cx + s(38), cy - s(28))
        pygame.draw.lines(self.screen, COLOR_TITULO, False, [p1, p2, p3], s(7))

    def _dibujar_progreso(self):
        total     = self.N_SLIDES
        sep       = s(28)
        cx_inicio = ANCHO // 2 - (total - 1) * sep // 2
        cy        = ALTO - s(143)
        for i in range(total):
            cx = cx_inicio + i * sep
            if i == self.slide_actual:
                pygame.draw.circle(self.screen, COLOR_TITULO,       (cx, cy), s(9))
            else:
                pygame.draw.circle(self.screen, COLOR_BOTON_ACTIVO, (cx, cy), s(6))

    def _dibujar_botones_nav(self):
        if self.slide_actual > 0:
            c = COLOR_BOTON_HOVER if self.hover_ant else COLOR_BOTON_ACTIVO
            pygame.draw.rect(self.screen, c, self.boton_anterior, border_radius=s(14))
            sf = self.fuentes["boton"].render("← Anterior", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.boton_anterior.center))
        if self.slide_actual < self.N_SLIDES - 1:
            c = COLOR_BOTON_GRIS if not self.hover_salt else (90, 100, 92)
            pygame.draw.rect(self.screen, c, self.boton_saltear, border_radius=s(14))
            sf = self.fuentes["boton"].render("Saltear", True, COLOR_PIE)
            self.screen.blit(sf, sf.get_rect(center=self.boton_saltear.center))
        if self.slide_actual < self.N_SLIDES - 1:
            texto = "Siguiente →"
            color = COLOR_BOTON_HOVER if self.hover_sig else COLOR_BOTON_ACTIVO
        else:
            texto = "Iniciar"
            color = COLOR_VERDE_HOVER if self.hover_sig else COLOR_VERDE
        pygame.draw.rect(self.screen, color, self.boton_siguiente, border_radius=s(14))
        sf = self.fuentes["boton"].render(texto, True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.boton_siguiente.center))


# ════════════════════════════════════════════════════════════
#  PANTALLA 8: SELECTOR DE NIVEL STROOP
# ════════════════════════════════════════════════════════════
class SelectorNivelStroop:
    def __init__(self, screen, fuentes):
        self.screen        = screen
        self.fuentes       = fuentes
        self.siguiente     = None
        self.boton_x       = pygame.Rect(s(20), s(20), s(52), s(52))
        self.hover_x       = False

        ab = s(480); alt = s(100); xc = (ANCHO - ab) // 2; yi = s(230)
        self.niveles = [
            {"clave": "facil",
             "texto": "Fácil",
             "desc":  "La palabra y el color de la tinta siempre coinciden",
             "rect":  pygame.Rect(xc, yi,          ab, alt), "hover": False},
            {"clave": "intermedio",
             "texto": "Intermedio",
             "desc":  "La mitad de las palabras NO coinciden con el color",
             "rect":  pygame.Rect(xc, yi + s(130), ab, alt), "hover": False},
            {"clave": "dificil",
             "texto": "Difícil",
             "desc":  "Ninguna palabra coincide con el color de la tinta",
             "rect":  pygame.Rect(xc, yi + s(260), ab, alt), "hover": False},
        ]

    def manejar_eventos(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            p = ev.pos
            self.hover_x = self.boton_x.collidepoint(p)
            for n in self.niveles: n["hover"] = n["rect"].collidepoint(p)
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            p = ev.pos
            if self.boton_x.collidepoint(p):
                # X vuelve a las instrucciones del Stroop, no al menú cognitivo
                self.siguiente = "instrucciones_stroop"; return
            for n in self.niveles:
                if n["rect"].collidepoint(p):
                    # Guardamos la clave del nivel ("facil", "intermedio", "dificil")
                    # y pasamos al selector de cantidad de estímulos
                    self.nivel_elegido = n["clave"]
                    self.siguiente     = ("estimulos_stroop", n["clave"]); return

    def dibujar(self):
        self.screen.fill(COLOR_FONDO)
        cx_color = COLOR_ROJO_HOVER if self.hover_x else COLOR_ROJO
        pygame.draw.rect(self.screen, cx_color, self.boton_x, border_radius=s(10))
        sf = self.fuentes["boton"].render("X", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.boton_x.center))
        pygame.draw.line(self.screen, COLOR_LINEA, (s(60), s(100)), (ANCHO - s(60), s(100)), 2)
        sf = self.fuentes["titulo"].render("Selecciona el nivel", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(60))))
        for n in self.niveles:
            c = COLOR_BOTON_HOVER if n["hover"] else COLOR_BOTON_ACTIVO
            pygame.draw.rect(self.screen, c, n["rect"], border_radius=s(14))
            # Nombre del nivel arriba, descripción corta abajo
            sf = self.fuentes["boton"].render(n["texto"], True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(midleft=(n["rect"].left + s(25), n["rect"].centery - s(16))))
            # max_ancho deja margen izquierdo (25) + margen derecho (20) para que no sobresalga
            max_ancho_desc = n["rect"].width - s(25) - s(20)
            render_en_lineas(self.screen, self.fuentes["descripcion"], n["desc"],
                             COLOR_DESCRIPCION, n["rect"].left + s(25),
                             n["rect"].centery + s(18), max_ancho_desc)


# ════════════════════════════════════════════════════════════
#  PANTALLA 9: SELECTOR DE CANTIDAD DE ESTIMULOS STROOP
#  Botones fijos: 20 / 40 / 60
#  Personalizado: +/- de a 10, rango 10-200
# ════════════════════════════════════════════════════════════
class SelectorEstimulosStroop:
    def __init__(self, screen, fuentes, nivel):
        self.screen    = screen
        self.fuentes   = fuentes
        self.nivel     = nivel
        self.siguiente = None

        # Cantidad actualmente seleccionada (None = ninguna todavia)
        self.cantidad         = None
        self.cantidad_custom  = 30      # valor del personalizador
        self.usando_custom    = False   # True cuando el usuario interactuo con +/-

        self.boton_x = pygame.Rect(s(20), s(20), s(52), s(52))
        self.hover_x = False

        # Botones fijos
        ab = s(140); alt = s(80)
        yi_fijos = s(240)
        xc = ANCHO // 2
        self.fijos = [
            {"valor": 20, "rect": pygame.Rect(xc - s(235), yi_fijos, ab, alt), "hover": False},
            {"valor": 40, "rect": pygame.Rect(xc - s(70),  yi_fijos, ab, alt), "hover": False},
            {"valor": 60, "rect": pygame.Rect(xc + s(95),  yi_fijos, ab, alt), "hover": False},
        ]

        # Controles del personalizador
        yi_custom = s(420)
        self.btn_menos    = pygame.Rect(xc - s(130), yi_custom - s(28), s(56), s(56))
        self.btn_mas      = pygame.Rect(xc + s(74),  yi_custom - s(28), s(56), s(56))
        self.hover_menos  = False
        self.hover_mas    = False

        # Boton confirmar
        self.btn_confirmar = pygame.Rect(xc - s(150), s(515), s(300), s(60))
        self.hover_conf    = False

    def manejar_eventos(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            p = ev.pos
            self.hover_x    = self.boton_x.collidepoint(p)
            self.hover_menos = self.btn_menos.collidepoint(p)
            self.hover_mas   = self.btn_mas.collidepoint(p)
            self.hover_conf  = self.btn_confirmar.collidepoint(p)
            for f in self.fijos: f["hover"] = f["rect"].collidepoint(p)

        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            p = ev.pos
            if self.boton_x.collidepoint(p):
                self.siguiente = "nivel_stroop"; return

            # Botones fijos: seleccionan la cantidad y desactivan el custom
            for f in self.fijos:
                if f["rect"].collidepoint(p):
                    self.cantidad      = f["valor"]
                    self.usando_custom = False; return

            # Boton menos
            if self.btn_menos.collidepoint(p) and self.cantidad_custom > 10:
                self.cantidad_custom -= 10
                self.cantidad      = self.cantidad_custom
                self.usando_custom = True; return

            # Boton mas
            if self.btn_mas.collidepoint(p) and self.cantidad_custom < 200:
                self.cantidad_custom += 10
                self.cantidad      = self.cantidad_custom
                self.usando_custom = True; return

            # Confirmar: solo si ya hay una cantidad elegida
            if self.btn_confirmar.collidepoint(p) and self.cantidad is not None:
                self.siguiente = ("form_paciente", "stroop", self.nivel, self.cantidad)

    def dibujar(self):
        self.screen.fill(COLOR_FONDO)

        # Boton X
        cx_col = COLOR_ROJO_HOVER if self.hover_x else COLOR_ROJO
        pygame.draw.rect(self.screen, cx_col, self.boton_x, border_radius=s(10))
        sf = self.fuentes["boton"].render("X", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.boton_x.center))

        pygame.draw.line(self.screen, COLOR_LINEA, (s(60), s(100)), (ANCHO - s(60), s(100)), 2)
        sf = self.fuentes["titulo"].render("¿Cuántos estímulos querés evaluar?", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(60))))

        # Botones fijos
        sf = self.fuentes["instruccion"].render("Opciones rápidas:", True, COLOR_SUBTITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(195))))
        for f in self.fijos:
            seleccionado = (not self.usando_custom) and (self.cantidad == f["valor"])
            if seleccionado:
                color = COLOR_BOTON_HOVER
            elif f["hover"]:
                color = COLOR_BOTON_HOVER
            else:
                color = COLOR_BOTON_ACTIVO
            pygame.draw.rect(self.screen, color, f["rect"], border_radius=s(14))
            if seleccionado:
                # Borde blanco para indicar seleccion
                pygame.draw.rect(self.screen, COLOR_TITULO, f["rect"], s(3), border_radius=s(14))
            sf = self.fuentes["grande"].render(str(f["valor"]), True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=f["rect"].center))

        # Separador
        pygame.draw.line(self.screen, COLOR_LINEA,
                         (ANCHO // 2 - s(220), s(345)), (ANCHO // 2 + s(220), s(345)), 1)
        sf = self.fuentes["instruccion"].render("Personalizar:", True, COLOR_SUBTITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(360))))

        # Boton menos
        c_menos = COLOR_BOTON_HOVER if self.hover_menos else COLOR_BOTON_ACTIVO
        pygame.draw.rect(self.screen, c_menos, self.btn_menos, border_radius=s(10))
        sf = self.fuentes["grande"].render("−", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.btn_menos.center))

        # Numero central del personalizador
        xc = ANCHO // 2
        yi_custom = s(420)
        color_num = COLOR_TITULO if self.usando_custom else COLOR_PIE
        sf = self.fuentes["grande"].render(str(self.cantidad_custom), True, color_num)
        self.screen.blit(sf, sf.get_rect(center=(xc, yi_custom)))
        if self.usando_custom:
            # Borde resaltado alrededor del numero para indicar que esta activo
            rect_num = pygame.Rect(xc - s(55), yi_custom - s(30), s(110), s(60))
            pygame.draw.rect(self.screen, COLOR_LINEA, rect_num, s(2), border_radius=s(8))

        # Boton mas
        c_mas = COLOR_BOTON_HOVER if self.hover_mas else COLOR_BOTON_ACTIVO
        pygame.draw.rect(self.screen, c_mas, self.btn_mas, border_radius=s(10))
        sf = self.fuentes["grande"].render("+", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.btn_mas.center))

        # Rango
        sf = self.fuentes["etiqueta"].render("(entre 10 y 200, de a 10)", True, COLOR_PIE)
        self.screen.blit(sf, sf.get_rect(center=(xc, yi_custom + s(40))))

        # Boton confirmar: verde si hay seleccion, gris si no
        if self.cantidad is not None:
            c_conf = COLOR_VERDE_HOVER if self.hover_conf else COLOR_VERDE
        else:
            c_conf = COLOR_BOTON_GRIS
        pygame.draw.rect(self.screen, c_conf, self.btn_confirmar, border_radius=s(14))
        sf = self.fuentes["boton"].render("Confirmar", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.btn_confirmar.center))


# ════════════════════════════════════════════════════════════
#  PANTALLA 10: TEST EFECTO STROOP
# ════════════════════════════════════════════════════════════
class TestStroop:
    # Bibliografía:
    # - Brysbaert & Stevens (2018): rangos de error por tipo de ensayo (congruente/incongruente).
    # - MacLeod (1991): revisión del efecto Stroop, interferencia normal 150-350 ms.
    # El tiempo de respuesta estándar es ~2000 ms. Se amplía a 5000 ms para post-ACV
    # para compensar los tiempos de reacción más lentos.
    TIEMPO_RESPUESTA_MS = 5000
    FLASH_MS            = 400   # ms de pantalla oscura entre estímulos

    def __init__(self, screen, fuentes, nivel, cantidad, nombre, id_pac):
        self.screen   = screen
        self.fuentes  = fuentes
        self.nivel    = nivel       # "facil" / "intermedio" / "dificil"
        self.cantidad = cantidad    # numero de estimulos elegido
        self.nombre   = nombre
        self.id_pac   = id_pac
        self.siguiente = None
        self._reiniciar()

    def _reiniciar(self):
        """Reinicia completamente el test (se llama al iniciar y al presionar Reiniciar)."""
        self.estimulos  = self._generar_estimulos()
        self.idx        = 0
        self.estado     = "flash"   # flash / activo / fin
        self.pausado    = False

        # Sistema de temporizado (igual que TestNBack)
        self.t_flash_ini  = pygame.time.get_ticks()
        self.t_inicio     = pygame.time.get_ticks()
        self.t_pausa_acum = 0
        self.t_pausa_ini  = 0
        self.t_respuesta  = None
        self.t_pausa_acum_respuesta = 0

        self.respuestas    = []
        self.guardado      = False
        self.ruta_guardado = ""

        # Botones: fila horizontal centrada en la parte inferior.
        # Se asigna una tecla del teclado a cada botón en orden: V · B · N · M
        teclas_str = [pygame.K_v, pygame.K_b, pygame.K_n, pygame.K_m]
        letras_str = ["V", "B", "N", "M"]
        ancho_b = s(200); alto_b = s(85); gap = s(18)
        total_ancho = len(STROOP_NOMBRES) * ancho_b + (len(STROOP_NOMBRES) - 1) * gap
        x_inicio = (ANCHO - total_ancho) // 2
        y_b = ALTO - s(155)
        self.btns_color = []
        for i, nombre_color in enumerate(STROOP_NOMBRES):
            xb = x_inicio + i * (ancho_b + gap)
            self.btns_color.append({
                "nombre": nombre_color,
                "rect":   pygame.Rect(xb, y_b, ancho_b, alto_b),
                "hover":  False,
                "tecla":  teclas_str[i],   # tecla de teclado asignada (pygame.K_v, etc.)
                "letra":  letras_str[i],   # letra visible en el botón
            })

        self.btn_pausa    = pygame.Rect(ANCHO - s(90), s(20),     s(65), s(55))
        bw = s(300)
        self.btn_reanudar  = pygame.Rect(ANCHO//2 - bw//2, s(290), bw, s(65))
        self.btn_reiniciar = pygame.Rect(ANCHO//2 - bw//2, s(375), bw, s(65))
        self.btn_menu      = pygame.Rect(ANCHO//2 - bw//2, s(460), bw, s(65))
        self.btn_guardar   = pygame.Rect(ANCHO//2 - s(320), s(440), s(280), s(65))
        self.btn_eliminar  = pygame.Rect(ANCHO//2 + s(40),  s(440), s(280), s(65))
        # Botón de observaciones: centrado debajo de guardar/eliminar
        self.btn_observaciones = pygame.Rect(ANCHO//2-s(255), s(530), s(510), s(62))

        # Estado del panel de observaciones
        self.modo_observaciones  = False   # True cuando el overlay de obs está abierto
        self.texto_observaciones = ""      # texto que escribe el terapeuta
        # Botones dentro del overlay de observaciones
        panel_y = ALTO // 2 - s(245)
        self.btn_guardar_obs   = pygame.Rect(ANCHO//2-s(280), panel_y+s(335), s(560), s(60))
        self.btn_descartar_obs = pygame.Rect(ANCHO//2-s(190), panel_y+s(415), s(380), s(55))

        self.hov = {k: False for k in
                    ["pausa", "reanudar", "reiniciar", "menú", "guardar", "eliminar",
                     "observaciones", "guardar_obs", "descartar_obs"]}

    def _generar_estimulos(self):
        """
        Genera la secuencia de estimulos segun el nivel elegido.
        Cada estimulo es un dict: {"palabra": str, "tinta": str, "congruente": bool}
        - facil:      tinta == palabra (todos congruentes)
        - intermedio: mitad congruentes, mitad incongruentes (mezclados aleatoriamente)
        - dificil:    tinta != palabra (todos incongruentes)
        """
        estimulos = []
        for _ in range(self.cantidad):
            palabra = random.choice(STROOP_NOMBRES)
            if self.nivel == "facil":
                tinta      = palabra
                congruente = True
            elif self.nivel == "dificil":
                # Elige una tinta distinta a la palabra
                opciones = [c for c in STROOP_NOMBRES if c != palabra]
                tinta      = random.choice(opciones)
                congruente = False
            else:   # intermedio: se decide despues de generar todos
                tinta      = palabra   # placeholder
                congruente = True      # placeholder
            estimulos.append({"palabra": palabra, "tinta": tinta, "congruente": congruente})

        if self.nivel == "intermedio":
            # La mitad de los indices seran incongruentes
            indices = list(range(self.cantidad))
            random.shuffle(indices)
            n_incong = self.cantidad // 2
            incongruentes = set(indices[:n_incong])
            for i in incongruentes:
                palabra = estimulos[i]["palabra"]
                opciones = [c for c in STROOP_NOMBRES if c != palabra]
                estimulos[i]["tinta"]      = random.choice(opciones)
                estimulos[i]["congruente"] = False

        return estimulos

    def _elapsed(self):
        """Tiempo transcurrido desde el inicio del estado actual, excluyendo pausas."""
        if self.pausado:
            return self.t_pausa_ini - self.t_inicio - self.t_pausa_acum
        return pygame.time.get_ticks() - self.t_inicio - self.t_pausa_acum

    def _registrar(self, color_elegido):
        """
        Registra la respuesta del paciente para el estimulo actual.
        color_elegido: string como "ROJO" si hubo clic, None si fue omision (timeout).
        """
        estim    = self.estimulos[self.idx]
        correcto = (color_elegido == estim["tinta"]) if color_elegido is not None else False

        # Calcula el tiempo de reaccion solo si hubo respuesta
        if self.t_respuesta is not None and color_elegido is not None:
            rt = (pygame.time.get_ticks() - self.t_respuesta
                  - (self.t_pausa_acum - self.t_pausa_acum_respuesta))
        else:
            rt = None

        self.respuestas.append({
            "estimulo":    self.idx + 1,
            "palabra":     estim["palabra"],
            "tinta":       estim["tinta"],
            "congruente":  estim["congruente"],
            "elegido":     color_elegido,   # None si omision
            "correcto":    correcto,
            "rt_ms":       rt,
        })

    def _siguiente_estimulo(self):
        """Avanza al proximo estimulo o termina el test."""
        self.idx += 1
        if self.idx >= self.cantidad:
            self.estado = "fin"
        else:
            # Flash corto antes de mostrar el siguiente estimulo
            self.estado       = "flash"
            self.t_flash_ini  = pygame.time.get_ticks()
            self.t_inicio     = pygame.time.get_ticks()
            self.t_pausa_acum = 0
            self.t_respuesta  = None

    def _metricas(self):
        """
        Calcula los resultados finales del test.
        Clasificacion basada en porcentaje de error segun nivel:
          Fácil (solo congruentes):
            error < 2%  (precision >= 98%) → Normal      (Brysbaert & Stevens, 2018)
            error 2-4%  (precision 96-97%) → Limítrofe
            error >= 4% (precision < 96%)  → Patológico
          Intermedio / Difícil (incluyen incongruentes):
            error < 10% (precision >= 90%) → Normal      (Brysbaert & Stevens, 2018)
            error 10-20% (precision 80-89%) → Limítrofe
            error >= 20% (precision < 80%) → Patológico
        """
        total      = len(self.respuestas)
        if total == 0: return {}
        correctas  = sum(1 for r in self.respuestas if r["correcto"])
        omisiones  = sum(1 for r in self.respuestas if r["elegido"] is None)
        comisiones = sum(1 for r in self.respuestas if not r["correcto"] and r["elegido"] is not None)
        precision  = round(correctas / total * 100, 1)

        # Tiempo de reaccion promedio (solo respuestas correctas con RT medido)
        rts = [r["rt_ms"] for r in self.respuestas if r["correcto"] and r["rt_ms"] is not None]
        rt_prom = round(sum(rts) / len(rts)) if rts else None

        # RT promedio separado por tipo de congruencia (todos los niveles)
        rts_cong   = [r["rt_ms"] for r in self.respuestas
                      if r["congruente"] and r["correcto"] and r["rt_ms"] is not None]
        rts_incong = [r["rt_ms"] for r in self.respuestas
                      if not r["congruente"] and r["correcto"] and r["rt_ms"] is not None]
        rt_cong_prom   = round(sum(rts_cong)   / len(rts_cong))   if rts_cong   else None
        rt_incong_prom = round(sum(rts_incong) / len(rts_incong)) if rts_incong else None

        # Efecto de interferencia: solo tiene sentido en nivel intermedio (hay ambos tipos)
        efecto = None
        if self.nivel == "intermedio" and rts_cong and rts_incong:
            efecto = round(sum(rts_incong) / len(rts_incong)
                           - sum(rts_cong)  / len(rts_cong))

        # Clasificacion y rango según nivel (Brysbaert & Stevens, 2018)
        if self.nivel == "facil":
            if precision >= 98:
                clasif = "Normal"
            elif precision >= 96:
                clasif = "Limítrofe"
            else:
                clasif = "Patológico"
            rango   = "error < 2%  (precisión ≥ 98%)"
            fuente  = "Brysbaert & Stevens (2018)"
        else:   # intermedio o dificil
            if precision >= 90:
                clasif = "Normal"
            elif precision >= 80:
                clasif = "Limítrofe"
            else:
                clasif = "Patológico"
            rango   = "error < 10%  (precisión ≥ 90%)"
            fuente  = "Brysbaert & Stevens (2018)"

        return {
            "nivel_stroop":                self.nivel,
            "estimulos_evaluados":         total,
            "respuestas_correctas":        correctas,
            "errores_omision":             omisiones,
            "errores_comision":            comisiones,
            "precision_porcentaje":        precision,
            "tiempo_reaccion_promedio_ms": rt_prom,
            "rango_esperado_precision":    rango,
            "fuente_rango":                fuente,
            "clasificacion":               clasif,
            "efecto_interferencia":        efecto,
            "rt_congruente_prom_ms":       rt_cong_prom,
            "rt_incongruente_prom_ms":     rt_incong_prom,
        }

    def manejar_eventos(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            p = ev.pos
            self.hov["pausa"] = self.btn_pausa.collidepoint(p)
            if self.pausado:
                self.hov["reanudar"]  = self.btn_reanudar.collidepoint(p)
                self.hov["reiniciar"] = self.btn_reiniciar.collidepoint(p)
                self.hov["menú"]      = self.btn_menu.collidepoint(p)
            if self.estado == "fin":
                self.hov["guardar"]       = self.btn_guardar.collidepoint(p)
                self.hov["eliminar"]      = self.btn_eliminar.collidepoint(p)
                self.hov["observaciones"] = self.btn_observaciones.collidepoint(p)
            if self.modo_observaciones:
                self.hov["guardar_obs"]   = self.btn_guardar_obs.collidepoint(p)
                self.hov["descartar_obs"] = self.btn_descartar_obs.collidepoint(p)
            for b in self.btns_color:
                b["hover"] = b["rect"].collidepoint(p)

        # Captura de texto del teclado cuando el overlay de observaciones está abierto
        if ev.type == pygame.KEYDOWN and self.modo_observaciones:
            if ev.key == pygame.K_BACKSPACE:
                self.texto_observaciones = self.texto_observaciones[:-1]
            elif ev.key == pygame.K_RETURN:
                self.texto_observaciones += "\n"
            elif ev.unicode and ev.unicode.isprintable():
                self.texto_observaciones += ev.unicode
            return   # ninguna otra acción mientras se escribe

        # ── Atajos de teclado para el test Stroop ─────────────────────────
        if ev.type == pygame.KEYDOWN and not self.modo_observaciones:
            if self.pausado:
                # Espacio reanuda la pausa
                if ev.key == pygame.K_SPACE:
                    self.t_pausa_acum += pygame.time.get_ticks() - self.t_pausa_ini
                    self.pausado = False
            elif self.estado == "activo":
                # Teclas V/B/N/M seleccionan el color correspondiente
                for b in self.btns_color:
                    if ev.key == b["tecla"]:
                        self._registrar(b["nombre"])
                        self._siguiente_estimulo()
                        return
                # Espacio pausa el test
                if ev.key == pygame.K_SPACE:
                    self.pausado = True; self.t_pausa_ini = pygame.time.get_ticks()
            elif self.estado not in ("fin",):
                # Espacio pausa en cualquier momento (no en pantalla de fin)
                if ev.key == pygame.K_SPACE:
                    self.pausado = True; self.t_pausa_ini = pygame.time.get_ticks()

        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            p = ev.pos

            # Si el overlay de observaciones está abierto, solo sus botones responden
            if self.modo_observaciones:
                if self.btn_guardar_obs.collidepoint(p):
                    m = self._metricas()
                    self.ruta_guardado = guardar_json_stroop(
                        self.id_pac, self.nombre, m,
                        observaciones=self.texto_observaciones)
                    self.guardado = True
                    self.modo_observaciones = False
                    self.btn_eliminar = pygame.Rect(ANCHO // 2 - s(140), s(440), s(280), s(65))
                elif self.btn_descartar_obs.collidepoint(p):
                    self.texto_observaciones = ""
                    self.modo_observaciones  = False
                return

            # Menú de pausa (prioridad maxima)
            if self.pausado:
                if self.btn_reanudar.collidepoint(p):
                    self.t_pausa_acum += pygame.time.get_ticks() - self.t_pausa_ini
                    self.pausado = False
                elif self.btn_reiniciar.collidepoint(p):
                    self._reiniciar()
                elif self.btn_menu.collidepoint(p):
                    self.siguiente = "cognitivo"
                return

            # Pantalla de fin
            if self.estado == "fin":
                if self.btn_guardar.collidepoint(p) and not self.guardado:
                    m = self._metricas()
                    self.ruta_guardado = guardar_json_stroop(self.id_pac, self.nombre, m)
                    self.guardado = True
                    # Despues de guardar, reposicionar btn_eliminar al centro como "Volver al menu"
                    self.btn_eliminar = pygame.Rect(ANCHO // 2 - s(140), s(440), s(280), s(65))
                elif self.btn_eliminar.collidepoint(p):
                    self.siguiente = "cognitivo"
                elif self.btn_observaciones.collidepoint(p) and not self.guardado:
                    self.modo_observaciones = True
                return

            # Boton pausa (solo durante el test)
            if self.btn_pausa.collidepoint(p):
                self.pausado     = True
                self.t_pausa_ini = pygame.time.get_ticks()
                return

            # Botones de respuesta (solo cuando el estimulo esta visible)
            if self.estado == "activo":
                for b in self.btns_color:
                    if b["rect"].collidepoint(p):
                        self._registrar(b["nombre"])
                        self._siguiente_estimulo()
                        return

    def actualizar(self):
        """Avanza la maquina de estados. Se llama en cada frame desde main()."""
        if self.pausado or self.estado == "fin": return

        if self.estado == "flash":
            # Esperamos FLASH_MS ms (pantalla oscura) antes de mostrar la siguiente palabra
            if pygame.time.get_ticks() - self.t_flash_ini >= self.FLASH_MS:
                self.estado               = "activo"
                self.t_inicio             = pygame.time.get_ticks()
                self.t_pausa_acum         = 0
                # Arrancamos el cronómetro de tiempo de reacción desde que aparece el estímulo
                self.t_respuesta          = pygame.time.get_ticks()
                self.t_pausa_acum_respuesta = 0

        # A diferencia del N-Back, en el Stroop no hay tiempo límite de respuesta:
        # el paciente puede tomarse todo el tiempo que necesite.

    def dibujar(self):
        self.screen.fill(COLOR_FONDO)

        # Barra de progreso superior: estimulos completados / total
        pygame.draw.line(self.screen, COLOR_LINEA, (s(60), s(75)), (ANCHO - s(60), s(75)), 2)
        nivel_txt = {"facil": "Fácil", "intermedio": "Intermedio", "dificil": "Difícil"}.get(
            self.nivel, self.nivel)
        sf = self.fuentes["casa"].render(
            f"Efecto Stroop  |  Nivel: {nivel_txt}  |  "
            f"Estimulo: {min(self.idx + 1, self.cantidad)}/{self.cantidad}",
            True, COLOR_SUBTITULO)
        self.screen.blit(sf, sf.get_rect(midleft=(s(60), s(45))))

        # Boton pausa (solo si el test no termino)
        if self.estado != "fin":
            cp = COLOR_AMARILLO_HOVER if self.hov["pausa"] else COLOR_AMARILLO
            pygame.draw.rect(self.screen, cp, self.btn_pausa, border_radius=s(10))
            sf = self.fuentes["boton"].render("II", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.btn_pausa.center))

        if self.estado == "fin":
            self._dibujar_fin()
            if self.modo_observaciones:
                dibujar_overlay_observaciones(
                    self.screen, self.fuentes, self.texto_observaciones,
                    self.hov, self.btn_guardar_obs, self.btn_descartar_obs)
            return

        # Flash: pantalla de fondo oscuro, sin estimulo
        if self.estado == "flash":
            if self.pausado:
                self._dibujar_pausa()
            return

        # Estado "activo": mostramos la palabra del estímulo actual y los botones de respuesta
        if self.idx < self.cantidad:
            estim = self.estimulos[self.idx]
            # La palabra aparece en el color de la TINTA (no del nombre), eso es el desafío Stroop
            fuente_palabra = pygame.font.SysFont("Arial", s(80), bold=True)
            sf = fuente_palabra.render(estim["palabra"], True, STROOP_TINTA_RGB[estim["tinta"]])
            rect_palabra = sf.get_rect(center=(ANCHO // 2, s(300)))
            # Fondo blanco detrás de la palabra para que el color de la tinta se vea con contraste
            rect_fondo = rect_palabra.inflate(s(50), s(30))
            pygame.draw.rect(self.screen, (255, 255, 255), rect_fondo, border_radius=s(14))
            self.screen.blit(sf, rect_palabra)

        # Los 4 botones de respuesta solo se muestran cuando hay un estímulo activo
        if self.estado == "activo" and not self.pausado:
            for b in self.btns_color:
                color = COLOR_BOTON_HOVER if b["hover"] else COLOR_BOTON_ACTIVO
                pygame.draw.rect(self.screen, color, b["rect"], border_radius=s(12))
                # Los botones muestran el nombre del color en texto blanco neutro,
                # no en el color correspondiente, para no dar pistas visuales
                sf = self.fuentes["boton"].render(b["nombre"], True, COLOR_TITULO)
                # El nombre va un poco arriba para dejar espacio a la tecla de atajo abajo
                nombre_rect = sf.get_rect(center=(b["rect"].centerx, b["rect"].centery - s(10)))
                self.screen.blit(sf, nombre_rect)
                # Tecla de atajo del teclado entre corchetes (V, B, N o M)
                sf_tecla = self.fuentes["subtitulo"].render(f"[{b['letra']}]", True, COLOR_SUBTITULO)
                tecla_rect = sf_tecla.get_rect(center=(b["rect"].centerx, b["rect"].centery + s(18)))
                self.screen.blit(sf_tecla, tecla_rect)

        if self.pausado:
            self._dibujar_pausa()

    def _dibujar_pausa(self):
        """Overlay semi-transparente con el menu de pausa."""
        ov = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        self.screen.blit(ov, (0, 0))
        caja = pygame.Rect(ANCHO // 2 - s(210), s(195), s(420), s(370))
        pygame.draw.rect(self.screen, (20, 55, 35), caja, border_radius=s(18))
        pygame.draw.rect(self.screen, COLOR_LINEA, caja, 2, border_radius=s(18))
        sf = self.fuentes["titulo"].render("Test pausado", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(245))))
        for btn, color, hover_color, etiq, key in [
            (self.btn_reanudar,  COLOR_VERDE,    COLOR_VERDE_HOVER,    "Reanudar",      "reanudar"),
            (self.btn_reiniciar, COLOR_ROJO,     COLOR_ROJO_HOVER,     "Reiniciar",     "reiniciar"),
            (self.btn_menu,      COLOR_AMARILLO, COLOR_AMARILLO_HOVER, "Volver al menú","menú"),
        ]:
            c = hover_color if self.hov.get(key, False) else color
            pygame.draw.rect(self.screen, c, btn, border_radius=s(12))
            sf = self.fuentes["boton"].render(etiq, True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=btn.center))

    def _dibujar_fin(self):
        """Pantalla de resultados al terminar el test."""
        sf = self.fuentes["grande"].render("Test finalizado", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(155))))

        m = self._metricas()
        if m:
            prec  = m.get("precision_porcentaje", 0)
            clas  = m.get("clasificacion", "")
            cc    = {"Normal": COLOR_VERDE, "Limítrofe": COLOR_AMARILLO,
                     "Patológico": COLOR_ROJO}.get(clas, COLOR_TITULO)
            # Línea 1: porcentaje de errores y diagnóstico
            errores_porc = round(100 - prec, 1)
            sf = self.fuentes["subtitulo"].render(
                f"Errores: {errores_porc}%     Diagnóstico: {clas}", True, cc)
            self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(220))))

            # Línea 2: rango normal esperado con fuente
            sf = self.fuentes["descripcion"].render(
                f"Rango normal (precisión): {m.get('rango_esperado_precision', '')}  "
                f"— {m.get('fuente_rango', '')}",
                True, COLOR_SUBTITULO)
            self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(258))))

            # Líneas 3-4: tiempos de reacción por tipo
            y = s(298)
            rt_cong   = m.get("rt_congruente_prom_ms")
            rt_incong = m.get("rt_incongruente_prom_ms")
            if rt_cong is not None:
                sf = self.fuentes["descripcion"].render(
                    f"Tiempo de reacción (congruentes): {rt_cong} ms", True, COLOR_SUBTITULO)
                self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, y)))
                y += s(33)
            if rt_incong is not None:
                sf = self.fuentes["descripcion"].render(
                    f"Tiempo de reacción (incongruentes): {rt_incong} ms", True, COLOR_SUBTITULO)
                self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, y)))
                y += s(33)

            # Efecto de interferencia + referencia bibliográfica (solo nivel intermedio)
            ef = m.get("efecto_interferencia")
            if ef is not None:
                sf = self.fuentes["descripcion"].render(
                    f"Diferencia de interferencia: {ef} ms  (normal: 150–350 ms, MacLeod 1991)",
                    True, COLOR_SUBTITULO)
                self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, y)))

        pygame.draw.line(self.screen, COLOR_LINEA, (s(60), s(400)), (ANCHO - s(60), s(400)), 1)

        if self.guardado:
            sf = self.fuentes["instruccion"].render(
                f"Guardado en: {self.ruta_guardado}", True, COLOR_VERDE)
            self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(420))))
            cv = COLOR_VERDE_HOVER if self.hov["eliminar"] else COLOR_VERDE
            pygame.draw.rect(self.screen, cv, self.btn_eliminar, border_radius=s(14))
            sf = self.fuentes["boton"].render("Volver al menú", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.btn_eliminar.center))
        else:
            cg = COLOR_VERDE_HOVER if self.hov["guardar"] else COLOR_VERDE
            pygame.draw.rect(self.screen, cg, self.btn_guardar, border_radius=s(14))
            sf = self.fuentes["boton"].render("Guardar resultados", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.btn_guardar.center))

            ce = COLOR_ROJO_HOVER if self.hov["eliminar"] else COLOR_ROJO
            pygame.draw.rect(self.screen, ce, self.btn_eliminar, border_radius=s(14))
            sf = self.fuentes["boton"].render("Eliminar intento", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.btn_eliminar.center))

            # Botón de observaciones: centrado debajo de los dos botones principales
            co = COLOR_AZUL_HOVER if self.hov["observaciones"] else COLOR_AZUL
            pygame.draw.rect(self.screen, co, self.btn_observaciones, border_radius=s(14))
            sf = self.fuentes["instruccion"].render("Agregar observaciones del terapeuta", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.btn_observaciones.center))


# ════════════════════════════════════════════════════════════
#  ACTIVIDADES DE LA VIDA DIARIA (AVD)
#  Cada actividad tiene sus pasos para 3 niveles de dificultad.
#  Los pasos de niveles 4 y 5 son un subconjunto del nivel 7.
# ════════════════════════════════════════════════════════════
ACTIVIDADES_AVD = {
    "Cepillarse los dientes": {
        4: ["Agarrar el cepillo de dientes y la pasta", "Ponerle pasta al cepillo",
            "Cepillarse los dientes", "Escupir la pasta"],
        5: ["Agarrar el cepillo de dientes y la pasta", "Abrir la pasta de dientes",
            "Ponerle pasta al cepillo", "Cepillarse los dientes", "Escupir la pasta"],
        7: ["Abrir la pasta de dientes", "Ponerle pasta al cepillo", 
            "Llevar el cepillo a la boca", "Cepillarse los dientes",
            "Escupir la pasta", "Cerrar la canilla", "Secarse las manos y la cara"],
    },
    "Bañarse": {
        4: ["Desvestirse", "Abrir el agua", "Bañarse con jabón", "Secarse"],
        5: ["Desvestirse", "Abrir el agua", "Regular la temperatura",
            "Bañarse con jabón", "Secarse"],
        7: ["Desvestirse", "Abrir el agua", "Regular la temperatura",
            "Bañarse con jabón", "Cerrar el agua", "Agarrar la toalla", "Secarse"],
    },
    "Ponerse la remera": {
        4: ["Elegir la remera", "Agarrar la remera",
            "Meter los brazos y la cabeza por los agujeros",
            "Bajar la remera hacia la cintura"],
        5: ["Elegir la remera", "Agarrar la remera",
            "Fijarse el lado correcto de la remera",
            "Meter los brazos y la cabeza por los agujeros",
            "Bajar la remera hacia la cintura"],
        7: ["Abrir el placard", "Elegir la remera", "Agarrar la remera",
            "Fijarse el lado correcto de la remera",
            "Meter los brazos y la cabeza por los agujeros",
            "Bajar la remera hacia la cintura", "Ver si queda bien puesta"],
    },
    "Preparar un té": {
        4: ["Poner agua en la pava", "Encender la pava",
            "Volcar el agua sobre la taza con el saquito",
            "Esperar a que infusione"],
        5: ["Poner agua en la pava", "Encender la pava",
            "Esperar a que hierva el agua",
            "Volcar el agua sobre la taza con el saquito",
            "Esperar a que infusione"],
        7: ["Poner agua en la pava", "Encender la pava",
            "Esperar a que hierva el agua", "Agarrar la pava con agua hirviendo",
            "Volcar el agua sobre la taza con el saquito",
            "Esperar a que infusione", "Sacar el saquito"],
    },
    "Comer": {
        4: ["Agarrar el tenedor y el cuchillo", "Pinchar el bocado",
            "Llevar el tenedor a la boca", "Masticar la comida"],
        5: ["Sentarse en la mesa", "Agarrar el tenedor y el cuchillo",
            "Pinchar el bocado", "Llevar el tenedor a la boca", "Masticar la comida"],
        7: ["Sentarse en la mesa", "Agarrar el tenedor y el cuchillo",
            "Cortar la comida", "Pinchar el bocado",
            "Llevar el tenedor a la boca", "Masticar la comida", "Tragar la comida"],
    },
    "Tender la cama": {
        4: ["Acercarse a la cama", "Quitar las almohadas y el acolchado",
            "Estirar el cubrecama y acolchado", "Acomodar los almohadones"],
        5: ["Acercarse a la cama", "Quitar las almohadas y el acolchado",
            "Estirar el cubrecama", "Poner el acolchado", "Acomodar los almohadones"],
        7: ["Acercarse a la cama", "Quitar las almohadas y el acolchado",
            "Alinear el colchón vacío", "Estirar el cubrecama",
            "Colocar las sábanas", "Poner el acolchado", "Acomodar los almohadones"],
    },
    "Mirar una película": {
        4: ["Encender la tele", "Buscar la película deseada",
            "Mirar la película", "Apagar la tele"],
        5: ["Encender la tele", "Buscar la película deseada",
            "Ponerle play a la película deseada", "Mirar la película", "Apagar la tele"],
        7: ["Agarrar el control remoto", "Encender la tele", 
            "Abrir la plataforma de la película", "Buscar la película deseada",
            "Ponerle play a la película deseada", "Mirar la película", "Apagar la tele"],
    },
    "Ir al baño": {
        4: ["Levantar la tapa del inodoro", "Sentarse sobre el inodoro",
            "Limpiarse", "Tirar la cadena"],
        5: ["Levantar la tapa del inodoro", "Sentarse sobre el inodoro", 
            "Hacer caca", "Limpiarse", "Tirar la cadena"],
        7: ["Abrir la puerta del baño", "Acercarse al inodoro",
            "Levantar la tapa del inodoro", "Sentarse sobre el inodoro",
            "Hacer caca", "Limpiarse", "Tirar la cadena"],
    },
}


# ════════════════════════════════════════════════════════════
#  GUARDAR JSON - SECUENCIACIÓN AVD
#  Mismo mecanismo que N-Back y Stroop. Si el paciente ya tiene
#  un archivo con otros tests, el nuevo intento se agrega al final.
# ════════════════════════════════════════════════════════════
def guardar_json_avd(id_paciente, nombre_paciente, metricas, observaciones=""):
    """
    Guarda el resultado del test AVD en CARPETA_RESULTADOS/ID_Nombre.json
    Si el paciente ya tiene intentos (N-Back, Stroop), los conserva y agrega éste.
    Si se pasan observaciones del terapeuta, se incluyen al final del intento.
    """
    if not os.path.exists(CARPETA_RESULTADOS):
        os.makedirs(CARPETA_RESULTADOS)

    nombre_limpio  = re.sub(r"\s+", "_", nombre_paciente.strip().lower())
    nombre_limpio  = re.sub(r"[^a-zA-Z0-9_\-]", "", nombre_limpio)
    nombre_archivo = f"{id_paciente}_{nombre_limpio}.json"
    ruta           = os.path.join(CARPETA_RESULTADOS, nombre_archivo)

    nivel_nombres = {1: "Básico (4 pasos)", 2: "Intermedio (5 pasos)", 3: "Avanzado (7 pasos)"}
    nivel_txt = nivel_nombres.get(metricas.get("nivel", 1), "?")

    nuevo_intento = {
        "━━━ NUEVO INTENTO ━━━"       : "",
        "Paciente"                     : nombre_paciente,
        "ID"                           : id_paciente,
        "Fecha"                        : datetime.now().strftime("%d/%m/%Y"),
        "Hora"                         : datetime.now().strftime("%H:%M"),
        "Test"                         : "Secuenciación AVD",
        "─── Resultados ───"           : "",
        "Nivel"                        : nivel_txt,
        "Actividades evaluadas"        : metricas.get("actividades_evaluadas", "?"),
        "Precisión obtenida"           : f"{metricas.get('precision_porcentaje', '?')}%",
        "Rango normal esperado"        : metricas.get("rango_esperado", "?"),
        "Clasificación"                : metricas.get("clasificacion", "?"),
        "Fuente bibliográfica"         : metricas.get("fuente_rango", "?"),
        "Tiempo total"                 : f"{metricas.get('tiempo_total_s', '?')} segundos",
        "─── Detalle por actividad ───": "",
        "Detalle por actividad"        : [
            {
                "Actividad"        : r["nombre"],
                "Pasos correctos"  : f"{r['correctos']} de {r['total_pasos']}",
                "Tiempo (s)"       : r["tiempo_s"],
                "Orden ingresado"  : r["orden_ingresado"],
                "Orden correcto"   : r["orden_correcto"],
            }
            for r in metricas.get("detalle", [])
        ],
    }

    # Cargar historial existente (si hay datos de otros tests del mismo paciente)
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f_:
                historial = json.load(f_)
            if not isinstance(historial, list):
                historial = []
        except:
            historial = []
    else:
        historial = []

    # Si el terapeuta escribió observaciones, se agregan al final del intento
    if observaciones and observaciones.strip():
        nuevo_intento["─── Observaciones del terapeuta ───"] = ""
        nuevo_intento["Observaciones"] = observaciones.strip()

    historial.append(nuevo_intento)

    with open(ruta, "w", encoding="utf-8") as f_:
        json.dump(historial, f_, ensure_ascii=False, indent=2)

    return ruta


# ════════════════════════════════════════════════════════════
#  INSTRUCCIONES SECUENCIACIÓN AVD  (carrusel 5 slides)
#  Misma estructura que InstruccionesNBack y InstruccionesStroop.
# ════════════════════════════════════════════════════════════
class InstruccionesAVD:

    SLIDES = [
        {
            "titulo": "Secuenciación de Actividades",
            "lineas": [
                "En este test vas a ordenar los pasos",
                "de actividades cotidianas.",
                "Por ejemplo: preparar un té o bañarse.",
            ]
        },
        {
            "titulo": "¿Qué vas a ver?",
            "lineas": [
                "Aparecen los pasos de una actividad",
                "mezclados y desordenados.",
                "Tu tarea: ordenarlos del primero al último.",
            ]
        },
        {
            "titulo": "¿Cómo se usa?",
            "lineas": [
                "Hacé clic en un paso (o presioná su letra) →",
                "   se coloca en el primer lugar vacío.",
                "Para quitarlo: clic sobre él en la lista de la derecha,",
                "   o volvé a presionar su letra.",
                "Cuando llenaste todos los lugares, confirmás el orden",
                "   haciendo clic en el botón o presionando Enter.",
            ]
        },
        {
            "titulo": "Niveles de dificultad",
            "lineas": [
                "Básico: 4 pasos por actividad.",
                "Intermedio: 5 pasos por actividad.",
                "Avanzado: 7 pasos por actividad.",
            ]
        },
        {
            "titulo": "¡Todo listo!",
            "lineas": [
                "Vas a ordenar 4 actividades en total.",
                "No hay límite de tiempo. Tomá tu tiempo.",
                "Cuando estés listo, presioná Iniciar.",
            ]
        },
    ]

    def __init__(self, screen, fuentes):
        self.screen    = screen
        self.fuentes   = fuentes
        self.siguiente = None

        self.slide_actual = 0
        self.N_SLIDES     = 5

        # Boton X para volver al menu cognitivo
        self.boton_x = pygame.Rect(s(20), s(20), s(52), s(52))

        # Botones de navegacion (misma posicion que N-Back y Stroop)
        self.boton_anterior  = pygame.Rect(s(60),            ALTO - s(120), s(200), s(60))
        self.boton_siguiente = pygame.Rect(ANCHO - s(260),   ALTO - s(120), s(200), s(60))
        self.boton_saltear   = pygame.Rect(ANCHO//2 - s(90), ALTO - s(120), s(180), s(60))

        self.hover_x    = False
        self.hover_ant  = False
        self.hover_sig  = False
        self.hover_salt = False

    def manejar_eventos(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            p = ev.pos
            self.hover_x    = self.boton_x.collidepoint(p)
            self.hover_ant  = (self.slide_actual > 0) and self.boton_anterior.collidepoint(p)
            self.hover_sig  = self.boton_siguiente.collidepoint(p)
            self.hover_salt = (self.slide_actual < self.N_SLIDES - 1) and self.boton_saltear.collidepoint(p)

        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            p = ev.pos
            if self.boton_x.collidepoint(p):
                self.siguiente = "cognitivo"; return
            if self.slide_actual < self.N_SLIDES - 1 and self.boton_saltear.collidepoint(p):
                self.slide_actual = self.N_SLIDES - 1; return
            if self.slide_actual > 0 and self.boton_anterior.collidepoint(p):
                self.slide_actual -= 1; return
            if self.boton_siguiente.collidepoint(p):
                if self.slide_actual < self.N_SLIDES - 1:
                    self.slide_actual += 1
                else:
                    self.siguiente = "nivel_avd"   # ultimo slide → elegir nivel

        # ── Atajos de teclado ──────────────────────────────────────
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RIGHT:               # → Siguiente / Iniciar
                if self.slide_actual < self.N_SLIDES - 1:
                    self.slide_actual += 1
                else:
                    self.siguiente = "nivel_avd"
            elif ev.key == pygame.K_LEFT:              # ← Anterior
                if self.slide_actual > 0:
                    self.slide_actual -= 1
            elif ev.key == pygame.K_SPACE:             # Espacio → Saltear al ultimo slide
                if self.slide_actual < self.N_SLIDES - 1:
                    self.slide_actual = self.N_SLIDES - 1

    def dibujar(self):
        self.screen.fill(COLOR_FONDO)
        slide = self.SLIDES[self.slide_actual]

        # ── Encabezado fijo ─────────────────────────────────────
        sf = self.fuentes["subtitulo"].render("Instrucciones - Secuenciación AVD", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(50))))
        pygame.draw.line(self.screen, COLOR_LINEA, (s(60), s(82)), (ANCHO - s(60), s(82)), 2)

        # Boton X
        cx_color = COLOR_ROJO_HOVER if self.hover_x else COLOR_ROJO
        pygame.draw.rect(self.screen, cx_color, self.boton_x, border_radius=s(10))
        sf = self.fuentes["boton"].render("X", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.boton_x.center))

        # ── Titulo y texto del slide ────────────────────────────
        y_texto = s(135)
        sf = self.fuentes["boton"].render(slide["titulo"], True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, y_texto)))
        y_texto += s(50)
        for linea in slide["lineas"]:
            sf = self.fuentes["subtitulo"].render(linea, True, COLOR_SUBTITULO)
            self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, y_texto)))
            y_texto += s(36)

        # ── Dibujo visual del slide ─────────────────────────────
        self._dibujar_visual(self.slide_actual)

        # ── Puntos de progreso y botones de navegacion ──────────
        self._dibujar_progreso()
        pygame.draw.line(self.screen, COLOR_LINEA,
                         (s(60), ALTO - s(130)), (ANCHO - s(60), ALTO - s(130)), 1)
        self._dibujar_botones_nav()

    def _dibujar_visual(self, idx):
        metodos = [
            self._visual_slide_0,
            self._visual_slide_1,
            self._visual_slide_2,
            self._visual_slide_3,
            self._visual_slide_4,
        ]
        metodos[idx]()

    def _tarjeta(self, texto, cx, cy, ancho, alto, fondo, borde):
        """Dibuja una tarjeta con texto centrado (helper reutilizable)."""
        r = pygame.Rect(cx - ancho // 2, cy - alto // 2, ancho, alto)
        pygame.draw.rect(self.screen, fondo, r, border_radius=s(10))
        pygame.draw.rect(self.screen, borde, r, s(2), border_radius=s(10))
        sf = self.fuentes["descripcion"].render(texto, True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(cx, cy)))

    # Slide 0: tres tarjetas mezcladas (pasos de una actividad desordenados)
    def _visual_slide_0(self):
        cy  = s(440)
        pasos = ["Abrir el agua", "Desvestirse", "Bañarse con jabón"]
        sep   = s(250)
        cx0   = ANCHO // 2 - sep
        for i, texto in enumerate(pasos):
            self._tarjeta(texto, cx0 + i * sep, cy, s(220), s(55), (25, 65, 42), COLOR_LINEA)
        sf = self.fuentes["instruccion"].render("(pasos mezclados)", True, COLOR_PIE)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, cy + s(46))))

    # Slide 1: tres tarjetas desordenadas apiladas verticalmente (pasos mezclados)
    def _visual_slide_1(self):
        # Mostramos 3 pasos de ejemplo apilados en el centro, con etiqueta "MEZCLADOS"
        pasos   = ["Bañarse con jabón", "Desvestirse", "Abrir el agua"]
        cw      = s(320); ch = s(48); gap = s(10)
        cx      = ANCHO // 2
        y_ini   = s(340)   # inicio de las tarjetas dentro de la zona visual

        sf = self.fuentes["instruccion"].render("Los pasos aparecen mezclados:", True, COLOR_SUBTITULO)
        self.screen.blit(sf, sf.get_rect(center=(cx, y_ini - s(28))))

        for i, texto in enumerate(pasos):
            y = y_ini + i * (ch + gap)
            self._tarjeta(texto, cx, y + ch // 2, cw, ch, (25, 65, 42), COLOR_LINEA)

    # Slide 2: clic/letra en tarjeta izq → flecha → slot en der
    def _visual_slide_2(self):
        cx_izq = ANCHO // 2 - s(240)
        cx_der = ANCHO // 2 + s(220)
        cy     = s(450)           # más abajo para dejar espacio al texto ampliado
        cw     = s(210); ch = s(50)

        # Tarjeta izquierda seleccionada (borde blanco indica que está activa)
        ri = pygame.Rect(cx_izq - cw//2, cy - ch//2, cw, ch)
        pygame.draw.rect(self.screen, (35, 90, 55), ri, border_radius=s(10))
        pygame.draw.rect(self.screen, COLOR_TITULO,  ri, s(3), border_radius=s(10))

        # Badge con letra "b" (ejemplo de atajo de teclado)
        badge_w = s(24); badge_h = s(24)
        badge_r = pygame.Rect(ri.left + s(7), cy - badge_h//2, badge_w, badge_h)
        pygame.draw.rect(self.screen, COLOR_LINEA, badge_r, border_radius=s(5))
        sf_let = self.fuentes["etiqueta"].render("b", True, COLOR_FONDO)
        self.screen.blit(sf_let, sf_let.get_rect(center=badge_r.center))

        sf = self.fuentes["descripcion"].render("Bañarse con jabón", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(midleft=(ri.left + badge_w + s(14), cy)))

        # Flecha de izq a der
        x1 = cx_izq + cw//2 + s(8)
        x2 = cx_der - cw//2 - s(12)
        pygame.draw.line(self.screen, COLOR_SUBTITULO, (x1, cy), (x2, cy), s(3))
        pygame.draw.polygon(self.screen, COLOR_SUBTITULO,
                            [(x2, cy - s(10)), (x2 + s(16), cy), (x2, cy + s(10))])

        # Slot destino (resaltado en verde)
        rd = pygame.Rect(cx_der - cw//2, cy - ch//2, cw, ch)
        pygame.draw.rect(self.screen, (35, 90, 55), rd, border_radius=s(10))
        pygame.draw.rect(self.screen, COLOR_VERDE,   rd, s(3), border_radius=s(10))

        # Badge con letra "b" también en el slot destino
        badge_r2 = pygame.Rect(rd.left + s(7), cy - badge_h//2, badge_w, badge_h)
        pygame.draw.rect(self.screen, COLOR_VERDE, badge_r2, border_radius=s(5))
        sf_let2 = self.fuentes["etiqueta"].render("b", True, COLOR_FONDO)
        self.screen.blit(sf_let2, sf_let2.get_rect(center=badge_r2.center))

        sf = self.fuentes["descripcion"].render("3.  Bañarse con jabón", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(midleft=(rd.left + badge_w + s(14), cy)))

        # Leyendas
        sf = self.fuentes["instruccion"].render(
            "Clic o tecla [letra] → va al primer lugar vacío", True, COLOR_PIE)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, cy + s(68))))
        sf = self.fuentes["instruccion"].render(
            "Clic o misma tecla sobre el paso ya colocado → vuelve a la lista", True, COLOR_PIE)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, cy + s(98))))

    # Slide 3: tres niveles con colores
    def _visual_slide_3(self):
        niveles = [
            ("Básico",     "4 pasos por actividad", COLOR_VERDE),
            ("Intermedio", "5 pasos por actividad", COLOR_AMARILLO),
            ("Avanzado",   "7 pasos por actividad", COLOR_ROJO),
        ]
        cy0 = s(360); sep = s(85); bw = s(360); bh = s(65)
        for i, (nombre, desc, color) in enumerate(niveles):
            cy   = cy0 + i * sep
            rect = pygame.Rect(ANCHO//2 - bw//2, cy - bh//2, bw, bh)
            pygame.draw.rect(self.screen, color, rect, border_radius=s(12))
            sf = self.fuentes["boton"].render(nombre, True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(midleft=(rect.left + s(20), rect.centery - s(8))))
            sf = self.fuentes["descripcion"].render(desc, True, COLOR_DESCRIPCION)
            self.screen.blit(sf, sf.get_rect(midleft=(rect.left + s(20), rect.centery + s(14))))

    # Slide 4: circulo verde con tilde (igual al N-Back)
    def _visual_slide_4(self):
        cx    = ANCHO // 2
        cy    = s(440)
        radio = s(80)
        pygame.draw.circle(self.screen, COLOR_BOTON_ACTIVO, (cx, cy), radio)
        pygame.draw.circle(self.screen, COLOR_LINEA,        (cx, cy), radio, s(4))
        p1 = (cx - s(32), cy)
        p2 = (cx - s(10), cy + s(28))
        p3 = (cx + s(38), cy - s(28))
        pygame.draw.lines(self.screen, COLOR_TITULO, False, [p1, p2, p3], s(7))

    def _dibujar_progreso(self):
        total     = self.N_SLIDES
        sep       = s(28)
        cx_inicio = ANCHO // 2 - (total - 1) * sep // 2
        cy        = ALTO - s(143)
        for i in range(total):
            cx = cx_inicio + i * sep
            if i == self.slide_actual:
                pygame.draw.circle(self.screen, COLOR_TITULO,       (cx, cy), s(9))
            else:
                pygame.draw.circle(self.screen, COLOR_BOTON_ACTIVO, (cx, cy), s(6))

    def _dibujar_botones_nav(self):
        if self.slide_actual > 0:
            c = COLOR_BOTON_HOVER if self.hover_ant else COLOR_BOTON_ACTIVO
            pygame.draw.rect(self.screen, c, self.boton_anterior, border_radius=s(14))
            sf = self.fuentes["boton"].render("← Anterior", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.boton_anterior.center))

        if self.slide_actual < self.N_SLIDES - 1:
            c = COLOR_BOTON_GRIS if not self.hover_salt else (90, 100, 92)
            pygame.draw.rect(self.screen, c, self.boton_saltear, border_radius=s(14))
            sf = self.fuentes["boton"].render("Saltear", True, COLOR_PIE)
            self.screen.blit(sf, sf.get_rect(center=self.boton_saltear.center))

        if self.slide_actual < self.N_SLIDES - 1:
            texto = "Siguiente →"
            color = COLOR_BOTON_HOVER if self.hover_sig else COLOR_BOTON_ACTIVO
        else:
            texto = "Iniciar"
            color = COLOR_VERDE_HOVER if self.hover_sig else COLOR_VERDE

        pygame.draw.rect(self.screen, color, self.boton_siguiente, border_radius=s(14))
        sf = self.fuentes["boton"].render(texto, True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.boton_siguiente.center))


# ════════════════════════════════════════════════════════════
#  SELECTOR DE NIVEL - SECUENCIACIÓN AVD
# ════════════════════════════════════════════════════════════
class SelectorNivelAVD:
    def __init__(self, screen, fuentes):
        self.screen        = screen
        self.fuentes       = fuentes
        self.siguiente     = None
        self.nivel_elegido = None
        self.boton_x       = pygame.Rect(s(20), s(20), s(52), s(52))
        self.hover_x       = False

        ab = s(420); alt = s(100); xc = (ANCHO - ab) // 2; yi = s(230)
        self.niveles = [
            {"nivel": 1, "texto": "Básico  (4 pasos)",
             "desc": "4 pasos por actividad  ·  4 actividades en total",
             "rect": pygame.Rect(xc, yi,          ab, alt), "hover": False},
            {"nivel": 2, "texto": "Intermedio  (5 pasos)",
             "desc": "5 pasos por actividad  ·  4 actividades en total",
             "rect": pygame.Rect(xc, yi + s(130), ab, alt), "hover": False},
            {"nivel": 3, "texto": "Avanzado  (7 pasos)",
             "desc": "7 pasos por actividad  ·  4 actividades en total",
             "rect": pygame.Rect(xc, yi + s(260), ab, alt), "hover": False},
        ]

    def manejar_eventos(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            p = ev.pos
            self.hover_x = self.boton_x.collidepoint(p)
            for n in self.niveles: n["hover"] = n["rect"].collidepoint(p)
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            p = ev.pos
            if self.boton_x.collidepoint(p):
                self.siguiente = "cognitivo"; return
            for n in self.niveles:
                if n["rect"].collidepoint(p):
                    # Enviamos el nivel al FormularioPaciente con tipo "avd"
                    self.siguiente = ("form_paciente", "avd", n["nivel"]); return

    def dibujar(self):
        self.screen.fill(COLOR_FONDO)
        cx = COLOR_ROJO_HOVER if self.hover_x else COLOR_ROJO
        pygame.draw.rect(self.screen, cx, self.boton_x, border_radius=s(10))
        sf = self.fuentes["boton"].render("X", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.boton_x.center))
        pygame.draw.line(self.screen, COLOR_LINEA, (s(60), s(100)), (ANCHO - s(60), s(100)), 2)
        sf = self.fuentes["titulo"].render("Seleccioná el nivel de dificultad", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(60))))
        for n in self.niveles:
            c = COLOR_BOTON_HOVER if n["hover"] else COLOR_BOTON_ACTIVO
            pygame.draw.rect(self.screen, c, n["rect"], border_radius=s(14))
            sf = self.fuentes["boton"].render(n["texto"], True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(midleft=(n["rect"].left + s(25), n["rect"].centery - s(16))))
            # max_ancho deja margen izquierdo (25) + margen derecho (20) para que no sobresalga
            max_ancho_desc = n["rect"].width - s(25) - s(20)
            render_en_lineas(self.screen, self.fuentes["descripcion"], n["desc"],
                             COLOR_DESCRIPCION, n["rect"].left + s(25),
                             n["rect"].centery + s(18), max_ancho_desc)


# ════════════════════════════════════════════════════════════
#  TEST SECUENCIACIÓN AVD
#
#  El paciente ve 4 actividades cotidianas una a la vez.
#  Para cada una, los pasos aparecen mezclados en la columna
#  izquierda. Con un clic los coloca en la columna derecha
#  (en el primer slot vacío). Otro clic los devuelve.
#  Al confirmar el orden, se muestra el feedback con ✓/✗
#  y el orden correcto. Al final, métricas globales y opción
#  de guardar en el JSON del paciente.
#
#  Referencia clínica: Baum et al. (2008) – EFPT
# ════════════════════════════════════════════════════════════
class TestAVD:

    N_ACTIVIDADES  = 4          # siempre 4 actividades por sesión
    PASOS_POR_NIVEL = {1: 4, 2: 5, 3: 7}

    def __init__(self, screen, fuentes, nivel, nombre, id_pac):
        self.screen    = screen
        self.fuentes   = fuentes
        self.nivel     = nivel      # 1 = básico, 2 = intermedio, 3 = avanzado
        self.nombre    = nombre
        self.id_pac    = id_pac
        self.siguiente = None
        self._reiniciar()

    # ─── Inicialización ───────────────────────────────────────
    def _reiniciar(self):
        """Reinicia el test desde el comienzo eligiendo 4 actividades al azar."""
        self.n_pasos = self.PASOS_POR_NIVEL[self.nivel]

        # Elegimos 4 actividades distintas al azar entre las 8 disponibles
        self.actividades = random.sample(list(ACTIVIDADES_AVD.keys()), self.N_ACTIVIDADES)

        self.idx_act  = 0              # índice de la actividad actual (0 a 3)
        self.estado   = "jugando"      # "jugando" | "fin"
        self.pausado  = False
        self.t_pausa_ini        = 0
        self.t_pausa_acum       = 0    # ms de pausa en la actividad actual
        self.t_pausa_acum_total = 0    # ms de pausa acumulados en todo el test

        self.resultados       = []     # lista de dicts, uno por actividad completada
        self.guardado         = False
        self.ruta_guardado    = ""

        # Cronómetro global del test
        self.t_inicio_total = pygame.time.get_ticks()
        self.t_fin_total    = None   # se fija cuando estado == "fin"

        # Botones del menú de pausa (iguales que N-Back y Stroop)
        bw = s(300)
        self.btn_pausa     = pygame.Rect(ANCHO - s(90), s(20), s(65), s(55))
        self.btn_reanudar  = pygame.Rect(ANCHO//2 - bw//2, s(290), bw, s(65))
        self.btn_reiniciar = pygame.Rect(ANCHO//2 - bw//2, s(375), bw, s(65))
        self.btn_menu      = pygame.Rect(ANCHO//2 - bw//2, s(460), bw, s(65))

        # Botones de la pantalla de fin
        self.btn_guardar  = pygame.Rect(ANCHO//2 - s(320), s(480), s(280), s(65))
        self.btn_eliminar = pygame.Rect(ANCHO//2 + s(40),  s(480), s(280), s(65))
        # Botón de observaciones: centrado debajo de guardar/eliminar
        self.btn_observaciones = pygame.Rect(ANCHO//2-s(255), s(570), s(510), s(62))

        # Estado del panel de observaciones
        self.modo_observaciones  = False   # True cuando el overlay de obs está abierto
        self.texto_observaciones = ""      # texto que escribe el terapeuta
        # Botones dentro del overlay de observaciones
        panel_y = ALTO // 2 - s(245)
        self.btn_guardar_obs   = pygame.Rect(ANCHO//2-s(280), panel_y+s(335), s(560), s(60))
        self.btn_descartar_obs = pygame.Rect(ANCHO//2-s(190), panel_y+s(415), s(380), s(55))

        # Botón "Confirmar orden" (pantalla de juego, solo activo cuando todos los slots están llenos)
        self.btn_confirmar = pygame.Rect(ANCHO//2 - s(200), ALTO - s(117), s(400), s(60))

        # Estados hover para todos los botones
        self.hov = {k: False for k in
                    ["pausa", "reanudar", "reiniciar", "menú",
                     "guardar", "eliminar", "confirmar",
                     "observaciones", "guardar_obs", "descartar_obs"]}

        # Cargamos la primera actividad
        self._cargar_actividad()

    def _cargar_actividad(self):
        """Prepara los datos de la actividad actual y reinicia el cronómetro."""
        nombre_act      = self.actividades[self.idx_act]
        self.nombre_act = nombre_act
        # Obtenemos los pasos correctos en el orden que el paciente debe reproducir
        self.pasos_ok   = list(ACTIVIDADES_AVD[nombre_act][self.n_pasos])

        # Mezclamos una copia de los pasos para mostrárselos desordenados al paciente
        # pasos_mezclados define también qué letra de teclado corresponde a cada paso (a, b, c...)
        mezclados = list(self.pasos_ok)
        random.shuffle(mezclados)
        self.pasos_mezclados = mezclados   # este orden no cambia durante la actividad

        # slots_der representa la columna derecha: lista con n_pasos posiciones.
        # None = slot vacío, string = paso que el paciente colocó ahí.
        self.slots_der = [None] * self.n_pasos

        # Reiniciamos el cronómetro y las pausas para esta actividad específica
        self.t_inicio_act = pygame.time.get_ticks()
        self.t_pausa_acum = 0

    # ─── Helpers de layout ────────────────────────────────────
    def _pasos_disponibles(self):
        """Devuelve los pasos que aún no fueron colocados en ningún slot."""
        en_slots = set(p for p in self.slots_der if p is not None)
        return [p for p in self.pasos_mezclados if p not in en_slots]

    def _rects_izq(self):
        """
        Calcula los Rect de las tarjetas de la columna izquierda
        (solo los pasos todavía disponibles).
        Devuelve lista de (texto_paso, Rect).
        """
        col_x  = s(60)
        col_w  = ANCHO // 2 - s(90)
        y_ini  = s(170)
        card_h = s(52)
        gap    = s(6)
        return [
            (paso, pygame.Rect(col_x, y_ini + i * (card_h + gap), col_w, card_h))
            for i, paso in enumerate(self._pasos_disponibles())
        ]

    def _rects_der(self):
        """
        Calcula los Rect de los slots de la columna derecha
        (siempre n_pasos slots, vacíos o llenos).
        Devuelve lista de (contenido_o_None, Rect).
        """
        col_x  = ANCHO // 2 + s(30)
        col_w  = ANCHO - s(60) - col_x
        y_ini  = s(152)
        card_h = s(52)
        gap    = s(6)
        return [
            (self.slots_der[i], pygame.Rect(col_x, y_ini + i * (card_h + gap), col_w, card_h))
            for i in range(self.n_pasos)
        ]

    def _todos_llenos(self):
        """True cuando el paciente colocó un paso en cada slot."""
        return all(p is not None for p in self.slots_der)

    def _tiempo_actividad_s(self):
        """Tiempo transcurrido en la actividad actual, en segundos, sin contar pausas."""
        if self.pausado:
            t = self.t_pausa_ini - self.t_inicio_act - self.t_pausa_acum
        else:
            t = pygame.time.get_ticks() - self.t_inicio_act - self.t_pausa_acum
        return max(0, t) // 1000

    def _tiempo_total_s(self):
        """Tiempo total del test, en segundos, sin contar pausas."""
        ref = self.t_fin_total if self.estado == "fin" else pygame.time.get_ticks()
        t = ref - self.t_inicio_total - self.t_pausa_acum_total
        return max(0, t) // 1000

    # ─── Lógica del test ──────────────────────────────────────
    def _confirmar_actividad(self):
        """
        Llamado cuando el paciente confirma su orden.
        Calcula el puntaje, guarda el resultado y pasa a la
        pantalla de feedback entre actividades.
        """
        correctos = sum(
            1 for i in range(self.n_pasos)
            if self.slots_der[i] == self.pasos_ok[i]
        )
        self.resultados.append({
            "nombre"          : self.nombre_act,
            "pasos_ok"        : list(self.pasos_ok),
            "orden_ingresado" : list(self.slots_der),
            "correctos"       : correctos,
            "total_pasos"     : self.n_pasos,
            "tiempo_s"        : self._tiempo_actividad_s(),
        })
        # Avanzamos directo a la siguiente actividad (o al fin si era la última)
        self.idx_act += 1
        if self.idx_act >= self.N_ACTIVIDADES:
            self.estado = "fin"
            self.t_fin_total = pygame.time.get_ticks()
        else:
            self._cargar_actividad()   # estado sigue siendo "jugando"

    def _metricas(self):
        """Calcula las métricas globales al finalizar el test completo."""
        total_correctos = sum(r["correctos"] for r in self.resultados)
        total_pasos     = self.n_pasos * len(self.resultados)
        precision       = round(total_correctos / total_pasos * 100, 1) if total_pasos else 0

        # Clasificación según Baum et al. (2008) – EFPT
        if   precision >= 80: clasif = "Normal"
        elif precision >= 60: clasif = "Limítrofe"
        else:                 clasif = "Patológico"

        return {
            "nivel"                : self.nivel,
            "actividades_evaluadas": len(self.resultados),
            "precision_porcentaje" : precision,
            "clasificacion"        : clasif,
            "rango_esperado"       : "≥80%",
            "fuente_rango"         : "Baum et al. (2008)",
            "tiempo_total_s"       : self._tiempo_total_s(),
            "detalle": [
                {
                    "nombre"          : r["nombre"],
                    "correctos"       : r["correctos"],
                    "total_pasos"     : r["total_pasos"],
                    "tiempo_s"        : r["tiempo_s"],
                    "orden_ingresado" : r["orden_ingresado"],
                    "orden_correcto"  : r["pasos_ok"],
                }
                for r in self.resultados
            ],
        }

    # ─── Manejo de eventos ────────────────────────────────────
    def manejar_eventos(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            p = ev.pos
            self.hov["pausa"] = self.btn_pausa.collidepoint(p)
            if self.pausado:
                self.hov["reanudar"]  = self.btn_reanudar.collidepoint(p)
                self.hov["reiniciar"] = self.btn_reiniciar.collidepoint(p)
                self.hov["menú"]      = self.btn_menu.collidepoint(p)
            if self.estado == "jugando":
                self.hov["confirmar"] = (self._todos_llenos() and
                                         self.btn_confirmar.collidepoint(p))
            if self.estado == "fin":
                self.hov["guardar"]       = self.btn_guardar.collidepoint(p)
                self.hov["eliminar"]      = self.btn_eliminar.collidepoint(p)
                self.hov["observaciones"] = self.btn_observaciones.collidepoint(p)
            if self.modo_observaciones:
                self.hov["guardar_obs"]   = self.btn_guardar_obs.collidepoint(p)
                self.hov["descartar_obs"] = self.btn_descartar_obs.collidepoint(p)

        # Captura de texto del teclado cuando el overlay de observaciones está abierto
        if ev.type == pygame.KEYDOWN and self.modo_observaciones:
            if ev.key == pygame.K_BACKSPACE:
                self.texto_observaciones = self.texto_observaciones[:-1]
            elif ev.key == pygame.K_RETURN:
                self.texto_observaciones += "\n"
            elif ev.unicode and ev.unicode.isprintable():
                self.texto_observaciones += ev.unicode
            return   # ninguna otra acción mientras se escribe

        # Atajos de teclado: cada paso tiene asignada una letra (a, b, c...) según su posición
        # en pasos_mezclados. Presionar la letra de un paso lo coloca en el primer slot vacío,
        # o lo devuelve si ya estaba en la columna derecha.
        if (ev.type == pygame.KEYDOWN and
                self.estado == "jugando" and
                not self.pausado and
                not self.modo_observaciones):
            # Enter confirma el orden cuando todos los slots están llenos
            if ev.key == pygame.K_RETURN and self._todos_llenos():
                self._confirmar_actividad()
            else:
                tecla = ev.unicode.lower() if ev.unicode else ""
                if tecla and tecla.isalpha():
                    # Convertimos la letra a un índice: 'a'→0, 'b'→1, 'c'→2, etc.
                    idx_letra = ord(tecla) - ord('a')
                    if 0 <= idx_letra < len(self.pasos_mezclados):
                        paso = self.pasos_mezclados[idx_letra]
                        if paso in self.slots_der:
                            # El paso ya estaba en la columna derecha → lo devolvemos a disponibles
                            self.slots_der[self.slots_der.index(paso)] = None
                        elif paso in self._pasos_disponibles():
                            # El paso está disponible → lo colocamos en el primer slot vacío
                            for j in range(self.n_pasos):
                                if self.slots_der[j] is None:
                                    self.slots_der[j] = paso
                                    break

        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            p = ev.pos

            # Si el overlay de observaciones está abierto, solo sus botones responden
            if self.modo_observaciones:
                if self.btn_guardar_obs.collidepoint(p):
                    m = self._metricas()
                    self.ruta_guardado = guardar_json_avd(
                        self.id_pac, self.nombre, m,
                        observaciones=self.texto_observaciones)
                    self.guardado = True
                    self.modo_observaciones = False
                    self.btn_eliminar = pygame.Rect(ANCHO//2 - s(140), s(480), s(280), s(65))
                elif self.btn_descartar_obs.collidepoint(p):
                    self.texto_observaciones = ""
                    self.modo_observaciones  = False
                return

            # El menú de pausa tiene prioridad sobre todo lo demás
            if self.pausado:
                if self.btn_reanudar.collidepoint(p):
                    dur = pygame.time.get_ticks() - self.t_pausa_ini
                    self.t_pausa_acum       += dur
                    self.t_pausa_acum_total += dur
                    self.pausado = False
                elif self.btn_reiniciar.collidepoint(p):
                    self._reiniciar()
                elif self.btn_menu.collidepoint(p):
                    self.siguiente = "cognitivo"
                return

            # Pantalla de fin
            if self.estado == "fin":
                if self.btn_guardar.collidepoint(p) and not self.guardado:
                    m = self._metricas()
                    self.ruta_guardado = guardar_json_avd(self.id_pac, self.nombre, m)
                    self.guardado = True
                    # Reposicionamos el botón al centro ahora que es el único
                    self.btn_eliminar = pygame.Rect(ANCHO//2 - s(140), s(480), s(280), s(65))
                elif self.btn_eliminar.collidepoint(p):
                    self.siguiente = "cognitivo"
                elif self.btn_observaciones.collidepoint(p) and not self.guardado:
                    self.modo_observaciones = True
                return

            # Botón pausa (solo durante "jugando")
            if self.btn_pausa.collidepoint(p) and self.estado == "jugando":
                self.pausado     = True
                self.t_pausa_ini = pygame.time.get_ticks()
                return

            # Interacción principal durante "jugando"
            if self.estado == "jugando" and not self.pausado:

                # ¿Clic en "Confirmar orden"? (solo si todos los slots están llenos)
                if self._todos_llenos() and self.btn_confirmar.collidepoint(p):
                    self._confirmar_actividad()
                    return

                # ¿Clic en un slot ocupado de la columna derecha? → devolver paso
                for i, (contenido, r) in enumerate(self._rects_der()):
                    if r.collidepoint(p) and contenido is not None:
                        self.slots_der[i] = None   # libera el slot
                        return

                # ¿Clic en una tarjeta de la columna izquierda? → colocar en primer slot vacío
                for paso, r in self._rects_izq():
                    if r.collidepoint(p):
                        for j in range(self.n_pasos):
                            if self.slots_der[j] is None:
                                self.slots_der[j] = paso
                                break
                        return

    # ─── Dibujo ───────────────────────────────────────────────
    def dibujar(self):
        self.screen.fill(COLOR_FONDO)

        if self.estado == "fin":
            self._dibujar_fin()
            if self.modo_observaciones:
                dibujar_overlay_observaciones(
                    self.screen, self.fuentes, self.texto_observaciones,
                    self.hov, self.btn_guardar_obs, self.btn_descartar_obs)
            return

        # Estado "jugando"
        self._dibujar_jugando()
        if self.pausado:
            self._dibujar_pausa()

    def _dibujar_jugando(self):
        """Pantalla principal: encabezado, columna izq (disponibles), columna der (slots)."""

        # ── Encabezado ─────────────────────────────────────────
        pygame.draw.line(self.screen, COLOR_LINEA, (s(60), s(90)), (ANCHO - s(60), s(90)), 2)
        nivel_txt = {1: "Básico", 2: "Intermedio", 3: "Avanzado"}[self.nivel]
        sf = self.fuentes["casa"].render(
            f"Secuenciación AVD  |  Nivel: {nivel_txt}  |  "
            f"Actividad: {self.idx_act + 1} de {self.N_ACTIVIDADES}",
            True, COLOR_SUBTITULO)
        self.screen.blit(sf, sf.get_rect(midleft=(s(60), s(55))))

        # Botón pausa
        cp = COLOR_AMARILLO_HOVER if self.hov["pausa"] else COLOR_AMARILLO
        pygame.draw.rect(self.screen, cp, self.btn_pausa, border_radius=s(10))
        sf = self.fuentes["boton"].render("II", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=self.btn_pausa.center))

        # ── Cabeceras de las columnas ───────────────────────────
        col_izq_cx = s(60) + (ANCHO // 2 - s(90)) // 2
        col_der_cx = ANCHO // 2 + s(30) + (ANCHO - s(60) - ANCHO // 2 - s(30)) // 2

        # Nombre de la actividad encima de la columna izquierda
        sf = self.fuentes["titulo"].render(self.nombre_act, True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(col_izq_cx, s(118))))

        sf = self.fuentes["instruccion"].render("Pasos disponibles", True, COLOR_SUBTITULO)
        self.screen.blit(sf, sf.get_rect(center=(col_izq_cx, s(148))))
        sf = self.fuentes["instruccion"].render("Tu orden  (clic para quitar)", True, COLOR_SUBTITULO)
        self.screen.blit(sf, sf.get_rect(center=(col_der_cx, s(134))))

        # Línea divisoria vertical entre las dos columnas
        pygame.draw.line(self.screen, COLOR_LINEA,
                         (ANCHO // 2, s(100)), (ANCHO // 2, ALTO - s(93)), 1)

        # ── Columna izquierda: pasos disponibles (tarjetas clicables) ──
        mouse_pos = pygame.mouse.get_pos()
        for paso, r in self._rects_izq():
            hover = r.collidepoint(mouse_pos) and not self.pausado
            fondo = (35, 90, 55) if hover else (25, 65, 42)
            pygame.draw.rect(self.screen, fondo, r, border_radius=s(10))
            pygame.draw.rect(self.screen, COLOR_LINEA, r, s(2), border_radius=s(10))

            # Badge con la letra asignada al paso (posición en pasos_mezclados)
            idx_paso = self.pasos_mezclados.index(paso)
            letra    = chr(ord('a') + idx_paso)
            badge_w  = s(26)
            badge_r  = pygame.Rect(r.left + s(8), r.centery - s(13), badge_w, s(26))
            pygame.draw.rect(self.screen, COLOR_LINEA, badge_r, border_radius=s(5))
            sf_let = self.fuentes["etiqueta"].render(letra, True, COLOR_FONDO)
            self.screen.blit(sf_let, sf_let.get_rect(center=badge_r.center))

            # Texto del paso (comienza después del badge)
            x_texto = r.left + s(8) + badge_w + s(8)
            ancho_texto = r.right - x_texto - s(8)
            sf = self.fuentes["instruccion"].render(paso, True, COLOR_TITULO)
            if sf.get_width() > ancho_texto:
                sf = self.fuentes["etiqueta"].render(paso, True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(midleft=(x_texto, r.centery)))

        # ── Columna derecha: slots numerados ───────────────────
        for i, (contenido, r) in enumerate(self._rects_der()):
            if contenido is not None:
                # Slot ocupado: verde, clic lo devuelve
                hover = r.collidepoint(mouse_pos) and not self.pausado
                fondo = (45, 110, 68) if hover else (35, 90, 55)
                pygame.draw.rect(self.screen, fondo, r, border_radius=s(10))
                pygame.draw.rect(self.screen, COLOR_VERDE, r, s(2), border_radius=s(10))

                # Badge con la letra del paso (igual que en columna izquierda)
                idx_paso  = self.pasos_mezclados.index(contenido)
                letra     = chr(ord('a') + idx_paso)
                badge_w   = s(26)
                badge_r   = pygame.Rect(r.left + s(8), r.centery - s(13), badge_w, s(26))
                pygame.draw.rect(self.screen, COLOR_VERDE, badge_r, border_radius=s(5))
                sf_let = self.fuentes["etiqueta"].render(letra, True, COLOR_FONDO)
                self.screen.blit(sf_let, sf_let.get_rect(center=badge_r.center))

                # Número de slot + texto del paso
                x_texto    = r.left + s(8) + badge_w + s(8)
                ancho_texto = r.right - x_texto - s(8)
                texto = f"{i + 1}.  {contenido}"
                sf = self.fuentes["instruccion"].render(texto, True, COLOR_TITULO)
                if sf.get_width() > ancho_texto:
                    sf = self.fuentes["etiqueta"].render(texto, True, COLOR_TITULO)
                self.screen.blit(sf, sf.get_rect(midleft=(x_texto, r.centery)))
            else:
                # Slot vacío: contorno tenue con número
                pygame.draw.rect(self.screen, (25, 55, 35), r, border_radius=s(10))
                pygame.draw.rect(self.screen, (60, 90, 65), r, s(2), border_radius=s(10))
                sf = self.fuentes["etiqueta"].render(f"{i + 1}.", True, COLOR_PIE)
                self.screen.blit(sf, sf.get_rect(midleft=(r.left + s(14), r.centery)))

        # ── Botón "Confirmar orden" ─────────────────────────────
        listo = self._todos_llenos()
        c  = (COLOR_VERDE_HOVER if self.hov["confirmar"] else COLOR_VERDE) if listo else COLOR_BOTON_GRIS
        ct = COLOR_TEXTO_BOTON if listo else COLOR_TEXTO_GRIS
        pygame.draw.rect(self.screen, c, self.btn_confirmar, border_radius=s(14))
        sf = self.fuentes["boton"].render("Confirmar orden", True, ct)
        self.screen.blit(sf, sf.get_rect(center=self.btn_confirmar.center))

    def _dibujar_pausa(self):
        """Overlay de pausa (igual al de N-Back y Stroop)."""
        ov = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        self.screen.blit(ov, (0, 0))
        caja = pygame.Rect(ANCHO//2 - s(210), s(195), s(420), s(370))
        pygame.draw.rect(self.screen, (20, 55, 35), caja, border_radius=s(18))
        pygame.draw.rect(self.screen, COLOR_LINEA,  caja, 2, border_radius=s(18))
        sf = self.fuentes["titulo"].render("Test pausado", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(245))))

        for btn, color, hover_color, etiq in [
            (self.btn_reanudar,  COLOR_VERDE,    COLOR_VERDE_HOVER,    "Reanudar"),
            (self.btn_reiniciar, COLOR_ROJO,     COLOR_ROJO_HOVER,     "Reiniciar"),
            (self.btn_menu,      COLOR_AMARILLO, COLOR_AMARILLO_HOVER, "Volver al menú"),
        ]:
            key = etiq.lower().replace(" al menú", "").replace(" ", "")
            c   = hover_color if self.hov.get(key, False) else color
            pygame.draw.rect(self.screen, c, btn, border_radius=s(12))
            sf = self.fuentes["boton"].render(etiq, True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=btn.center))

    def _dibujar_fin(self):
        """Pantalla de resultados finales del test completo."""
        pygame.draw.line(self.screen, COLOR_LINEA, (s(60), s(100)), (ANCHO - s(60), s(100)), 2)
        sf = self.fuentes["grande"].render("Test finalizado", True, COLOR_TITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(65))))

        m     = self._metricas()
        prec  = m.get("precision_porcentaje", 0)
        clas  = m.get("clasificacion", "")
        t_s   = m.get("tiempo_total_s", 0)
        cc    = {"Normal": COLOR_VERDE, "Limítrofe": COLOR_AMARILLO,
                 "Patológico": COLOR_ROJO}.get(clas, COLOR_TITULO)

        sf = self.fuentes["subtitulo"].render(
            f"Precisión: {prec}%     Clasificación: {clas}", True, cc)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(150))))
        sf = self.fuentes["descripcion"].render(
            "Rango normal: ≥80%  (Baum et al., 2008)", True, COLOR_SUBTITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(186))))
        sf = self.fuentes["descripcion"].render(
            f"Tiempo total: {t_s} segundos", True, COLOR_SUBTITULO)
        self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(218))))

        # Resumen por actividad
        pygame.draw.line(self.screen, COLOR_LINEA, (s(60), s(245)), (ANCHO - s(60), s(245)), 1)
        y_res = s(260)
        for i, res in enumerate(self.resultados):
            col_r = COLOR_VERDE if res["correctos"] == res["total_pasos"] else COLOR_SUBTITULO
            texto = (f"{i + 1}. {res['nombre']}  —  "
                     f"{res['correctos']}/{res['total_pasos']} pasos correctos  "
                     f"({res['tiempo_s']} s)")
            sf = self.fuentes["descripcion"].render(texto, True, col_r)
            self.screen.blit(sf, sf.get_rect(midleft=(s(80), y_res)))
            y_res += s(40)

        pygame.draw.line(self.screen, COLOR_LINEA, (s(60), s(450)), (ANCHO - s(60), s(450)), 1)

        if self.guardado:
            sf = self.fuentes["instruccion"].render(
                f"Guardado en: {self.ruta_guardado}", True, COLOR_VERDE)
            self.screen.blit(sf, sf.get_rect(center=(ANCHO // 2, s(465))))
            cv = COLOR_VERDE_HOVER if self.hov["eliminar"] else COLOR_VERDE
            pygame.draw.rect(self.screen, cv, self.btn_eliminar, border_radius=s(14))
            sf = self.fuentes["boton"].render("Volver al menú", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.btn_eliminar.center))
        else:
            cg = COLOR_VERDE_HOVER if self.hov["guardar"] else COLOR_VERDE
            pygame.draw.rect(self.screen, cg, self.btn_guardar, border_radius=s(14))
            sf = self.fuentes["boton"].render("Guardar resultados", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.btn_guardar.center))

            ce = COLOR_ROJO_HOVER if self.hov["eliminar"] else COLOR_ROJO
            pygame.draw.rect(self.screen, ce, self.btn_eliminar, border_radius=s(14))
            sf = self.fuentes["boton"].render("Eliminar intento", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.btn_eliminar.center))

            # Botón de observaciones: centrado debajo de los dos botones principales
            co = COLOR_AZUL_HOVER if self.hov["observaciones"] else COLOR_AZUL
            pygame.draw.rect(self.screen, co, self.btn_observaciones, border_radius=s(14))
            sf = self.fuentes["instruccion"].render("Agregar observaciones del terapeuta", True, COLOR_TITULO)
            self.screen.blit(sf, sf.get_rect(center=self.btn_observaciones.center))


# ════════════════════════════════════════════════════════════
#  LOOP PRINCIPAL
# ════════════════════════════════════════════════════════════
def main():
    # Creamos la ventana a pantalla completa según el tamaño detectado al inicio
    screen  = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("OpenRehab ACV")
    reloj   = pygame.time.Clock()
    fuentes = cargar_fuentes()

    # La app arranca siempre en el menú principal
    pantalla = MenuPrincipal(screen, fuentes)

    # Loop principal: se ejecuta a 60 FPS hasta que el usuario cierra la app
    while True:
        # Procesamos todos los eventos del frame (clics, teclas, cierre de ventana)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            pantalla.manejar_eventos(ev)

        # Los tests con temporizador necesitan actualizar su estado interno en cada frame.
        # TestAVD no necesita actualizar() porque no tiene estados con temporizador.
        if isinstance(pantalla, (TestNBack, TestStroop)):
            pantalla.actualizar()

        # Sistema de navegación entre pantallas:
        # Cada pantalla tiene self.siguiente = None mientras está activa.
        # Cuando el usuario hace clic en algo que cambia de pantalla, self.siguiente se llena
        # con un string o tupla que indica a qué pantalla ir y con qué datos.
        sig = pantalla.siguiente
        if sig is not None:
            # Rutas del N-Back
            if   sig == "cognitivo":           pantalla = MenuCognitivo(screen, fuentes)
            elif sig == "principal":           pantalla = MenuPrincipal(screen, fuentes)
            elif sig == "instrucciones_nback": pantalla = InstruccionesNBack(screen, fuentes)
            elif sig == "nivel_nback":         pantalla = SelectorNivelNBack(screen, fuentes)
            elif sig == "form_paciente_nback":
                nivel = pantalla.nivel_elegido
                pantalla = FormularioPaciente(screen, fuentes, nivel)
            elif isinstance(sig, tuple) and sig[0] == "test_nback":
                # La tupla trae el nivel, nombre del paciente e ID para pasárselos al test
                _, nivel, nombre, id_pac = sig
                pantalla = TestNBack(screen, fuentes, nivel, nombre, id_pac)
            # Rutas del Efecto Stroop
            elif sig == "instrucciones_stroop":
                pantalla = InstruccionesStroop(screen, fuentes)
            elif sig == "nivel_stroop":
                pantalla = SelectorNivelStroop(screen, fuentes)
            elif isinstance(sig, tuple) and sig[0] == "estimulos_stroop":
                _, nivel_str = sig
                pantalla = SelectorEstimulosStroop(screen, fuentes, nivel_str)
            elif isinstance(sig, tuple) and sig[0] == "form_paciente" and sig[1] == "stroop":
                _, _, nivel_str, cantidad = sig
                pantalla = FormularioPaciente(screen, fuentes, nivel_str,
                                              test_tipo="stroop", cantidad=cantidad)
            elif isinstance(sig, tuple) and sig[0] == "test_stroop":
                _, nivel_str, cantidad, nombre, id_pac = sig
                pantalla = TestStroop(screen, fuentes, nivel_str, cantidad, nombre, id_pac)
            # Rutas de la Secuenciación AVD
            elif sig == "instrucciones_avd":
                pantalla = InstruccionesAVD(screen, fuentes)
            elif sig == "nivel_avd":
                pantalla = SelectorNivelAVD(screen, fuentes)
            elif isinstance(sig, tuple) and sig[0] == "form_paciente" and sig[1] == "avd":
                _, _, nivel_avd = sig
                pantalla = FormularioPaciente(screen, fuentes, nivel_avd, test_tipo="avd")
            elif isinstance(sig, tuple) and sig[0] == "test_avd":
                _, nivel_avd, nombre, id_pac = sig
                pantalla = TestAVD(screen, fuentes, nivel_avd, nombre, id_pac)

        # Dibujamos la pantalla actual y actualizamos el display
        pantalla.dibujar()
        pygame.display.flip()
        reloj.tick(FPS)

if __name__ == "__main__":
    main()
