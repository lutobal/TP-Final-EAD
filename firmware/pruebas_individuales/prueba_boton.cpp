#include <Arduino.h>     // Funciones básicas de Arduino
#include <Wire.h>        // Comunicación I2C
#include <U8g2lib.h>     // Librería para la pantalla OLED

// ======================================================
// CREACIÓN DEL OBJETO OLED
// ======================================================
//
// SH1106      -> controlador de la pantalla
// 128X64      -> resolución
// HW_I2C      -> usa I2C por hardware del ESP32
//
// Pines utilizados:
// SCL -> GPIO 13
// SDA -> GPIO 19
//
U8G2_SH1106_128X64_NONAME_F_HW_I2C display(
    U8G2_R0,          // orientación normal de la pantalla
    U8X8_PIN_NONE,    // no usamos pin de reset
    13,               // SCL
    19                // SDA
);

// ======================================================
// FUNCIÓN PARA MOSTRAR INFORMACIÓN EN LA OLED
// ======================================================
//
// test      -> nombre del test
// aciertos  -> cantidad de aciertos
// errores   -> cantidad de errores
//
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

// ======================================================
// SETUP
// Se ejecuta una sola vez al encender el ESP32
// ======================================================
void setup()
{
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
}

// ======================================================
// LOOP
// Se ejecuta continuamente
// ======================================================
void loop()
{
    // Simula resultados del test Stroop
    mostrarEstado("Stroop", 5, 2);
    delay(2000);

    // Simula resultados del test Faro
    mostrarEstado("Faro", 8, 1);
    delay(2000);

    // Simula resultados del test N-Back
    mostrarEstado("N-Back", 12, 3);
    delay(2000);

    // Simula resultados del Laberinto
    mostrarEstado("Laberinto", 4, 0);
    delay(2000);
}