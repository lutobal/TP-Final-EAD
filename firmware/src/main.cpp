#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL345_U.h>
#include <U8g2lib.h>     // Librería para la pantalla OLED
#include <WiFi.h>        // Conexión WiFi del ESP32
#include <WiFiUdp.h>      // Envío de paquetes UDP (botones -> PC)


// WIFI Y UDP: conexión con la PC (backend NeuroRehab).

const char* WIFI_SSID = "Luana";         // <-- completar con el nombre del hotspot
const char* WIFI_PASSWORD = "12345678"; // <-- completar con la contraseña del hotspot

IPAddress IP_PC(172, 20, 10, 4); // IP de la PC dentro de la red WiFi actual
const unsigned int PUERTO_UDP = 4210; // ESP32 -> PC (eventos de botones)

WiFiUDP udp;


//Seteamos los pines a los que asociamos cada componente
int boton_rojo = 5;
int boton_verde = 17;
int boton_azul = 18;
int boton_amarillo = 19;

int stick_X = 32;
int stick_Y = 35;
int stick_Boton = 34;
// Para mandar la posicion del joystick por UDP cada cierto tiempo, no en
// cada vuelta de loop() (ver uso mas abajo).
unsigned long ultimoTiempoJoystick = 0;
const unsigned long intervaloJoystickMs = 150;

//Pines del encoder
int Rot_CLK = 25;          //CLK--> detecta que el encoder se movió, que hubo un paso de giro.
int Rot_DT = 26;           // DT es la referencia; comparando CLK con DT, se interpreta la dirección del giro (derecha o izquierda)
int Rot_SW = 27;          //Botón del encoder

// Estado anterior de cada boton (rojo/verde/azul/amarillo/stick/encoder) +
// el momento del ultimo evento aceptado: sirve para detectar SOLO el
// flanco de bajada (el instante exacto HIGH->LOW en que se aprieta), no
// reenviar el mismo evento mientras el boton sigue apretado. Reemplaza el
// viejo "if presionado -> delay(200)": ese delay() bloqueaba TODO loop()
// (con el, tambien la recepcion de comandos UDP que prenden los LEDs)
// durante 200ms cada vez que se apretaba un boton.
const unsigned long DEBOUNCE_BOTON_MS = 30; // filtra el rebote mecanico del contacto
int estadoAnteriorBotonRojo = HIGH;
int estadoAnteriorBotonVerde = HIGH;
int estadoAnteriorBotonAzul = HIGH;
int estadoAnteriorBotonAmarillo = HIGH;
int estadoAnteriorBotonStick = HIGH;
int estadoAnteriorBotonEncoder = HIGH;
unsigned long ultimoEventoBotonRojo = 0;
unsigned long ultimoEventoBotonVerde = 0;
unsigned long ultimoEventoBotonAzul = 0;
unsigned long ultimoEventoBotonAmarillo = 0;
unsigned long ultimoEventoBotonStick = 0;
unsigned long ultimoEventoBotonEncoder = 0;

// Devuelve true una sola vez por apretada real (flanco HIGH->LOW), sin
// bloquear con delay(). Cada boton llama a esto con sus propias variables
// de estado/tiempo (ver declaracion arriba).
bool flancoDescendente(int pin, int &estadoAnterior, unsigned long &ultimoEvento) {
  int estadoActual = digitalRead(pin);
  bool disparado = (estadoActual == LOW && estadoAnterior == HIGH &&
                     millis() - ultimoEvento > DEBOUNCE_BOTON_MS);
  if (disparado) ultimoEvento = millis();
  estadoAnterior = estadoActual;
  return disparado;
}

//Lógica del encoder: cuando giras la perilla, el pin va cambiando entre high y low, se detectan los cambios y se interpreta: "Hubo un paso de giro"
//giro a la derecha --> +1 paso. Giro a la izquierda--> -1 paso.

//ESTO SE QUEDA O SE VA?
//Se lee por INTERRUPCION (no por polling en loop()) porque loop() tiene
//varios delay() (botones, joystick): mientras el programa está parado en
//un delay(), un giro rápido del encoder genera varios pulsos que el
//polling se pierde, el algoritmo queda desincronizado, y el síntoma es
//justo el que se vio: parecía que siempre giraba "a la derecha" y solo
//detectaba "izquierda" al cambiar de sentido. Con la interrupción, cada
//pulso se captura en el instante exacto en que ocurre.

//Volatile indica que no se debe confiar en el valor viejo, sino que el valo del encoder puede cambiar en cualquier momento
//Si lo ponemos adentro del loop, el contador volvería a cero en cada vuelta 
volatile long contadorEncoder = 0; // Cuenta total de pasos (para debug/referencia)
volatile long contadorEncoderPendiente = 0; // Pasos sin "drenar" todavía hacia UDP/Serial desde loop()
volatile unsigned long ultimoPulsoEncoderUs = 0;
const unsigned long DEBOUNCE_ENCODER_US = 1000; // 1 ms: filtra el rebote del contacto mecánico

void IRAM_ATTR isrEncoder() {
  unsigned long ahoraUs = micros();
  if (ahoraUs - ultimoPulsoEncoderUs < DEBOUNCE_ENCODER_US) return;
  ultimoPulsoEncoderUs = ahoraUs;

  // Invertido respecto a la comparación "de manual": en este cableado
  // físico daba derecha/izquierda al revés de lo esperado.
  if (digitalRead(Rot_DT) != digitalRead(Rot_CLK)) {
    contadorEncoder++;
    contadorEncoderPendiente++;
  } else {
    contadorEncoder--;
    contadorEncoderPendiente--;
  }
}

// Creamos el objeto del acelerómetro.
// A partir de ahora, vamos a usar "acelerometro" para pedirle datos al sensor.
Adafruit_ADXL345_Unified acelerometro = Adafruit_ADXL345_Unified(12345);
// Para leer el acelerómetro cada cierto tiempo sin frenar todo el programa
unsigned long ultimoTiempoAcelerometro = 0;
const unsigned long intervaloAcelerometro = 300;
// Si no se detecta el acelerometro en setup(), queda en false y loop() se
// salta su lectura (para poder probar otros componentes sin tenerlo conectado).
bool acelerometroOK = false;


//LEDs
int LED_AMARILLO = 33;
int LED_ROJO = 16;
int LED_VERDE = 21;
int LED_AZUL = 4;

//OLED
U8G2_SH1106_128X64_NONAME_F_SW_I2C display(
    U8G2_R0,
    13,              // SCL
    14,              // SDA
    U8X8_PIN_NONE    // RESET
);

// Corrimiento horizontal de todo el texto: este panel recorta los primeros
// pixeles contra el borde izquierdo (se veia "ENU" en vez de "MENU"), asi
// que se arranca a dibujar mas adentro en vez de en x=0.
const int OLED_OFFSET_X = 11;


void mostrarEstado(String test, int aciertos, int errores)
{
    // Borra todo lo que había en el buffer gráfico
    display.clearBuffer();

    // Selecciona fuente para el título
    display.setFont(u8g2_font_ncenB08_tr);

    // Escribe el nombre del proyecto
    display.drawStr(OLED_OFFSET_X, 12, "NeuroRehab");

    // Cambia a una fuente más chica
    display.setFont(u8g2_font_6x10_tr);

    // --------------------------------------------------
    // Nombre del test
    // --------------------------------------------------
    display.setCursor(OLED_OFFSET_X, 30);
    display.print("Test: ");
    display.print(test);

    // --------------------------------------------------
    // Cantidad de aciertos
    // --------------------------------------------------
    display.setCursor(OLED_OFFSET_X, 45);
    display.print("Aciertos: ");
    display.print(aciertos);

    // --------------------------------------------------
    // Cantidad de errores
    // --------------------------------------------------
    display.setCursor(OLED_OFFSET_X, 60);
    display.print("Errores: ");
    display.print(errores);

    // Envía el contenido del buffer a la OLED
    display.sendBuffer();
}

//Función para mostrar mensaje
void mostrarMensajeOLED(String mensaje)
{
    display.clearBuffer();

    display.setFont(u8g2_font_ncenB08_tr);
    display.drawStr(OLED_OFFSET_X, 12, "NeuroRehab");

    display.setFont(u8g2_font_6x10_tr);
    display.setCursor(OLED_OFFSET_X, 35);
    display.print(mensaje);

    display.sendBuffer();
}

//Muestra varias líneas cortas en la OLED, separadas por ';' en el texto que
//llega (lo usa el resultado final de un test: nombre del test + 1-2 métricas).
void mostrarLineasOLED(String texto)
{
    display.clearBuffer();

    display.setFont(u8g2_font_ncenB08_tr);
    display.drawStr(OLED_OFFSET_X, 12, "NeuroRehab");

    display.setFont(u8g2_font_6x10_tr);
    int y = 28;
    int inicio = 0;
    while (inicio < (int)texto.length() && y <= 60) {
        int fin = texto.indexOf(';', inicio);
        if (fin == -1) fin = texto.length();
        display.setCursor(OLED_OFFSET_X, y);
        display.print(texto.substring(inicio, fin));
        y += 14;
        inicio = fin + 1;
    }

    display.sendBuffer();
}

//Pantalla del menú principal: se usa al arrancar el ESP32 y también cada vez
//que el frontend pide volver a este estado neutro (comando "OLED_MENU", que
//manda home.html cada vez que se entra a esa página) para no dejar pegada
//en la pantalla la info del último test que se jugó.
void mostrarMenuOLED() {
    display.clearBuffer();
    display.setFont(u8g2_font_ncenB14_tr);
    display.drawStr(OLED_OFFSET_X, 25, "MENU");
    display.setFont(u8g2_font_6x10_tr);
    display.drawStr(OLED_OFFSET_X, 50, "Elegi un test...");
    display.sendBuffer();
}

//Prende/apaga los LEDs y maneja la OLED según el comando recibido por UDP
//desde el backend: "LED_ROJO"/"LED_VERDE"/"LED_AZUL"/"LED_AMARILLO"/"LED_OFF"
//(estímulos de N-Back y pruebas manuales desde /api/dispositivo/comando),
//"OLED_TIMER:<segundos>" mientras corre un test con timer (Tracking, Faro,
//Laberinto), "OLED_MENSAJE:<texto>" mientras corre un test sin timer
//(Stroop, N-Back; por ejemplo, el nombre del test), "OLED_RESULTADO:
//<linea1>;<linea2>;..." al terminar cualquier test, y "OLED_MENU" para
//volver a la pantalla del menú principal (lo manda home.html).
void procesarComandoLED(String comando) {
  if (comando.startsWith("OLED_TIMER:")) {
    mostrarMensajeOLED("Tiempo: " + comando.substring(11) + "s");
    return;
  }

  if (comando.startsWith("OLED_MENSAJE:")) {
    mostrarMensajeOLED(comando.substring(13));
    return;
  }

  if (comando.startsWith("OLED_RESULTADO:")) {
    mostrarLineasOLED(comando.substring(15));
    return;
  }

  if (comando == "OLED_MENU") {
    mostrarMenuOLED();
    return;
  }

  if (comando == "LED_ROJO") {
    digitalWrite(LED_ROJO, HIGH);
    Serial.println("LED ROJO ENCENDIDO");
  }

  else if (comando == "LED_VERDE") {
    digitalWrite(LED_VERDE, HIGH);
    Serial.println("LED VERDE ENCENDIDO");
  }

  else if (comando == "LED_AZUL") {
    digitalWrite(LED_AZUL, HIGH);
    Serial.println("LED AZUL ENCENDIDO");
  }

  else if (comando == "LED_AMARILLO") {
    digitalWrite(LED_AMARILLO, HIGH);
    Serial.println("LED AMARILLO ENCENDIDO");
  }

  else if (comando == "LED_OFF") {
    digitalWrite(LED_AMARILLO, LOW);
    digitalWrite(LED_ROJO, LOW);
    digitalWrite(LED_VERDE, LOW);
    digitalWrite(LED_AZUL, LOW);
    Serial.println("TODOS LOS LEDS APAGADOS");
  }

  else {
    Serial.print("Comando no reconocido: ");
    Serial.println(comando);
  }
}

//Void setup--> configura los inputs y outputs por default en el arduino, sin que haga nada
void setup() {
  
  Serial.begin(115200); //Establece la comunicación entre el SP32 y la computadora

  //Conexion WiFi (necesaria para mandar eventos por UDP a la PC)
  // WiFi.mode(WIFI_STA) + disconnect(true) antes de begin(): el ESP32 a
  // veces arranca con el modo/credenciales de una conexion anterior
  // guardada en flash, lo que hace que begin() se quede pegado. Forzar
  // modo estacion y descartar esa conexion vieja antes de conectar evita eso.
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(true);
  delay(100);

  // Reduce la potencia de transmision del radio WiFi. A maxima potencia
  // (default WIFI_POWER_19_5dBm) el pico de corriente del radio al
  // transmitir es el consumo mas alto de toda la placa, y alimentando todo
  // (OLED + acelerometro + LEDs + WiFi) desde el USB de una compu puede
  // hacer caer la tension y resetear el ESP32 a medio programa. Como el
  // hotspot esta cerca, bajar la potencia no debería afectar la conexion.
  WiFi.setTxPower(WIFI_POWER_8_5dBm);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Conectando a WiFi");

  // Con timeout (no "while" infinito): si el hotspot no esta disponible,
  // el resto del hardware (botones, encoder, acelerometro, LEDs, OLED) se
  // configura igual mas abajo. Sin este timeout, una falla de WiFi dejaba
  // TODO el resto sin inicializar para siempre.
  unsigned long inicioWiFi = millis();
  const unsigned long TIMEOUT_WIFI_MS = 15000;
  while (WiFi.status() != WL_CONNECTED && millis() - inicioWiFi < TIMEOUT_WIFI_MS) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi conectado. IP del ESP32: ");
    Serial.println(WiFi.localIP());

    // Apaga el modo de ahorro de energia del WiFi: con el ahorro de energia
    // activado (que es el default), el ESP32 "duerme" el radio a ratos y
    // puede perderse paquetes UDP entrantes que lleguen justo en ese momento
    // (no afecta lo que el ESP32 manda, solo lo que recibe).
    WiFi.setSleep(false);
  } else {
    Serial.print("AVISO: no conecto al WiFi en ");
    Serial.print(TIMEOUT_WIFI_MS / 1000);
    Serial.println("s (codigo de estado WiFi.status() impreso abajo). Sigue intentando" \
                    " solo en background; mientras tanto no manda/recibe eventos UDP," \
                    " pero el resto del hardware funciona igual.");
    Serial.print("Codigo WiFi.status(): ");
    Serial.println(WiFi.status());
  }

  udp.begin(PUERTO_UDP);

  // Avisa al backend "acá estoy" apenas el socket UDP está listo. El
  // backend no tiene la IP del ESP32 escrita a mano: la aprende del
  // remitente del último paquete UDP que le llega. Sin este aviso, recién
  // se enteraría cuando se apriete el primer botón físico.
  udp.beginPacket(IP_PC, PUERTO_UDP);
  udp.print("ESP32_ONLINE");
  udp.endPacket();

  //Botones de colores
  pinMode(boton_rojo, INPUT_PULLUP); //el pin va a ser un input; pullup: cuando no lo apreto manda 1, cuando lo apreto manda 0.
  pinMode(boton_verde, INPUT_PULLUP);
  pinMode(boton_azul, INPUT_PULLUP);
  pinMode(boton_amarillo, INPUT_PULLUP);
  
  //Boton del joystick
  pinMode(stick_Boton, INPUT);

  //Encoder
  pinMode(Rot_CLK, INPUT_PULLUP);
  pinMode(Rot_DT, INPUT_PULLUP);
  pinMode(Rot_SW, INPUT_PULLUP); //Igual que los botones del LED: no apreto--> 1. Apreto--> 0.

  // El conteo de pasos se hace en isrEncoder() (interrupción), no por
  // polling acá: ver el comentario junto a la declaración de contadorEncoder.
  attachInterrupt(digitalPinToInterrupt(Rot_CLK), isrEncoder, CHANGE);

  //Acelerómetro
   Wire.begin(23, 22); // SDA = GPIO23, SCL = GPIO22

  // Intenta detectar el acelerómetro en la dirección I2C default (0x53,
  // pin ALT ADDRESS en bajo). Si no responde ahí, reintenta en 0x1D: varios
  // clones del ADXL345 (modulos GY-291) traen el pin ALT ADDRESS en alto y
  // quedan en esa dirección en vez de la default.
  // Mientras se prueban los componentes de a uno, no conviene trabar todo
  // el programa por esto: solo avisa y sigue. La lectura en loop() se salta
  // sola si acelerometroOK queda en false (ver mas abajo).
  uint8_t direccionAcelerometro = ADXL345_DEFAULT_ADDRESS; // 0x53
  acelerometroOK = acelerometro.begin(direccionAcelerometro);
  if (!acelerometroOK) {
    direccionAcelerometro = 0x1D;
    acelerometroOK = acelerometro.begin(direccionAcelerometro);
  }

  if (!acelerometroOK) {
    Serial.println("ERROR: No se detecta el ADXL345 (probado en 0x53 y 0x1D)");
    Serial.println("Revisar conexiones: VCC, GND, SDA y SCL (sigue sin el acelerometro)");
  } else {
    Serial.print("ADXL345 detectado en direccion I2C 0x");
    Serial.println(direccionAcelerometro, HEX);

    // Configura el rango de medición del acelerómetro.
    // 2G significa que mide aceleraciones entre -2g y +2g.
    // Para inclinaciones y movimientos suaves está bien.
    acelerometro.setRange(ADXL345_RANGE_2_G);

    // Algunos módulos ADXL345 (sobre todo clones) detectan bien por I2C
    // (por eso begin() devuelve true) pero quedan en modo standby, sin
    // arrancar a medir de verdad: ahí todos los ejes quedan clavados en 0.
    // Forzamos a mano el bit "Measure" del registro POWER_CTL (0x2D), por
    // si la escritura que hace la librería internamente no llegó a tomar.
    Wire.beginTransmission(direccionAcelerometro);
    Wire.write(0x2D);
    Wire.write(0x08);
    Wire.endTransmission();
  }

  //LEDs
    // Configuramos los LEDs como salidas
  pinMode(LED_AMARILLO, OUTPUT);
  pinMode(LED_ROJO, OUTPUT);
  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_AZUL, OUTPUT);

  // Arrancan todos apagados
  digitalWrite(LED_AMARILLO, LOW);
  digitalWrite(LED_ROJO, LOW);
  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_AZUL, LOW);

  //OLED
  // Inicializa el monitor serie
    Serial.begin(115200);

    // Inicializa la OLED
    display.begin();

    // Pantalla del menú, la misma que se vuelve a mostrar cada vez que el
    // frontend manda "OLED_MENU" (ver mostrarMenuOLED).
    mostrarMenuOLED();

    // Mantiene esta pantalla durante 2 segundos
    delay(2000);

  Serial.println("PRUEBA DE HARDWARE INICIADA");
}

//Void loop: loop que se repite constantemente. Lee y ejecuta el código
void loop() {

//el arduino lee constantemente que señales están llegand0/emitiendo los componentes

  //Comandos UDP que llegan desde el backend (ej: prender un LED puntual
  //para un estímulo del test N-Back). Usa el mismo socket `udp` con el que
  //se manda BOTON_X, así no hace falta un puerto ni una conexión aparte.
  int tamanoPaqueteUDP = udp.parsePacket();
  if (tamanoPaqueteUDP > 0) {
    // 160 bytes: los comandos cortos de LED entran de sobra, y también los
    // de resultado de la OLED ("OLED_RESULTADO:Test;linea2;linea3..."), que
    // con el buffer chico de antes (32) quedaban cortados a la mitad.
    char bufferUDP[160];
    int leidos = udp.read(bufferUDP, sizeof(bufferUDP) - 1);
    bufferUDP[leidos > 0 ? leidos : 0] = '\0';
    String comandoRecibido = String(bufferUDP);
    comandoRecibido.trim();
    Serial.print("Comando UDP recibido: ");
    Serial.println(comandoRecibido);
    procesarComandoLED(comandoRecibido);
  }

  //Lectura de los botones: flancoDescendente() dispara una sola vez por
  //apretada real (ver su comentario mas arriba), sin bloquear loop() con
  //delay() como antes.
  if (flancoDescendente(boton_rojo, estadoAnteriorBotonRojo, ultimoEventoBotonRojo)) {
    Serial.println("BOTON ROJO APRETADO");
    udp.beginPacket(IP_PC, PUERTO_UDP);
    udp.print("BOTON_ROJO");
    udp.endPacket();
  }
  if (flancoDescendente(boton_verde, estadoAnteriorBotonVerde, ultimoEventoBotonVerde)) {
    Serial.println("BOTON VERDE APRETADO");
    udp.beginPacket(IP_PC, PUERTO_UDP);
    udp.print("BOTON_VERDE");
    udp.endPacket();
  }
  if (flancoDescendente(boton_azul, estadoAnteriorBotonAzul, ultimoEventoBotonAzul)) {
    Serial.println("BOTON AZUL APRETADO");   // Esto aparece en el Monitor Serial
    udp.beginPacket(IP_PC, PUERTO_UDP);      // Manda el UDP primero, sin esperar a la OLED
    udp.print("BOTON_AZUL");
    udp.endPacket();
    mostrarMensajeOLED("BOTON AZUL");        // Esto aparece en la OLED (mas lento, va despues)
  }
  if (flancoDescendente(boton_amarillo, estadoAnteriorBotonAmarillo, ultimoEventoBotonAmarillo)) {
    Serial.println("BOTON AMARILLO APRETADO");
    udp.beginPacket(IP_PC, PUERTO_UDP);
    udp.print("BOTON_AMARILLO");
    udp.endPacket();
  }
  if (flancoDescendente(stick_Boton, estadoAnteriorBotonStick, ultimoEventoBotonStick)) {
    Serial.println("BOTON STICK APRETADO");
    udp.beginPacket(IP_PC, PUERTO_UDP);
    udp.print("BOTON_STICK");
    udp.endPacket();
  }

  //Lectura del joystick (streaming continuo de posicion, para el test de Tracking)
  // analogRead lee el voltaje del eje X/Y del joystick y lo convierte en un valor entre 0 y 4095 en el ESP32.
  int lecturaX = analogRead(stick_X);
  int lecturaY = analogRead(stick_Y);

  // Solo manda el paquete UDP cada intervaloJoystickMs (no en cada vuelta de
  // loop): mandar por WiFi en cada iteracion mantiene al radio transmitiendo
  // casi sin pausa, que es el consumo de corriente mas alto de la placa.
  // Espaciar los envios le da tiempo a la fuente para recuperarse entre
  // picos, sin perder fluidez para el test de Tracking.
  if (millis() - ultimoTiempoJoystick >= intervaloJoystickMs) {
    ultimoTiempoJoystick = millis();

    udp.beginPacket(IP_PC, PUERTO_UDP);
    udp.print("JOYSTICK,");
    udp.print(lecturaX);
    udp.print(",");
    udp.print(lecturaY);
    udp.endPacket();

    Serial.print("JOYSTICK -> X: ");
    Serial.print(lecturaX);
    Serial.print(" | Y: ");
    Serial.println(lecturaY);
  }

  //Lectura del Encoder: el conteo en si ya lo hizo isrEncoder() por
  //interrupcion (ver mas arriba); aca solo "drenamos" los pasos
  //pendientes, uno por uno, para mandarlos por UDP/Serial. Drenarlos de
  //a uno (no de una sola vez como un solo evento) es importante: si
  //giraste rapido y se acumularon varios pasos entre una vuelta de loop()
  //y la siguiente, cada paso manda su propio evento, para no perder
  //pasos en la navegacion del menu (proximo paso de este trabajo).
  while (contadorEncoderPendiente != 0) {
    if (contadorEncoderPendiente > 0) {
      contadorEncoderPendiente--;
      Serial.print("ENCODER GIRO A LA DERECHA | Contador = ");
      Serial.println(contadorEncoder);
      udp.beginPacket(IP_PC, PUERTO_UDP);
      udp.print("ENCODER_DERECHA");
      udp.endPacket();
    } else {
      contadorEncoderPendiente++;
      Serial.print("ENCODER GIRO A LA IZQUIERDA | Contador = ");
      Serial.println(contadorEncoder);
      udp.beginPacket(IP_PC, PUERTO_UDP);
      udp.print("ENCODER_IZQUIERDA");
      udp.endPacket();
    }
  }

  if (flancoDescendente(Rot_SW, estadoAnteriorBotonEncoder, ultimoEventoBotonEncoder)) {
    Serial.println("BOTON DEL ENCODER APRETADO");
    udp.beginPacket(IP_PC, PUERTO_UDP);
    udp.print("BOTON_ENCODER");
    udp.endPacket();
  }


  //Acelerometro (se salta toda esta lectura si no se detecto en setup())
  sensors_event_t evento;

  if (acelerometroOK && millis() - ultimoTiempoAcelerometro >= intervaloAcelerometro) {
    ultimoTiempoAcelerometro = millis();

    // Leemos los datos del acelerómetro
    acelerometro.getEvent(&evento);

    float ax = evento.acceleration.x;
    float ay = evento.acceleration.y;
    float az = evento.acceleration.z;

    udp.beginPacket(IP_PC, PUERTO_UDP);
    udp.print("ACEL,");
    udp.print(ax);
    udp.print(",");
    udp.print(ay);
    udp.print(",");
    udp.print(az);
    udp.endPacket();

    Serial.print("ACELEROMETRO -> X: ");
    Serial.print(ax);
    Serial.print(" | Y: ");
    Serial.print(ay);
    Serial.print(" | Z: ");
    Serial.println(az);
  }

  // Pausa chica al final de cada vuelta: ahora que el envio del joystick ya
  // no tiene su propio delay(100) (ver mas arriba), sin esto el loop() puede
  // quedar girando sin pausa, y eso puede gatillar el watchdog del ESP32.
  delay(5);
}

