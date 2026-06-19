# OBSOLETO: server.py ya escucha este mismo puerto UDP directamente (ver la
# seccion "3c. Puente con el dispositivo" en server.py) y reenvia los eventos
# al navegador por WebSocket. No correr este script al mismo tiempo que el
# backend: los dos no pueden escuchar el mismo puerto UDP a la vez.
#
# Se deja como referencia de como se probo el paso 1 (ESP32 -> UDP -> PC)
# antes de integrarlo a server.py.

import socket

PUERTO = 4210

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", PUERTO))

print(f"Escuchando paquetes UDP en el puerto {PUERTO}... (Ctrl+C para salir)")

while True:
    datos, direccion = sock.recvfrom(1024)
    mensaje = datos.decode("utf-8", errors="replace")
    print(f"Llego desde {direccion[0]}: {mensaje}")
