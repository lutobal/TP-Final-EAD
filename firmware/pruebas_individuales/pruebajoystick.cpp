#include <Arduino.h>

int boton_rojo = 15;
int boton_verde = 14;
int boton_azul = 17;
int boton_amarillo = 12;

//int stick_X = 13;
int stick_Y = 13;
int stick_Boton = 33;

int Rot_CLK = 3;
int Rot_DT = 2;
int Rot_SW = 1;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);

  pinMode(boton_rojo, INPUT_PULLUP);
  pinMode(boton_verde, INPUT_PULLUP);
  pinMode(boton_azul, INPUT_PULLUP);
  pinMode(boton_amarillo, INPUT_PULLUP);
  
  pinMode(stick_Boton, INPUT_PULLUP);
}

void loop() {
// tengo los botones en PULL-UP entonces cuando los precione me va a dar 0
// y cuando los suelte me va a dar 1

int BOTON_R = digitalRead(boton_rojo);
int BOTON_AM = digitalRead(boton_amarillo);
int BOTON_AZ = digitalRead(boton_azul);
int BOTON_V = digitalRead(boton_verde);

  if (BOTON_R == LOW) {
    Serial.println("BOTON ROJO APRETADO");
    delay(200); 
  }
  if (BOTON_V == LOW) {
    Serial.println("BOTON VERDE APRETADO");
    delay(200);
  }
  if (BOTON_AZ == LOW) {
    Serial.println("BOTON AZUL APRETADO");
    delay(200);
  }
  if (BOTON_AM == LOW) {
    Serial.println("BOTON AMARILLO APRETADO");
    delay(200);
  }
  if (digitalRead(stick_Boton) == LOW) {
    Serial.println("BOTON STICK XY APRETADO");
    delay(200);
  }

  // analogRead nos devuelve un valor entre 0 y 4095 según la posición.
  //int lecturaX = analogRead(stick_X);
  int lecturaY = analogRead(stick_Y);
  
  // Imprimo las coordenadas del Joystick para verificar los valores
  //Serial.print("JOYSTICK -> Eje X: ");
  //Serial.print(lecturaX);
  //Serial.print(" | Eje Y: ");
  //Serial.println(lecturaY);

  delay(100);

  //if (lecturaX < 1500){
  //  Serial.println("STICK X IZQUIERDA");
 //   delay(200);
 // }
  //if (lecturaX > 3000){
   // Serial.println("STICK X DERECHA");
  //  delay(200);
  //}
  if (lecturaY < 1000){
    Serial.println("STICK Y ARRIBA");
    delay(200);
  }
if (lecturaY > 1400){
    Serial.println("STICK Y ABAJO");
    delay(200);
  }
}