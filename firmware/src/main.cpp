#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL345_U.h>
#include <U8g2lib.h>     // Librería para la pantalla OLED
#include <WiFi.h>        // Conexión WiFi del ESP32
#include <WiFiUdp.h>      // Envío de paquetes UDP (botones -> PC)

// ======================================================
// WIFI Y UDP: paso 1 de la integración con la PC.
// Por ahora solo el botón rojo manda un evento por UDP.
// ======================================================
const char* WIFI_SSID = "casa tobal";         // <-- completar con el nombre del hotspot
const char* WIFI_PASSWORD = "Tobal35!"; // <-- completar con la contraseña del hotspot

IPAddress IP_PC(192, 168, 86, 153); // IP de la PC dentro de la red WiFi actual
const unsigned int PUERTO_UDP = 4210; // ESP32 -> PC (eventos de botones)

WiFiUDP udp;


//Seteamos los pines a los que asociamos cada componente
int boton_rojo = 5; 
int boton_verde = 14;
int boton_azul = 19;
int boton_amarillo = 17;

// int stick_X = 35;
// int stick_Y = 34;
// int stick_Boton = 23;

//Pines del encoder
int Rot_CLK = 26; //CLK--> detecta que el encoder se movió, que hubo un paso de giro.
int Rot_DT = 27; // DT es la referencia; comparando CLK con DT, se interpreta la dirección del giro (derecha o izquierda)
int Rot_SW = 32; //Botón del encoder: cuando apretas hacia abajo, se comporta como un botón común.

//Lógica del encoder: cuando giras la perilla, el pin va cambiando entre high y low, se detectan los cambios y se interpreta: "Hubo un paso de giro"
//giro a la derecha --> +1 paso. Giro a la izquierda--> -1 paso.
int estadoAnteriorCLK; // Guarda el estado anterior de CLK para detectar cuándo cambia
int contadorEncoder = 0; // Contador que empieza en cero y cuenta cuántos pasos giró el encoder

// Para debounce del botón --> EXPLICAR DESPUES??
unsigned long ultimoTiempoBoton = 0;
const int DEBOUNCE_MS = 200;

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
int LED_VERDE = 18;
int LED_AZUL = 4;

//OLED
U8G2_SH1106_128X64_NONAME_F_SW_I2C display(
    U8G2_R0,
    13,              // SCL
    25,              // SDA
    U8X8_PIN_NONE    // RESET
);


void mostrarEstado(String test, int aciertos, int errores)
{
    // Borra todo lo que había en el buffer gráfico
    display.clearBuffer();

    // Selecciona fuente para el título
    display.setFont(u8g2_font_ncenB08_tr);

    // Escribe el nombre del proyecto
    display.drawStr(0, 12, "NeuroRehab");

    // Cambia a una fuente más chica
    display.setFont(u8g2_font_6x10_tr);

    // --------------------------------------------------
    // Nombre del test
    // --------------------------------------------------
    display.setCursor(0, 30);
    display.print("Test: ");
    display.print(test);

    // --------------------------------------------------
    // Cantidad de aciertos
    // --------------------------------------------------
    display.setCursor(0, 45);
    display.print("Aciertos: ");
    display.print(aciertos);

    // --------------------------------------------------
    // Cantidad de errores
    // --------------------------------------------------
    display.setCursor(0, 60);
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
    display.drawStr(0, 12, "NeuroRehab");

    display.setFont(u8g2_font_6x10_tr);
    display.setCursor(0, 35);
    display.print(mensaje);

    display.sendBuffer();
}

//Prende/apaga los LEDs segun el comando recibido. Entiende los comandos
//cortos que se escriben a mano por el Monitor Serial ("r","v","az","am","off")
//y los comandos largos que manda el backend por UDP ("LED_ROJO", etc.).
void procesarComandoLED(String comando) {
  if (comando == "r" || comando == "LED_ROJO") {
    digitalWrite(LED_ROJO, HIGH);
    Serial.println("LED ROJO ENCENDIDO");
  }

  else if (comando == "v" || comando == "LED_VERDE") {
    digitalWrite(LED_VERDE, HIGH);
    Serial.println("LED VERDE ENCENDIDO");
  }

  else if (comando == "az" || comando == "LED_AZUL") {
    digitalWrite(LED_AZUL, HIGH);
    Serial.println("LED AZUL ENCENDIDO");
  }

  else if (comando == "am" || comando == "LED_AMARILLO") {
    digitalWrite(LED_AMARILLO, HIGH);
    Serial.println("LED AMARILLO ENCENDIDO");
  }

  else if (comando == "off" || comando == "LED_OFF") {
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
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Conectando a WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("WiFi conectado. IP del ESP32: ");
  Serial.println(WiFi.localIP());

  // Apaga el modo de ahorro de energia del WiFi: con el ahorro de energia
  // activado (que es el default), el ESP32 "duerme" el radio a ratos y
  // puede perderse paquetes UDP entrantes que lleguen justo en ese momento
  // (no afecta lo que el ESP32 manda, solo lo que recibe).
  WiFi.setSleep(false);

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
  // pinMode(stick_Boton, INPUT_PULLUP);

  //Encoer
  pinMode(Rot_CLK, INPUT_PULLUP);
  pinMode(Rot_DT, INPUT_PULLUP);
  pinMode(Rot_SW, INPUT_PULLUP); //Igual que los botones del LED: no apreto--> 1. Apreto--> 0.

  estadoAnteriorCLK = digitalRead(Rot_CLK); //Lee como está el Rot_CLK en ese momento y lo guarda en la variable astadoAnteriorCLK

  //Acelerómetro
   Wire.begin(21, 22);

  // Intenta detectar el acelerómetro.
  // Si acelerometro.begin() devuelve false, significa que no lo encontró.
  // Mientras se prueban los componentes de a uno, no conviene trabar todo
  // el programa por esto: solo avisa y sigue. La lectura en loop() se salta
  // sola si acelerometroOK queda en false (ver mas abajo).
  acelerometroOK = acelerometro.begin();
  if (!acelerometroOK) {
    Serial.println("ERROR: No se detecta el ADXL345");
    Serial.println("Revisar conexiones: VCC, GND, SDA y SCL (sigue sin el acelerometro)");
  } else {
    // Configura el rango de medición del acelerómetro.
    // 2G significa que mide aceleraciones entre -2g y +2g.
    // Para inclinaciones y movimientos suaves está bien.
    acelerometro.setRange(ADXL345_RANGE_2_G);
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

  //IMPORTANTE PARA CONECTAR DESPUES CON EL CÓDIGO BASE
  //"r  -> prender LED rojo
  //"v  -> prender LED verde
  //az -> prender LED azul
  //am -> prender LED amarillo"
  //off -> apagar todos"


  //OLED
  // Inicializa el monitor serie
    Serial.begin(115200);

    // Inicializa la OLED
    display.begin();

    // Borra el buffer gráfico
    display.clearBuffer();

    // Fuente grande para el mensaje principal
    display.setFont(u8g2_font_ncenB14_tr);

    // Escribe "HOLA"
    display.drawStr(0, 25, "HOLA");

    // Cambia a fuente más pequeña
    display.setFont(u8g2_font_6x10_tr);

    // Mensaje secundario
    display.drawStr(0, 50, "OLED funcionando");

    // Muestra el contenido en pantalla
    display.sendBuffer();

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
    char bufferUDP[32];
    int leidos = udp.read(bufferUDP, sizeof(bufferUDP) - 1);
    bufferUDP[leidos > 0 ? leidos : 0] = '\0';
    String comandoRecibido = String(bufferUDP);
    comandoRecibido.trim();
    Serial.print("Comando UDP recibido: ");
    Serial.println(comandoRecibido);
    procesarComandoLED(comandoRecibido);
  }

  //Lectura del los botones.
  //Se guarda en cada variable BOTON_X el estado digital de cada botón (0: apagado, 1:encendido)
  int BOTON_R = digitalRead(boton_rojo); 
  int BOTON_AM = digitalRead(boton_amarillo);
  int BOTON_AZ = digitalRead(boton_azul);
  int BOTON_V = digitalRead(boton_verde);

  //Si apretamos el botón, manda un cero e imprime botón apretado
  if (BOTON_R == LOW) {
    Serial.println("BOTON ROJO APRETADO");
    udp.beginPacket(IP_PC, PUERTO_UDP);
    udp.print("BOTON_ROJO");
    udp.endPacket();
    delay(200);
  }
  if (BOTON_V == LOW) {
    Serial.println("BOTON VERDE APRETADO");
    udp.beginPacket(IP_PC, PUERTO_UDP);
    udp.print("BOTON_VERDE");
    udp.endPacket();
    delay(200);
  }
  if (BOTON_AZ == LOW) {
    Serial.println("BOTON AZUL APRETADO");   // Esto aparece en el Monitor Serial
    udp.beginPacket(IP_PC, PUERTO_UDP);      // Manda el UDP primero, sin esperar a la OLED
    udp.print("BOTON_AZUL");
    udp.endPacket();
    mostrarMensajeOLED("BOTON AZUL");        // Esto aparece en la OLED (mas lento, va despues)
    delay(200);
  }
  if (BOTON_AM == LOW) {
    Serial.println("BOTON AMARILLO APRETADO");
    udp.beginPacket(IP_PC, PUERTO_UDP);
    udp.print("BOTON_AMARILLO");
    udp.endPacket();
    delay(200);
  }
  // if (digitalRead(stick_Boton) == LOW) {
  //   Serial.println("BOTON STICK XY APRETADO");
  //   delay(200);
  // }

  //Lectura del joystick
  // analogRead lee el voltaje del eje X/Y del joystick y lo convierte en un valor entre 0 y 4095 en el ESP32.
  // int lecturaX = analogRead(stick_X);
  // int lecturaY = analogRead(stick_Y);

  delay(100); //pausa de 100 ms


  // Serial.print("X = ");
  // Serial.println(lecturaX);

  // Serial.print("Y = ");
  // Serial.println(lecturaY);

  //Si es eje x es mayor a 2800, entonces se interpreta que el joystick se movió hacia la derecha
  // if (lecturaX > 3000){
  //   Serial.println("STICK X DERECHA");
  //   delay(200);
  // }
  
  //Si es eje x es mayor a 2800, entonces se interpreta que el joystick se movió hacia la derecha
  // if (lecturaX < 1500){
  //   Serial.println("STICK X IZQUIERDA");
  //   delay(200);
  // }

  // //Si el valor del eje Y es menor a 1500, interpreta que el joystick fue hacia abajo.
  // if (lecturaY < 1500){
  //   Serial.println("STICK Y ARRIBA");
  //   delay(200);
  // }

  //Si el valor del eje Y es mayor a 1500, interpreta que el joystick fue hacia abajo.
  // if (lecturaY > 3000){
  //   Serial.println("STICK Y ABAJO");
  //   delay(200);
  // }

  //Lectura del Encoder
   int estadoActualCLK = digitalRead(Rot_CLK);

  if (estadoActualCLK != estadoAnteriorCLK) {
    estadoActualCLK = digitalRead(Rot_CLK);
    
    int estadoDT = digitalRead(Rot_DT);

    if (estadoDT != estadoActualCLK) {
      contadorEncoder--;
      Serial.print("ENCODER GIRO A LA IZQUIERDA | Contador = ");
      Serial.println(contadorEncoder);
    } else {
      contadorEncoder++;
      Serial.print("ENCODER GIRO A LA DERECHA | Contador = ");
      Serial.println(contadorEncoder);
    }
  }

  estadoAnteriorCLK = estadoActualCLK;

  if (digitalRead(Rot_SW) == LOW) {
    Serial.println("BOTON DEL ENCODER APRETADO");
    delay(200);
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

    // Serial.print("X = ");
    // Serial.print(ax);
    // Serial.print(" m/s2 | Y = ");
    // Serial.print(ay);
    // Serial.print(" m/s2 | Z = ");
    // Serial.print(az);
    // Serial.println(" m/s2");

    // Interpretación simple de inclinación
    if (ax > 3) {
      Serial.println("INCLINACION HACIA LA DERECHA");
    }

    if (ax < -3) {
      Serial.println("INCLINACION HACIA LA IZQUIERDA");
    }

    if (ay > 3) {
      Serial.println("INCLINACION HACIA ADELANTE");
    }

    if (ay < -3) {
      Serial.println("INCLINACION HACIA ATRAS");
    }

  

  }

  //LEDS por Serial (comandos cortos, para probar a mano desde el Monitor Serial)
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    procesarComandoLED(comando);
  }

}

