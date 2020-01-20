
/*--------------This code is for a Wemos D1 board equipped with a MCP3204 (12bits 8 channels ADC).
 * Every input has it's internal pull-up enabled, so a switch must be wired between the input and ground for example

          Wemos D1         INPUTpins
            5V -------------- vcc
            Gnd ------------- gnd
            D0 --15k pullup-- IN0
            D1 -------------- IN1
            D2 -------------- IN2
            D5 -------------- IN3
            D6 -------------- IN4
            D7 -------------- IN5
            D4 -------------- IN6

D0/GPIO16 does need an external pullup, even in INPUT_PULLUP mode. Otherwise the internal pullup is deactivated the first time the pin is pulled LOW
D8/GPIO15 must stay LOW for the ESP8266 to boot, so no external pullup possible there. The internal one doesn't seems to work either.
compiled with ESP8266 v2.4.1 and OSC 1.3.3
*/
#include "Arduino.h"
#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <OSCMessage.h>


#define OTA_TIMEOUT 5 // time in seconds after which the device resume it's normal activity if no OTA firmware is comming 
#define SERIAL_DEBUG

const int lightPin=D1;
const String MACaddress=WiFi.macAddress();
String hostname="light_"+MACaddress;
static char* PSK = "malinette666";
static char* SSID = "malinette";
const int listenPort = 8000;
int targetPort = 9000;
IPAddress serverIP=IPAddress({10,0,0,255}); // communication with the Pi server, can be superseded by /whoIsThere message
IPAddress IPfromLastMessageReceived; // will store, well the IP of the OSC sender
WiFiUDP udpserver;
char incomingPacket[255]; // UDP packet buffer
char incomingAddress[128]; // OSC address buffer
String OSCprefix; // will store /[hostname][MACaddress without semicolons
bool OTA_asked = false; // flag which become true for OTA_TIMEOUT seconds after receiving a /beginOTA message to suspend device activity while flashing
int lastValueUsed = 0;

#ifdef SERIAL_DEBUG
  #define debugPrint(x)  Serial.print (x)
  #define debugPrintln(x)  Serial.println (x)
#else
  #define debugPrint(x)
  #define debugPrintln(x)
#endif

void setup() {
  digitalWrite(lightPin, LOW);
  hostname.replace(":","");
  OSCprefix = "/"+hostname;
  char hostnameAsChar[hostname.length()+1];
  hostname.toCharArray(hostnameAsChar, hostname.length()+1);
  #ifdef SERIAL_DEBUG
  Serial.begin(115200);
  #endif
  connectToWifi(hostnameAsChar, SSID, PSK);
  udpserver.begin(listenPort); // start listening to specified port
  debugPrint("hostname : ");debugPrintln(hostname);
  sendID();
}

void loop() {
  char hostnameAsChar[hostname.length()+1];
  hostname.toCharArray(hostnameAsChar, hostname.length()+1);
  if (OTA_asked) { // when receiving a /beginOTA message, this loop will wait for OTA to begin instead of carrying on the main loop
    for (int i=0; i<OTA_TIMEOUT; i++) {
      ESP.wdtFeed();
      yield();
      ArduinoOTA.handle();
      delay(1000);
    }
    OTA_asked = false;
  }
  else {
     delay(2);// needed to be able to receive OSC messages
  
  // Read OSC messages sent to this adress (or broadcasted)
    OSCMessage* msg = getOscMessage();
    if (msg != NULL) {
      // preconstruct char* containing this device prefix (ex: /LDR_01:23:45:67:78:9A/something) to be matched to received adresses
      const String OSCLightAddressStr = OSCprefix + "/light";
      const char* OSCLightAddress = OSCLightAddressStr.c_str();
      const String OSCOTAStr = OSCprefix + "/beginOTA";
      const char* OSCOTA = OSCOTAStr.c_str();
      
      if (msg->fullMatch("/whoIsThere")) {
        serverIP=IPfromLastMessageReceived;
        sendID();
        debugPrint("set server IP to ");debugPrintln(serverIP);
      } else if (msg->fullMatch(OSCLightAddress)&& msg->isInt(0)) { 
        int value = msg->getInt(0);
        value = constrain(value, 0, 1023);
        setLight(value);
      } else if ( msg->fullMatch(OSCOTA) ) {
        debugPrintln("Asked to prepare for OTA flashing");
        OTA_asked = true;
      }
      delete msg;
    }
  
    ESP.wdtFeed(); // avoid triggering the ESP watchdog
    yield(); // same but different
  }
}

//---------------- Hardware-specific functions ------------------  

void sendACK() {
  char hostnameAsChar[hostname.length()+1];
  hostname.toCharArray(hostnameAsChar, hostname.length()+1);
  OSCMessage* msg = new OSCMessage("/ACK");
  msg->add(hostnameAsChar); // Hostname
  msg->add((int) lastValueUsed); //value
  sendOscToServer(msg);
  debugPrintln("sent ACK");
  delete(msg);
}

void setLight(int value) {
  analogWrite(lightPin, value);
  lastValueUsed = value;
  sendACK();
}

void sendID() {
  char hostnameAsChar[hostname.length()+1];
  hostname.toCharArray(hostnameAsChar, hostname.length()+1);
  OSCMessage* msg = new OSCMessage("/myID");
  msg->add(hostnameAsChar); // Hostname
  sendOscToServer(msg);
  debugPrintln("sent ID");
  delete(msg);
}

OSCMessage* getOscMessage(){
  int packetSize = udpserver.parsePacket();
  if (packetSize)
  {
    //Serial.printf("Received %d bytes from %s, port %d\n", packetSize, udpserver.remoteIP().toString().c_str(), udpserver.remotePort());
    int len = udpserver.read(incomingPacket, packetSize);
    if (len > 0)  {incomingPacket[len] = 0;}
    IPfromLastMessageReceived= udpserver.remoteIP();
    OSCMessage* msg = new OSCMessage();
    msg->fill((uint8_t*)incomingPacket, len);
    int size = msg->getAddress(incomingAddress);
    ESP.wdtFeed();
    yield();
    return msg;
  }
  return NULL;
}

void sendOscToServer(OSCMessage *msg){
  sendOsc(msg, serverIP, targetPort);
}

void sendOsc(OSCMessage *msg,IPAddress ip,int port ){
    udpserver.beginPacket(ip, port);
    msg->send(udpserver);
    udpserver.endPacket();
    ESP.wdtFeed();
    yield();
}

void connectToWifi(const char *Hostname, const char* ssid, const char* passphrase) {
  debugPrintln("\n\nConnecting to " + String(ssid) + "...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, passphrase);
  WiFi.hostname(Hostname);
  ESP.wdtFeed();
  yield();
  if ( WiFi.waitForConnectResult() == WL_CONNECTED ) {
    ArduinoOTA.setPort(8266); //default OTA port
    ArduinoOTA.setHostname(Hostname);// No authentication by default, can be set with : ArduinoOTA.setPassword((const char *)"passphrase");
    ArduinoOTA.begin();
  }
}
