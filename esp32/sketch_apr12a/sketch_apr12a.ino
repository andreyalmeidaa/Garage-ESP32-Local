#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>

const char* ssid = "iPhone de Andrey";
const char* password = "12345678";

WebServer server(80);
Servo servoMotor;

const int SERVO_PIN = 13;
const int LED_VERDE = 25;
const int LED_VERMELHO = 26;

const int ANGULO_FECHADO = 35;
const int ANGULO_ABERTO = 116;

// Controle do movimento
int posicaoAtual = ANGULO_FECHADO;
int posicaoAlvo = ANGULO_FECHADO;
const int PASSO_SERVO = 2;
const unsigned long INTERVALO_SERVO = 15;
unsigned long ultimoMovimentoServo = 0;

String statusPortao = "Fechado";
unsigned long ultimaTentativaWiFi = 0;

// Controle do pisca do LED verde
unsigned long ultimoPiscaLed = 0;
const unsigned long INTERVALO_PISCA_LED = 500;
bool estadoPiscaVerde = false;

void conectarWiFi() {
  Serial.println("Conectando ao Wi-Fi...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  int tentativas = 0;
  while (WiFi.status() != WL_CONNECTED && tentativas < 30) {
    delay(500);
    Serial.print(".");
    tentativas++;
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("Wi-Fi conectado");
    Serial.print("IP do ESP32: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Falha ao conectar no Wi-Fi");
  }
}

void garantirWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  unsigned long agora = millis();
  if (agora - ultimaTentativaWiFi >= 5000) {
    ultimaTentativaWiFi = agora;
    Serial.println("Wi-Fi caiu. Tentando reconectar...");
    WiFi.disconnect();
    WiFi.begin(ssid, password);
  }
}

void atualizarLeds() {
  unsigned long agora = millis();

  if (statusPortao == "Aberto") {
    if (agora - ultimoPiscaLed >= INTERVALO_PISCA_LED) {
      ultimoPiscaLed = agora;
      estadoPiscaVerde = !estadoPiscaVerde;
      digitalWrite(LED_VERDE, estadoPiscaVerde ? HIGH : LOW);
    }
    digitalWrite(LED_VERMELHO, LOW);
  }
  else if (statusPortao == "Fechado") {
    digitalWrite(LED_VERDE, LOW);
    digitalWrite(LED_VERMELHO, HIGH);
  }
  else if (statusPortao == "Parado") {
    digitalWrite(LED_VERDE, HIGH);
    digitalWrite(LED_VERMELHO, HIGH);
  }
  else {
    // Abrindo ou Fechando
    digitalWrite(LED_VERDE, LOW);
    digitalWrite(LED_VERMELHO, LOW);
  }
}

void atualizarMovimentoServo() {
  unsigned long agora = millis();

  if (agora - ultimoMovimentoServo < INTERVALO_SERVO) {
    return;
  }

  ultimoMovimentoServo = agora;

  if (posicaoAtual < posicaoAlvo) {
    posicaoAtual += PASSO_SERVO;
    if (posicaoAtual > posicaoAlvo) posicaoAtual = posicaoAlvo;
    servoMotor.write(posicaoAtual);
  } 
  else if (posicaoAtual > posicaoAlvo) {
    posicaoAtual -= PASSO_SERVO;
    if (posicaoAtual < posicaoAlvo) posicaoAtual = posicaoAlvo;
    servoMotor.write(posicaoAtual);
  }

  // Atualiza o status quando chega no destino
  if (posicaoAtual == posicaoAlvo) {
    if (posicaoAlvo == ANGULO_ABERTO) {
      statusPortao = "Aberto";
    } else if (posicaoAlvo == ANGULO_FECHADO) {
      statusPortao = "Fechado";
    }
  }
}

void abrirPortao() {
  Serial.println("Comando recebido: ABRIR");
  posicaoAlvo = ANGULO_ABERTO;
  statusPortao = "Abrindo";
  server.send(200, "text/plain", "OK:ABRINDO");
}

void fecharPortao() {
  Serial.println("Comando recebido: FECHAR");
  posicaoAlvo = ANGULO_FECHADO;
  statusPortao = "Fechando";
  server.send(200, "text/plain", "OK:FECHANDO");
}

void pararPortao() {
  Serial.println("Comando recebido: PARAR");
  posicaoAlvo = posicaoAtual;
  statusPortao = "Parado";
  server.send(200, "text/plain", "OK:PARADO");
}

void statusHandler() {
  server.send(200, "text/plain", statusPortao);
}

void raizHandler() {
  String resposta = "";
  resposta += "ESP32 online\n";
  resposta += "Status: " + statusPortao + "\n";
  resposta += "Posicao atual: " + String(posicaoAtual) + "\n";
  resposta += "Posicao alvo: " + String(posicaoAlvo) + "\n";
  resposta += "IP: " + WiFi.localIP().toString() + "\n";
  resposta += "Rotas: /abrir /fechar /parar /status\n";
  server.send(200, "text/plain", resposta);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_VERMELHO, OUTPUT);

  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_VERMELHO, HIGH); // começa fechado

  servoMotor.setPeriodHertz(50);
  servoMotor.attach(SERVO_PIN, 500, 2400);
  servoMotor.write(ANGULO_FECHADO);

  posicaoAtual = ANGULO_FECHADO;
  posicaoAlvo = ANGULO_FECHADO;

  conectarWiFi();

  server.on("/", HTTP_GET, raizHandler);
  server.on("/abrir", HTTP_GET, abrirPortao);
  server.on("/fechar", HTTP_GET, fecharPortao);
  server.on("/parar", HTTP_GET, pararPortao);
  server.on("/status", HTTP_GET, statusHandler);

  server.begin();
  Serial.println("Servidor HTTP iniciado");
}

void loop() {
  garantirWiFi();
  server.handleClient();
  atualizarMovimentoServo();
  atualizarLeds();
}