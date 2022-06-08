// Simple Serial protocol to DMX

// Arduino Micro!
#include <Arduino.h>
#include <DmxSimple.h>
#include <EEPROM.h>

// Options
//#define DEBUG_MSG // Verbose change/received messages
#define LEDPIN 13
#define DMXPIN 10
#define SERIALBAUD 115200

#define MAXCHANNELS 256 // Numbered 0..255
byte dmxvalue[MAXCHANNELS];
byte dmxtarget[MAXCHANNELS];
byte dmxstep[MAXCHANNELS];

// Prototypes
void setdmxvalue(int chan, int val);
void flipled();

void setup() {
  Serial.begin( SERIALBAUD );
  Serial.println("Started");
  DmxSimple.usePin(DMXPIN);

  // If you don't do this, DmxSimple will set the maximum channel number to the
  // highest channel you DmxSimple.write() to.
  DmxSimple.maxChannel(255);
  Serial.print( MAXCHANNELS);
  Serial.println(" channels");

  // LED
  pinMode( LEDPIN, OUTPUT);

  // Clear data
  for (int i = 0; i < MAXCHANNELS; i++) {
    dmxvalue[i] = 0;
    dmxtarget[i] = 0;
    dmxstep[i] = 0;
  }

  // EEPROM - read and use it if the check value is a specific number
  int checkval = EEPROM.read(MAXCHANNELS);
  if (checkval == 31) {
    for (int i = 0; i < MAXCHANNELS; i++) {
      dmxvalue[i] = EEPROM.read(i);
      dmxtarget[i] = dmxvalue[i];
      if (dmxvalue[i] != 0) {
        Serial.print( "initial chan ");
        Serial.print( i);
        Serial.print( " = ");
        Serial.println( dmxvalue[i]);
      }
    }
  }

  // initialise DMX values
  for (int i = 0; i < MAXCHANNELS; i++) {
    DmxSimple.write( i, dmxvalue[i] );
  }
}

#define MAX_ARD_CMD 20
char inputCommand[ MAX_ARD_CMD];
int  inputLength = 0;
char outputCommand[ MAX_ARD_CMD];

// For 1 sec flash timer
unsigned long lasttickmillis = 0; 
bool state = false;

// For 100 ms light step timer
unsigned long lastscanmillis = 0; 

// For 1 minute EEPROM write timer
unsigned long lasteepromwrite = 0;

void flipled() {
  state = !state; // LED Flip
  digitalWrite( LEDPIN, state);
}

void loop() {
  unsigned long millisnow = millis();
  // One second flash
  if (millisnow - lasttickmillis > 1000) {
    lasttickmillis = millisnow;
    flipled();
    Serial.println(".");
  }

  // One minute eeprom
  if (millisnow - lasteepromwrite > 60000) {
    lasteepromwrite = millisnow;
  
    EEPROM.update(MAXCHANNELS, 31);
    for (int i = 0; i < MAXCHANNELS; i++) {
      EEPROM.update(i, dmxtarget[i]);
    }
    Serial.println("eeprom");
  }

  // 100mS light change interval
  if (millisnow - lastscanmillis > 100) {
    // Read data looking for changes required
    for (int i = 0; i < MAXCHANNELS; i++) {
      if (dmxvalue[i] != dmxtarget[i]) {
        // The step value is used to smoothly change from value to target
        // The value is the number of 100 milliseconds periods the change is spread over
        // Each time we reduce the number of milliseconds remaining.
        if (dmxstep[i] == 0) {
          // Last step
          setdmxvalue(i, dmxtarget[i]);
        } else {
          // How many 100ms steps elapsed
          int stepselapsed = (millisnow - lastscanmillis) / 100;

          // work out value. If the difference (times steps elapsed) is smaller than the steps remaining
          // then the increment becomes zero. We keep on reducing steps remaining until it becomes 1
          // so the change remains smooth. 
          int newvalue = dmxvalue[i] + ( (dmxtarget[i] - dmxvalue[i])  * stepselapsed / dmxstep[i]);
          if (newvalue != dmxvalue[i]) {
            setdmxvalue(i, newvalue); 
          }

          // Subtract from time remaining, would usually be 1 but could be greater.
          // Ensure we don't roll around
          if (dmxstep[i] < stepselapsed) {
            dmxstep[i] = 0;
          } else {
            dmxstep[i] -= stepselapsed;
          }
        }
      }
    }
    lastscanmillis = millisnow;
  }

  // ******************************** Serial Handling **************************************
  // We receive command from the PC
  // We send back: A to ack
  // get serial data and buffer it up
  while (Serial.available() ) {
    // Characters available
    inputCommand[ inputLength] = Serial.read();
    // Control chars will also reset message
    if ( inputCommand[ inputLength] > 32 ) {
      inputLength++;
      inputCommand[ inputLength] = 0;
    } else {
      inputLength = 0;
      inputCommand[ inputLength] = 0;
    }
    // If too many chars, reject all
    if (inputLength > MAX_ARD_CMD - 1) {
      inputLength = 0;
      inputCommand[ inputLength] = 0;
      Serial.println( "com overflow.");
    }
    // End char received
    if (inputCommand[ inputLength-1] == 'E') {
      flipled();
#ifdef DEBUG_MSG
      Serial.print( "received: ");
      Serial.println( inputCommand);
#endif
      // Got a command - deal with it
      // SET
      // ScccVxxxE S channel V value E
      // 012345678
      if ( inputCommand[0] == 'S' &&
           inputCommand[4] == 'V' &&
           inputCommand[8] == 'E'   ) {
        int chan = 
            (( inputCommand[1] - '0') * 100) +
            (( inputCommand[2] - '0') * 10 ) +
            (( inputCommand[3] - '0')      );
        int val = 
            (( inputCommand[5] - '0') * 100) +
            (( inputCommand[6] - '0') * 10 ) +
            (( inputCommand[7] - '0')      );
        Serial.print( "set ");
        dmxtarget[chan] = val;
        dmxstep[chan] = 1;
      }
      // FADE channel c to value x over 100s periods n 
      // FcccVxxxPnnnE F channel V value P period E, e.g. F003V255P252E
      // 0123456789012
      if ( inputCommand[0] == 'F' &&
           inputCommand[4] == 'V' &&
           inputCommand[8] == 'P' &&
           inputCommand[12] == 'E'   ) {
        int chan = 
            (( inputCommand[1] - '0') * 100) +
            (( inputCommand[2] - '0') * 10 ) +
            (( inputCommand[3] - '0')      );
        int val = 
            (( inputCommand[5] - '0') * 100) +
            (( inputCommand[6] - '0') * 10 ) +
            (( inputCommand[7] - '0')      );
        int per = 
            (( inputCommand[9] - '0') * 100) +
            (( inputCommand[10]- '0') * 10 ) +
            (( inputCommand[11]- '0')      );
        Serial.print( "fade ");
        Serial.print( chan);
        Serial.print( " to ");
        Serial.print( val);
        Serial.print( " periods ");
        Serial.println( per);
        dmxtarget[chan] = val;
        dmxstep[chan] = per;
      }
      // Clear
      inputLength = 0;
      inputCommand[ inputLength] = 0;

      // A for Ack. Do not use 'A' in any other message or command
      strcpy( outputCommand, "\nA\n");
      Serial.print( outputCommand);
    }
  }

}

void setdmxvalue(int chan, int val) {
  DmxSimple.write(chan, val);
  dmxvalue[chan] = val;
#ifdef DEBUG_MSG
  Serial.print( "chan ");
  Serial.print( chan);
  Serial.print( " = ");
  Serial.println( val);
#endif
  flipled();
}
