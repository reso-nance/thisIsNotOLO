/*Copyright 2019 Reso-nance Numérique <laurent@reso-nance.org>

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.
  
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
  MA 02110-1301, USA.


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
#include "RBDdimmerESP8266.h"

#define OTA_TIMEOUT 5 // time in seconds after which the device resume it's normal activity if no OTA firmware is comming 
#define DIMMER_PWM D1
#define DIMMER_ZC D2
#define MIN_FADING_STEP_DURATION 5 // minimum time in ms after which the fading can be updated
#define FADE_INTERRUPTS_ANOTHER false // if set to false, creating a new fade will be ignored if another fading is already in progress
#define SERIAL_DEBUG
#define NO_ROUTER
#define USE_BUILTIN_LED // if undef, will use RBDdimmer instead

static const float exponent = 2.0f; // used to produce exponential fades
const String MACaddress=WiFi.macAddress();
String hostname="light_"+MACaddress;
#ifdef NO_ROUTER
static char* SSID = "ZINC 2.4";
static char* PSK = "zincZN30!";
#else
static char* PSK = "malinette666";
static char* SSID = "malinette";
#endif
const int listenPort = 8000;
int targetPort = 9000;
#ifdef NO_ROUTER
IPAddress serverIP=IPAddress({10,0,120,255}); // communication with the Pi server, can be superseded by /whoIsThere message
#else
IPAddress serverIP=IPAddress({10,0,0,255}); // communication with the Pi server, can be superseded by /whoIsThere message
#endif
IPAddress IPfromLastMessageReceived; // will store, well the IP of the OSC sender
WiFiUDP udpserver;
char incomingPacket[255]; // UDP packet buffer
char incomingAddress[128]; // OSC address buffer
String OSCprefix; // will store /[hostname][MACaddress without semicolons
bool OTA_asked = false; // flag which become true for OTA_TIMEOUT seconds after receiving a /beginOTA message to suspend device activity while flashing
int lastValueUsed = 0;
#ifndef USE_BUILTIN_LED
dimmerLampESP8266 dimmer(DIMMER_PWM, DIMMER_ZC);
#endif

struct Fade{ 
  bool isActive;
  bool isInverted;
  unsigned int start; 
  unsigned int stop;
  unsigned int duration;
  unsigned int stepCount;
  unsigned int stepDuration;
  unsigned int stepIncrement;
  unsigned int currentStep;
  unsigned long nextStepTimer;
  unsigned long startedTimer;
};

Fade fade = {false, false, 0, 0, 0, 0, 0, 0, 0, 0}; // default inactive fade

#ifdef SERIAL_DEBUG
  #define debugPrint(x)  Serial.print (x)
  #define debugPrintln(x)  Serial.println (x)
#else
  #define debugPrint(x)
  #define debugPrintln(x)
#endif

void setup() {
  #ifndef USE_BUILTIN_LED
  dimmer.begin(NORMAL_MODE, ON);
  dimmer.setPower(0);
  #else
  pinMode(LED_BUILTIN, OUTPUT);
  analogWriteRange(100);
  digitalWrite(LED_BUILTIN, HIGH);
  #endif
  hostname.replace(":","");
  OSCprefix = "/"+hostname;
  char hostnameAsChar[hostname.length()+1];
  hostname.toCharArray(hostnameAsChar, hostname.length()+11001);
  #ifdef SERIAL_DEBUG
  Serial.begin(115200);
  #endif
  connectToWifi(hostnameAsChar, SSID, PSK);
  udpserver.begin(listenPort); // start listening to specified port
  debugPrint("\thostname : ");debugPrintln(hostname);
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
      const String OSCfadeAddressStr = OSCprefix + "/fade";
      const char* OSCfadeAddress = OSCfadeAddressStr.c_str();
      const String OSCOTAStr = OSCprefix + "/beginOTA";
      const char* OSCOTA = OSCOTAStr.c_str();
      
      if (msg->fullMatch("/whoIsThere")) {
        serverIP=IPfromLastMessageReceived;
        sendID();
        debugPrint("set server IP to ");debugPrintln(serverIP);
      } else if (msg->fullMatch(OSCLightAddress)&& msg->isInt(0)) { 
        int value = msg->getInt(0);
        value = constrain(value, 0, 100);
        setLight(value);
        sendACK();
        } else if (msg->fullMatch(OSCfadeAddress) && msg->isInt(0) && msg->isInt(1) && msg->isInt(2)) { 
        const int start = constrain(msg->getInt(0),0,100);
        const int stop = constrain(msg->getInt(1),0,100);
        const int duration = msg->getInt(2);
        startFade(start, stop, duration);
      } else if ( msg->fullMatch(OSCOTA) ) {
        debugPrintln("Asked to prepare for OTA flashing");
        OTA_asked = true;
      }
      delete msg;
    }
    ESP.wdtFeed(); // avoid triggering the ESP watchdog
    yield(); // same but different
    handleFade();
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

void sendFadeACK() {
  char hostnameAsChar[hostname.length()+1];
  hostname.toCharArray(hostnameAsChar, hostname.length()+1);
  OSCMessage* msg = new OSCMessage("/fadeACK");
  msg->add(hostnameAsChar); // Hostname
  msg->add((int) fade.start); //start value
  msg->add((int) fade.stop); // stop value
  msg->add((int) fade.duration); //duration in ms
  sendOscToServer(msg);
  debugPrintln("sent fade ACK");
  delete(msg);
}

unsigned int expMap(unsigned int value, unsigned int start, unsigned int stop){
  float num=0;
  float denum=0;
  if (start < stop) {
    num = pow(value, exponent) - pow(start, exponent);
    denum = pow(stop, exponent) - pow(start, exponent);
  }
  else {
    num = pow(value, exponent) - pow(stop, exponent);
    denum = pow(start, exponent) - pow(stop, exponent);
  }
  float result = num/denum;
  //unsigned int result = 100* (pow(value, exponent) - pow(start, exponent))/(pow(stop, exponent)-pow(start, exponent));
  return 100*result;
}

void setLight(int value) {
  debugPrint("set light to "); debugPrintln(value);
  #ifndef USE_BUILTIN_LED
  dimmer.setPower(value);
  #else
  analogWrite(LED_BUILTIN, 100-value); // BUILTIN_LED is sinked so 0 = bright and 100 = dark
  #endif
  lastValueUsed = value;
}

void startFade(unsigned int start, unsigned int stop, unsigned int duration){
  if (start == stop) return; // or it will divide by zero sooner or later
  if (!fade.isActive || FADE_INTERRUPTS_ANOTHER){ // if another fade is in progress, we'll either replace it or ignore this one
    fade.isInverted = (start>stop);
    fade.stepCount = (fade.isInverted) ? start-stop : stop-start;
    fade.stepDuration = duration/fade.stepCount;
    if (fade.stepDuration < MIN_FADING_STEP_DURATION){ // very short fades forces us to increment by more than one each time
      fade.stepDuration = MIN_FADING_STEP_DURATION; 
      fade.stepIncrement = MIN_FADING_STEP_DURATION / ((float) duration/fade.stepCount); // will never be exact, handled below
      fade.stepCount = fade.stepCount/fade.stepIncrement; // bigger increments = lower stepCount
      debugPrint("stepIncrement : "); debugPrintln(fade.stepIncrement);
      debugPrint("stepcount : "); debugPrintln(fade.stepCount);
    }
    else fade.stepIncrement = 1;
    if (fade.isInverted) setLight(stop);
    else setLight(start);
    fade.isActive = true;
    fade.startedTimer = millis();
    fade.nextStepTimer = fade.startedTimer+fade.stepDuration; // prepare for the handleFade function
    fade.currentStep = 0;
    fade.start = start;
    fade.stop = stop;
    fade.duration = duration;
    debugPrint("Beginning ");
    if(fade.isInverted) debugPrint("inverted");
    debugPrint(" fade from ");debugPrint(fade.start); debugPrint(" to "); debugPrint(fade.stop);
    debugPrint(" in "); debugPrint(duration); debugPrintln(" ms");
    debugPrint("\tstep count :");debugPrintln(fade.stepCount);
    debugPrint("\tstep duration : "); debugPrintln(fade.stepDuration);
    debugPrint("\tstep increment : "); debugPrintln(fade.stepIncrement);
    debugPrint("\tcurrent step :"); debugPrintln(fade.currentStep);
    debugPrint("\tcurrentValue : "); 
    if(fade.isInverted) debugPrintln(stop);
    else debugPrintln(start);
    sendFadeACK();
  }
}

void handleFade(){
  if(! fade.isActive) return;
  if (fade.currentStep == fade.stepCount +1){
    fade.isActive = false;
    debugPrintln("fading finished");
    return;
  }
  if (millis() >= fade.nextStepTimer){// time to update the light
    unsigned int currentValue = 0;
    if (fade.isInverted) currentValue = fade.start - fade.currentStep*fade.stepIncrement;
    else currentValue = fade.start + fade.currentStep*fade.stepIncrement;
    if (fade.stop - currentValue<fade.stepIncrement) currentValue = fade.stop; // we are very near the final value but we will overshoot at the next loop
    currentValue = expMap(currentValue, fade.start, fade.stop);// this will map the value exponentially
    setLight(currentValue);
    fade.currentStep++;
    fade.nextStepTimer = fade.startedTimer+fade.stepDuration*fade.currentStep ;
    debugPrint("\tcurrent step :"); debugPrintln(fade.currentStep);
    debugPrint("\tcurrentValue : "); debugPrintln(currentValue);
    debugPrint("\ttime elapsed : "); debugPrintln(millis()-fade.startedTimer);
  }
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
  while (WiFi.waitForConnectResult() != WL_CONNECTED) {
    debugPrintln("\tfailed to connect, retrying in 1s");
    delay(1000);
  }
    debugPrintln("\tconnected :");
    debugPrint("\tlocal IP :"); debugPrintln(WiFi.localIP());
    ArduinoOTA.setPort(8266); //default OTA port
    ArduinoOTA.setHostname(Hostname);// No authentication by default, can be set with : ArduinoOTA.setPassword((const char *)"passphrase");
    ArduinoOTA.begin();
    debugPrintln("\tlistening for OTA on port 8266");
}
