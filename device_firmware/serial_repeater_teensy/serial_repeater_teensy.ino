/*
This splits one USB port of a Teensy 3.1 into two TTL serial ports. It broadcasts messages from the USB serial
to two TTL serials, and forwards messages from either of TTL serials to the USB serial.
There is no crosstalk between the TX lines of the TTL serial ports. 


USB SERIAL >---------------> TTL SERIAL 1
                  |
                  |
                  ---------> TTL SERIAL 2
                  

TTL SERIAL 1 >-------------> USB SERIAL

TTL SERIAL 2 >-------------> USB SERIAL

This was designed to allow users to put two addressable Alicat MFCs on a single USB serial port.

by CW
*/

//#define DEBUG_ECHO   // if this is defined, the commands will be echoed back from the usb serial to the usb serial.

#define BAUDRATE 38400
#define SERIAL_FMT SERIAL_8N1_RXINV_TXINV
#define LEDPIN 13

char buffer_rx[128];  // this buffer recieves from USB serial (CPU)
char buffer_tx[128];  // this buffer recieves from Serials 1 and 2 (Alicats)
int nbytes_rx = 0;
int nbytes_tx = 0;

int readSerial(HardwareSerial *serial, char *buff) {
  //overload for TTL serial.
  int i = 0;
  while (serial->available()) {
    buff[i] = serial->read();
    i++;
  }
  return i; // the number of bytes that have accumulated in the buffer.
}

int readSerial(usb_serial_class *serial, char *buff) {
  //overload for USB serial.
  int i = 0;
  while (serial->available()) {
    buff[i] = serial -> read();
    i++;
  }
  return i;
}

void setup() {
  pinMode(LEDPIN, OUTPUT);
  Serial.begin(115200);  // USB serial.
  Serial1.begin(BAUDRATE, SERIAL_FMT);  //Alicat default = 19200
  Serial2.begin(BAUDRATE, SERIAL_FMT);
}

void loop() {

  if (Serial.available()) {
    digitalWrite(LEDPIN, HIGH);
    // broadcast CPU message to other serials. Wait for response
    nbytes_rx = readSerial(&Serial, buffer_rx);
    //    repeatSerial(&Serial1, buffer_rx, nbytes_rx);
    //    repeatSerial(&Serial2, buffer_rx, nbytes_rx);
    for (int i = 0; i < nbytes_rx; i++) {
      Serial1.write(buffer_rx[i]);
      Serial2.write(buffer_rx[i]);
      #ifdef DEBUG_ECHO
      Serial.write(buffer_rx[i]);  //DEBUG
      #endif
    }
    Serial1.flush();
    Serial2.flush();
    digitalWrite(LEDPIN, LOW);
  }

  if (Serial1.available()) {    
    nbytes_tx = readSerial(&Serial1, buffer_tx);
    Serial.write(buffer_tx, nbytes_tx);
    Serial.flush();
  }

  if (Serial2.available()) {
    nbytes_tx = readSerial(&Serial2, buffer_tx);
    Serial.write(buffer_tx, nbytes_tx);
    Serial.flush();

  }
}
