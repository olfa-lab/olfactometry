
// command definitions
#define SET_VALVE     1
#define SET_VIAL      2
#define VALVE_STATUS  3
#define VIAL_STATUS   4
#define SET_MFC       5
#define READ_MFC      6
#define VIAL_ON       7
#define VIAL_OFF      8
#define SET_ANALOG    9
#define READ_ANALOG  10
#define SET_DIGITAL  11
#define READ_DIGITAL 12
#define MODE_DIGITAL 13
#define SET_D_MFC    14
#define READ_D_MFC   15

#define OFF 0
#define ON  1


#include <Wire.h>

// Used for buffering serial transmission data.
char buffer[128];
// Index into the serial data buffer.
uint8_t idx = 0;
// Set of word arguments of a line received via serial.
char *argv[8];
int arg1, arg2, arg3;
// i2c buffer. We are using only one buffer since each transaction should be
// atomic and there is no need to have memory of the data, which is forwarded
// to the inquiring serial connection.
uint8_t i2cBuffer[64];
int resp;

// Parse a line into words and store those words in argv array.
void parse(char *line, char **argv, uint8_t maxArgs) {
  uint8_t argCount = 0;
  while (*line != '\0') {       /* if not the end of line ....... */ 
    while (*line == ',' || *line == ' ' || *line == '\t' || *line == '\n')
      *line++ = '\0';     /* replace commas and white spaces with 0    */
    *argv++ = line;          /* save the argument position     */
    argCount++;
    if (argCount == maxArgs-1)
      break;
    while (*line != '\0' && *line != ',' && *line != ' ' && 
           *line != '\t' && *line != '\n') 
      line++;             /* skip the argument until ...    */
  }
  *argv = '\0';                 /* mark the end of argument list  */
}

// Reads a line from I2C and puts it in a buffer starting at given index.
short read_I2C_line(int i2c_buffer_index) {
	// start the buffer again from 0
	short chars_read = 0;
	char readChar;
	int aval_bytes;
	int size_of_buffer = sizeof(i2cBuffer) / sizeof(i2cBuffer[0]);

	aval_bytes = Wire.available();
	while((aval_bytes > 0) && (i2c_buffer_index < size_of_buffer-1)) {
		readChar = Wire.read();
		i2cBuffer[i2c_buffer_index++] = readChar;  // Read the byte
		chars_read++;
		aval_bytes = Wire.available();
		// Debugging
		//Serial.print(readChar);
		//Serial.print("\tBytes remaining: ");
		//Serial.println(aval_bytes);
	}
	i2cBuffer[i2c_buffer_index] = '\0';  // Denote end of string in the buffer
	return chars_read;
}

// This function will set or clear a valve.
// The arguments to the function is the device address, the valve number
// and the state to set it to.
int SetValve(uint8_t device, uint8_t valve, uint8_t state) {
  uint8_t txbuff[3];
  // Check to make sure the arguments are sane
  if (device > 127 || valve == 0 || valve > 32 || state > 1)
    return -1; // No, error return
  // Issue set valve command
  txbuff[0] = SET_VALVE; // command
  txbuff[1] = valve;     // valve to update
  txbuff[2] = state;     // state (ON or OFF)
  Wire.beginTransmission(device); // This is the I2C address of the device
  Wire.write(txbuff, 3);
  Wire.endTransmission();
  // Read back the valve status to verify that it got updated
  txbuff[0] = VALVE_STATUS;
  txbuff[1] = valve;
  Wire.beginTransmission(device);
  Wire.write(txbuff, 2);
  Wire.endTransmission();
  if (!Wire.requestFrom(device, (uint8_t)1))
    return -1; // Error return, command failed
  int value = Wire.read();
  if (value != (int)state)
	  // Error return. valve status state did not match the set valve state
      return -1;
  return 0;    // all OK
}

// This function will return the status of a valve (ON or OFF)
// The arguments to the function is the device address,
// the valve number and a pointer to the return state.
int ValveStatus(uint8_t device, uint8_t valve, uint8_t * state) {
  uint8_t txbuff[2];
  // Check to make sure the arguments are sane
  if (device > 127 || valve == 0 || valve > 32)
    return -1;
  // Issue the valve state command
  txbuff[0] = VALVE_STATUS;
  txbuff[1] = valve;
  Wire.beginTransmission(device);
  Wire.write(txbuff, 2);
  Wire.endTransmission();
  if (!Wire.requestFrom(device, (uint8_t)1))
    return -1; // Error return, command failed
  int value = Wire.read();
  if (value < 0 || value > 1)
    return -1; // Error return, invalid return value
  if (value == 0)
    *state = (uint8_t)OFF;
  else
    *state = (uint8_t)ON;
  return 0;
}

// This function will set or clear a vial (a pair of valves)
// The arguments to the function is the device address,
// the vial number and the state to set it to.
int SetVial(uint8_t device, uint8_t vial, uint8_t state) {
  uint8_t txbuff[3];
  int value;
  // Check to make sure the arguments are sane
  if (device > 127 || vial == 0 || vial > 16 || state > 1)
    return -1; // No, error return
  // Issue set vial command
  txbuff[0] = SET_VIAL; // command
  txbuff[1] = vial;     // vial to update
  txbuff[2] = state;    // state (ON or OFF)
  Wire.beginTransmission(device); // This is the I2C address of the device
  Wire.write(txbuff, 3);
  Wire.endTransmission();    
  // Read back the vial status to verify that it got updated
  txbuff[0] = VIAL_STATUS;
  txbuff[1] = vial;
  Wire.beginTransmission(device);
  Wire.write(txbuff, 2);
  Wire.endTransmission();
  if (!Wire.requestFrom(device, (uint8_t)1))
    return -3; // Error return, command failed
  value = Wire.read();
  if (value != (int)state)
	  // Error return, vial status state did not match the set vial state
	  return -4;
  return 0;    // all OK
}

// This function will return the status of a vial (ON or OFF)
// The arguments to the function is the device address,
// the vial number and a pointer to the return state.
int VialStatus(uint8_t device, uint8_t vial, uint8_t * state) {
  uint8_t txbuff[2];
  // Check to make sure the arguments are sane
  if (device > 127 || vial == 0 || vial > 16)
    return -1;
  // Issue the vial state command
  txbuff[0] = VIAL_STATUS;
  txbuff[1] = vial;
  Wire.beginTransmission(device);
  Wire.write(txbuff, 2);
  Wire.endTransmission();
  if (!Wire.requestFrom(device, (uint8_t)1))
    return -1; // Error return, command failed
  int value = Wire.read();
  if (value < 0 || value > 1)
    return -1; // Error return, invalid return value
  if (value == 0)
    *state = (uint8_t)OFF;
  else
    *state = (uint8_t)ON;
  return 0;
}

// This function will set the analog value for MFC
// The arguments to the function is the device address,
// the MFC number and the value to set.
int SetMFC(uint8_t device, uint8_t MFC, float param) {
  uint8_t txbuff[4];
  // Check to make sure the arguments are sane
  if (device > 127 || MFC == 0 || MFC > 4 || param < 0.0 || param > 1.0)
    return -1; // No, error return
  uint16_t intValue = param * 65535;
  // Issue set MFC command
  txbuff[0] = SET_MFC; // command
  txbuff[1] = MFC;     // MFC to update
  txbuff[2] = intValue & 0xff;   // low byte
  txbuff[3] = intValue >> 8;     // high
  Wire.beginTransmission(device); // This is the I2C address of the device
  Wire.write(txbuff, 4);
  Wire.endTransmission();
  if (!Wire.requestFrom(device, (uint8_t)1))
    return -1; // Error return, command failed
  uint8_t reply = Wire.read();
  if (reply)
    return reply;
  return 0;    // all OK
}

// This function will read the analog value for MFC
// The arguments to the function is the device address,
// the MFC number and a pointer to the return value.
int ReadMFC(uint8_t device, uint8_t MFC, float * value) {
  uint8_t txbuff[2];
  // Check to make sure the arguments are sane
  if (device > 127 || MFC == 0 || MFC > 2)
    return -1; // No, error return
  // Issue read MFC command
  txbuff[0] = READ_MFC; // command
  txbuff[1] = MFC;      // MFC to read
  Wire.beginTransmission(device); // This is the I2C address of the device
  Wire.write(txbuff, 2);
  Wire.endTransmission();
  if (!Wire.requestFrom(device, (uint8_t)2))
    return -2; // Error return, command failed
  uint8_t low = Wire.read(); //low
  uint16_t resp = Wire.read(); //high
  resp = (resp << 8) | low;
  float respf = (float)resp;
  if (respf > 1023.0)
    return -3;
  *value = respf/1023;
  return 0;    // all OK
}

// This function will attempt to read digitally from an MFC
// The arguments to the function are device address and MFC number.
// i2cBuffer is used to hold the returned string. Returns 0 iff successful.
int ReadDMFC(uint8_t deviceAddr, uint8_t MFCNum) {

	uint8_t txbuff[2];       // initial command
	// amount of bytes sent back from the slave after a requestFrom command.
	uint8_t bytes_back;
	int tx_buffer_index = 0;
	int bytes_to_request;
	// Check to make sure the arguments are sane
	if (deviceAddr > 127 || MFCNum == 0 || MFCNum > 2)
		return -1; // No, error return

	// Issue read MFC in digital mode command
	txbuff[0] = READ_D_MFC;  // command
	txbuff[1] = MFCNum;      // MFC to read

	do {
	Wire.beginTransmission(deviceAddr); // This is the I2C address of the device
	Wire.write(txbuff, 2);
	Wire.endTransmission();  // Send the request

	// Confirm that the request was received
	// by receiving back the length of the read string.
	bytes_back = Wire.requestFrom(deviceAddr,(uint8_t) 1);
	if (!bytes_back)  // 0 means we could not communicate
		return -1; // Error return, command failed

    // The first byte is the amount of bytes to request from the response.
	// That is equal to the amount of bytes that were read from the MFC.
	// 255 is a special code denoting transaction is still in progress.
	bytes_to_request = Wire.read();
	if (bytes_to_request == 0) {
		return -2;   // The board could not read from its serial
	}
	//Serial.print("Initial request: ");
	//Serial.print(bytes_to_request);
	//Serial.println(" bytes.");
	} while(bytes_to_request == 255);

	// Cap the request of bytes to the size of buffer we can handle.
	int size_of_buffer = sizeof(i2cBuffer) / sizeof(i2cBuffer[0]);

	do {
		if (bytes_to_request > size_of_buffer)
			bytes_to_request = size_of_buffer;
		// Ask for the reply from the MFC.
		if (!Wire.requestFrom(deviceAddr, (uint8_t)bytes_to_request))
			return -2; // Error return, command failed

		// Read the bytes into internal buffer, and advance the index marker by
		// amount of bytes read.
		tx_buffer_index += read_I2C_line(tx_buffer_index);
		//Serial.println("BUFFER: ");
		//Serial.println((char *)i2cBuffer);

		do {
		// Issue read MFC command and attempt another read.
		Wire.beginTransmission(deviceAddr);
		Wire.write(txbuff, 2);
		Wire.endTransmission();  // Send the request

		bytes_back = Wire.requestFrom(deviceAddr,(uint8_t) 1);
		if (!bytes_back)  // 0 means we could not communicate
			return -1; // Error return, command failed
		// find out how many bytes to request from the response
		bytes_to_request = Wire.read();
		//Serial.print("Request: ");
		//Serial.print(bytes_to_request);
		//Serial.println(" more bytes.");
		} while (bytes_to_request == 255);

	}  while(bytes_to_request > 0);
	return 0;
}

// This function will attempt to send the Atmel controller an ASCII command
// via i2c. This command will be forwarded to the MFC number given subsequently.
// The arguments to the function are the device address, the MFC number,
// and the string to send. Returns 0 iff successful.
int SetDMFC(uint8_t deviceAddr, uint8_t MFCNum, char *command) {
	uint8_t txbuff[2];   // initial command
	// Check to make sure the arguments are sane
	if (deviceAddr > 127 || MFCNum == 0 || MFCNum > 2)
		return -1; // No, error return

	// Issue write digitally to MFC command
	txbuff[0] = SET_D_MFC;     // command
	txbuff[1] = MFCNum;        // MFC to update
	Wire.beginTransmission(deviceAddr); // This is the I2C address of the device
	Wire.write(txbuff, 2);     // Write the command and mfc number into buffer.
	// Write the string to send to the MFC into the i2c buffer.
	Wire.write((uint8_t*)command,strlen(command));
	Wire.endTransmission();    // Send the bytes over the 2 wire interface

	// Check back response.
	int bytes_back = Wire.requestFrom(deviceAddr, (uint8_t)1);
	if (!bytes_back)
		return -1; // Error return, command failed

	// Get response code
	uint8_t reply = Wire.read();
	if (reply)
		return reply;
	return 0;    // all OK
}

// This function will exclusively set a single vial and the dummy vial ON.
// The arguments to the function is the device address and the vial number.
int VialOn(uint8_t device, uint8_t vial) {
  uint8_t txbuff[2];
  // Check to make sure the arguments are sane
  if (device > 127 || vial == 0 || vial > 16)
    return -1; // No, error return
  // Issue vial on command
  txbuff[0] = VIAL_ON; // command
  txbuff[1] = vial;     // vial to update
  Wire.beginTransmission(device); // This is the I2C address of the device
  Wire.write(txbuff, 2);
  Wire.endTransmission();    
  if (!Wire.requestFrom(device, (uint8_t)1)) {
    return -1; // Error return, valve status command failed
    Serial.println("oh no!");
  }
  uint8_t reply = Wire.read();
  if (reply)
    return reply;
  return 0;    // all OK
}

// This function will turn OFF a single vial and the dummy vial.
// The arguments to the function is the device address and the vial number.
// The function will return an error unless this and only this vial and
// the dummy vial are on.
int VialOff(uint8_t device, uint8_t vial) {
  uint8_t txbuff[2];
  // Check to make sure the arguments are sane
  if (device > 127 || vial == 0 || vial > 16)
    return -1; // No, error return
  // Issue vial off command
  txbuff[0] = VIAL_OFF; // command
  txbuff[1] = vial;     // vial to update
  Wire.beginTransmission(device); // This is the I2C address of the device
  Wire.write(txbuff, 2);
  Wire.endTransmission();
  if (!Wire.requestFrom(device, (uint8_t)1))
    return -1; // Error return, command failed
  uint8_t reply = Wire.read();
  if (reply)
    return reply;
  return 0;    // all OK
}

// This function will set the analog value for an analog-out channel.
// The arguments to the function is the device address,
// the analog-out number and the value to set.
int SetAnalog(uint8_t device, uint8_t ch, float param) {
  uint8_t txbuff[4];
  // Check to make sure the arguments are sane
  if (device > 127 || ch == 0 || ch > 2 || param < 0.0 || param > 1.0)
    return -1; // No, error return
  uint16_t intValue = param * 65535;
  // Issue set analog command
  txbuff[0] = SET_ANALOG; // command
  txbuff[1] = ch;         // channel to update
  txbuff[2] = intValue & 0xff;   // low byte
  txbuff[3] = intValue >> 8;     // high
  Wire.beginTransmission(device); // This is the I2C address of the device
  Wire.write(txbuff, 4);
  Wire.endTransmission();
  if (!Wire.requestFrom(device, (uint8_t)1))
    return -1; // Error return, command failed
  uint8_t reply = Wire.read();
  if (reply)
    return reply;
  return 0;    // all OK
}

// This function will read the analog value for an analog-in channel
// The arguments to the function is the device address,
// the analog-in number and a pointer to the return value
int ReadAnalog(uint8_t device, uint8_t ch, float * value) {
  uint8_t txbuff[2];
  // Check to make sure the arguments are sane
  if (device > 127 || ch == 0 || ch > 6)
    return -1; // No, error return
  // Issue read analog command
  txbuff[0] = READ_ANALOG; // command
  txbuff[1] = ch;          // channel to read
  Wire.beginTransmission(device); // This is the I2C address of the device
  Wire.write(txbuff, 2);
  Wire.endTransmission();
  if (!Wire.requestFrom(device, (uint8_t)2))
    return -2; // Error return, command failed
  uint8_t low = Wire.read(); //low
  uint16_t resp = Wire.read(); //high
  resp = (resp << 8) | low;
  float respf = (float)resp;
  if (respf > 1023.0)
    return -3;
  *value = respf/1023;
  return 0;    // all OK
}

// This function will set the digital value for a digital pin
// The arguments to the function is the device address,
// the pin number and the value to set.
int SetDigital(uint8_t device, uint8_t pin, uint8_t value) {
  uint8_t txbuff[3];
  // Check to make sure the arguments are sane
  if (device > 127 || pin == 0 || pin > 6 || value > 1)
    return -1; // No, error return
  // Issue set digital command
  txbuff[0] = SET_DIGITAL; // command
  txbuff[1] = pin;         // pin to update
  txbuff[2] = value;   // value
  Wire.beginTransmission(device); // This is the I2C address of the device
  Wire.write(txbuff, 3);
  Wire.endTransmission();
  if (!Wire.requestFrom(device, (uint8_t)1))
    return -1; // Error return, command failed
  uint8_t reply = Wire.read();
  if (reply)
    return reply;
  return 0;    // all OK
}

// This function will read the digital value for a digital pin
// The arguments to the function is the device address,
// the pin number and a pointer to the return value.
int ReadDigital(uint8_t device, uint8_t pin, uint8_t * value) {
  uint8_t txbuff[2];
  // Check to make sure the arguments are sane
  if (device > 127 || pin == 0 || pin > 6)
    return -1; // No, error return
  // Issue read analog command
  txbuff[0] = READ_DIGITAL; // command
  txbuff[1] = pin;          // pin to read
  Wire.beginTransmission(device); // This is the I2C address of the device
  Wire.write(txbuff, 2);
  Wire.endTransmission();
  if (!Wire.requestFrom(device, (uint8_t)2))
    return -2; // Error return, command failed
  uint8_t resp = Wire.read();
  if (resp > 1)
    return -3;
  *value = resp;
  return 0;    // all OK
}

// This function will set the digital mode for a digital pin
// The arguments to the function is the device address,
// the pin number and the mode to set.
int ModeDigital(uint8_t device, uint8_t pin, uint8_t value) {
  uint8_t txbuff[3];
  // Check to make sure the arguments are sane
  if (device > 127 || pin == 0 || pin > 6 || value > 1)
    return -1; // No, error return
  // Issue set digital command
  txbuff[0] = MODE_DIGITAL; // command
  txbuff[1] = pin;         // pin to update
  txbuff[2] = value;   // value
  Wire.beginTransmission(device); // This is the I2C address of the device
  Wire.write(txbuff, 3);
  Wire.endTransmission();
  if (!Wire.requestFrom(device, (uint8_t)1))
    return -1; // Error return, command failed
  uint8_t reply = Wire.read();
  if (reply)
    return reply;
  return 0;    // all OK
}

void setup() 
{
  pinMode(0, OUTPUT);
  digitalWrite(0, LOW);
  Wire.begin();
  Serial.begin(115200);
  Serial.println();
  Serial.print(">");
}

void loop() 
{
  uint8_t c;
  if (Serial.available() > 0) { // PC communication
    c = Serial.read();
    if (c == '\r') {
      buffer[idx] = 0;
      Serial.println();
      parse((char*)buffer, argv, sizeof(argv));
      if (strcmp(argv[0], "valve") == 0) {
        if (strlen(argv[1]) > 0 && strlen(argv[2]) > 0) {
          arg1 = atoi(argv[1]);
          arg2 = atoi(argv[2]);
          if (arg1 > 0 && arg1 < 128 && arg2 > 0 && arg2 < 33) {
            if (argv[3] == '\0') {
              if (resp = ValveStatus((uint8_t)arg1, (uint8_t)arg2, &c)) {
                Serial.print("Error ");
                Serial.println(resp);
              } else if (c == OFF)
                Serial.println("off");
              else 
                Serial.println("on");
            } else if (strcmp(argv[3], "on") == 0) {
              if (arg2 == 6)
                  SetDigital((uint8_t)arg1, (uint8_t)4, (uint8_t)ON);
              if (resp = SetValve((uint8_t)arg1, (uint8_t)arg2, (uint8_t)ON)) {
                Serial.print("Error ");
                Serial.println(resp);
              } else {
                SetDigital((uint8_t)arg1, (uint8_t)4, (uint8_t)OFF);
                Serial.println("valve set");
              }
            } else if (strcmp(argv[3], "off") == 0) {         
              if (resp = SetValve((uint8_t)arg1, (uint8_t)arg2, (uint8_t)OFF)) {
                Serial.print("Error ");
                Serial.println(resp);
              } else {
                Serial.println("valve cleared");
              }
            } else {
              Serial.println("valve <DEVICE> <N> {on,off}");
            }
          } else {
            Serial.println("valve <DEVICE> <N> {on,off}, N = {1..32}");
          }
        } else {
          Serial.println("valve <DEVICE> <N> {on,off}");
        }
      } else if (strcmp(argv[0], "vial") == 0) {
        if (strlen(argv[1]) > 0 && strlen(argv[2]) > 0) {
          arg1 = atoi(argv[1]);
          arg2 = atoi(argv[2]);
          if (arg1 > 0 && arg1 < 128 && arg2 > 0 && arg2 < 17) {
            if (argv[3] == '\0') {
              if (resp = VialStatus((uint8_t)arg1, (uint8_t)arg2, &c)) {
                Serial.print("Error ");
                Serial.println(resp);
              } else if (c == OFF)
                Serial.println("off");
              else 
                Serial.println("on");
            } else if (strcmp(argv[3], "on") == 0) {
              SetDigital((uint8_t)arg1, (uint8_t)3, (uint8_t)ON);
              if (resp = SetVial((uint8_t)arg1, (uint8_t)arg2, (uint8_t)ON)) {
                Serial.print("Error ");
                Serial.println(resp);
              } else {
                SetDigital((uint8_t)arg1, (uint8_t)3, (uint8_t)OFF);
                Serial.println("vial set");
              }
            } else if (strcmp(argv[3], "off") == 0) {
              if (resp = SetVial((uint8_t)arg1, (uint8_t)arg2, (uint8_t)OFF)) {
                Serial.print("Error ");
                Serial.println(resp);
              } else
                Serial.println("vial cleared");
            } else {
              Serial.println("vial <DEVICE> <N> {on,off}");
            }
          } else {
            Serial.println("vial <DEVICE> <N> {on,off}, N = {1..16}");
          }
        } else {
          Serial.println("vial <DEVICE> <N> {on,off}");
        }
      } else if (strcmp(argv[0], "vialOn") == 0) {
        if (strlen(argv[1]) > 0 && strlen(argv[2]) > 0) {
          arg1 = atoi(argv[1]);
          arg2 = atoi(argv[2]);
          if (arg1 > 0 && arg1 < 128 && arg2 > 0 && arg2 < 17) {
            SetDigital((uint8_t)arg1, (uint8_t)3, (uint8_t)ON);
            if (resp = VialOn((uint8_t)arg1, (uint8_t)arg2)) {
              Serial.print("Error ");
              Serial.println(resp);
            } else {
              SetDigital((uint8_t)arg1, (uint8_t)3, (uint8_t)OFF);
              Serial.println("vial and dummy on");
            }
          } else {
            Serial.println("vialOn <DEVICE> <N>, N = {1..16}");
          }
        } else {
          Serial.println("vialOn <DEVICE> <N>");
        }
      } else if (strcmp(argv[0], "vialOff") == 0) {
        if (strlen(argv[1]) > 0 && strlen(argv[2]) > 0) {
          arg1 = atoi(argv[1]);
          arg2 = atoi(argv[2]);
          if (arg1 > 0 && arg1 < 128 && arg2 > 0 && arg2 < 17) {
            //SetDigital((uint8_t)arg1, (uint8_t)3, (uint8_t)ON);
            if (resp = VialOff((uint8_t)arg1, (uint8_t)arg2)) {
              Serial.print("Error ");
              Serial.println(resp);
            } else {
              //SetDigital((uint8_t)arg1, (uint8_t)3, (uint8_t)OFF);
              Serial.println("vial and dummy off");
            }
          } else {
            Serial.println("vialOff <DEVICE> <N>, N = {1..16}");
          }
        } else {
          Serial.println("vialOff <DEVICE> <N>");
        }
      } else if (strcmp(argv[0], "MFC") == 0) {
        if (strlen(argv[1]) > 0 && strlen(argv[2]) > 0) {
          arg1 = atoi(argv[1]);
          arg2 = atoi(argv[2]);
          if (arg1 > 0 && arg1 < 128 && arg2 > 0 && arg2 < 3) {
            if (argv[3] == '\0') {
              float value;
              if (resp = ReadMFC((uint8_t)arg1, (uint8_t)arg2, &value)) {
                Serial.print("Error ");
                Serial.println(resp);
              } else 
                Serial.println(value);
            } else {
              float param = atof(argv[3]);
              if (resp = SetMFC((uint8_t)arg1, (uint8_t)arg2, param)) {
                Serial.print("Error ");
                Serial.println(resp);
              } else
                Serial.println("MFC set");
            }
          } else {
            Serial.println("MFC <DEVICE> <N> {value}, N = {1..2}, value = "
            		"{0.0...1.0}\t ==> \t Set or Read (no value specified)"
            		" MFC N");
          }
        } else {
          Serial.println("MFC <DEVICE> <N> {value}");
        }
/*
      } else if (strcmp(argv[0], "analog") == 0) {
        if (strlen(argv[1]) > 0 && strlen(argv[2]) > 0) {
          arg1 = atoi(argv[1]);
          arg2 = atoi(argv[2]);
          if (arg1 > 0 && arg1 < 128 && arg2 > 0 && arg2 < 3) {
            if (argv[3] == '\0') {
              float value;
              if (resp = ReadAnalog((uint8_t)arg1, (uint8_t)arg2, &value)) {
                Serial.print("Error ");
                Serial.println(resp);
              } else 
                Serial.println(value);
            } else {
              float param = atof(argv[3]);
              if (resp = SetAnalog((uint8_t)arg1, (uint8_t)arg2, param)) {
                Serial.print("Error ");
                Serial.println(resp);
              } else
                Serial.println("analog-out set");
            }
          } else {
            Serial.println("analog <DEVICE> <N> {value}, N = {1..2}");
          }
        } else {
          Serial.println("analog <DEVICE> <N> {value}");
        }
*/
      }
      // Ask the controller board to communicate to MFC (read/write) digitally
      else if(strcmp(argv[0], "DMFC") == 0) {
    	  if (strlen(argv[1]) > 0 && strlen(argv[2]) > 0) {
    		  arg1 = atoi(argv[1]);
    	      arg2 = atoi(argv[2]);
    	      if (arg1 > 0 && arg1 < 128 && arg2 > 0 && arg2 < 3) {
    	          // We want to read from the MFC
    	    	  if (argv[3] == '\0') {
    	    		  if (resp = ReadDMFC((uint8_t)arg1, (uint8_t)arg2)) {
    	                  Serial.print("Error ");
    	                  Serial.println(resp);
    	              }
    	    		  else {
    	    			  Serial.println((char*)i2cBuffer);
    	    		  }
    	    	  }
    	    	  // Write the given command to the MFC
    	    	  else {
    	    		  char* command;
    	    		  command = argv[3];
    	    		  resp = SetDMFC((uint8_t)arg1, (uint8_t)arg2, command);
    	              if (resp) {
    	                  Serial.print("Error ");
    	                  Serial.println(resp);
    	              }
    	              else {
                          Serial.println("MFC set");
    	              }
    	          }
    	      }
    	      else {
    	    	  Serial.println("DMFC <DEVICE> <N> {string}, N = {1..2},"
    	    			  " string = {ASCII string} \t Send or Read (when no"
    	    			  " string specified) a command to MFC N");
    	      }
    	  }
    	  else {
    		  Serial.println("DMFC <DEVICE> <N> {string}");
    	  }
      } else if (strcmp(argv[0], "analogSet") == 0) {
        if (strlen(argv[1]) > 0 && strlen(argv[2]) > 0 && strlen(argv[3]) > 0) {
          arg1 = atoi(argv[1]);
          arg2 = atoi(argv[2]);
          float param = atof(argv[3]);
          if (arg1 > 0 && arg1 < 128 && arg2 > 0 && arg2 < 3) {
            if (resp = SetAnalog((uint8_t)arg1, (uint8_t)arg2, param)) {
              Serial.print("Error ");
              Serial.println(resp);
            } else
              Serial.println("analog-out set");
          } else {
            Serial.println("analogSet <DEVICE> <N> {value},"
            		" N = {1..2}, value = {0.0...1.0} ");
          }
        } else {
          Serial.println("analogSet <DEVICE> <N> {value}");
        }
      } else if (strcmp(argv[0], "analogRead") == 0) {
        if (strlen(argv[1]) > 0 && strlen(argv[2]) > 0) {
          arg1 = atoi(argv[1]);
          arg2 = atoi(argv[2]);
          if (arg1 > 0 && arg1 < 128 && arg2 > 0 && arg2 < 7) {
            float value;
            if (resp = ReadAnalog((uint8_t)arg1, (uint8_t)arg2, &value)) {
              Serial.print("Error ");
              Serial.println(resp);
            } else 
              Serial.println(value);
          } else {
            Serial.println("analogRead <DEVICE> <N>, N = {1..6}");
          }
        } else {
          Serial.println("analogRead <DEVICE> <N>");
        }
      } else if (strcmp(argv[0], "digitalSet") == 0) {
        if (strlen(argv[1]) > 0 && strlen(argv[2]) > 0 && strlen(argv[3]) > 0) {
          arg1 = atoi(argv[1]);
          arg2 = atoi(argv[2]);
          arg3 = atoi(argv[3]);
          if (arg1 > 0 && arg1 < 128 && arg2 > 0 && arg2 < 7 &&
        		  arg3 >= 0 && arg3 < 2) {
            if (resp = SetDigital((uint8_t)arg1, (uint8_t)arg2,
            		(uint8_t)arg3)){
              Serial.print("Error ");
              Serial.println(resp);
            } else
              Serial.println("digital pin set");
          } else {
            Serial.println("digitalSet <DEVICE> <N> {value},"
            		" N = {1..6}, value = 0/1");
          }
        } else {
          Serial.println("digitalSet <DEVICE> <N> {value}");
        }
      } else if (strcmp(argv[0], "digitalRead") == 0) {
        if (strlen(argv[1]) > 0 && strlen(argv[2]) > 0) {
          arg1 = atoi(argv[1]);
          arg2 = atoi(argv[2]);
          if (arg1 > 0 && arg1 < 128 && arg2 > 0 && arg2 < 7) {
            uint8_t value;
            if (resp = ReadDigital((uint8_t)arg1, (uint8_t)arg2, &value)) {
              Serial.print("Error ");
              Serial.println(resp);
            } else 
              Serial.println(value);
          } else {
            Serial.println("digitalRead <DEVICE> <N>, N = {1..6}");
          }
        } else {
          Serial.println("digitalRead <DEVICE> <N>");
        }
      } else if (strcmp(argv[0], "digitalMode") == 0) {
        if (strlen(argv[1]) > 0 && strlen(argv[2]) > 0 && strlen(argv[3]) > 0) {
          arg1 = atoi(argv[1]);
          arg2 = atoi(argv[2]);
          arg3 = atoi(argv[3]);
          if (arg1 > 0 && arg1 < 128 && arg2 > 0 && arg2 < 7
        		  && arg3 >= 0 && arg3 < 2) {
            if (resp = ModeDigital((uint8_t)arg1, (uint8_t)arg2,
            		(uint8_t)arg3)) {
              Serial.print("Error ");
              Serial.println(resp);
            } else
              Serial.println("digital mode set");
          } else {
            Serial.println("digitalMode <DEVICE> <N> {value}, N = {1..6),"
            		" value = 0/1\t ==> \t 0 = input, 1 = output");
          }
        } else {
          Serial.println("digitalMode <DEVICE> <N> {value}");
        }
      } else if (strcmp(argv[0], "speed") == 0) {
        if (strlen(argv[1]) > 0 && strlen(argv[2]) > 0) {
          arg1 = atoi(argv[1]);
          arg2 = atoi(argv[2]);
          if (arg1 > 0 && arg1 < 128 && arg2 > 0 && arg2 < 17) {
            if (resp = VialOn((uint8_t)arg1, (uint8_t)arg2)) {
              Serial.print("Error ");
              Serial.println(resp);
            } else {
              for (int i = 0; i < 10000; i++) {
                digitalWrite(0, LOW);
                VialOff((uint8_t)arg1, (uint8_t)arg2);
                digitalWrite(0, HIGH);
                VialOn((uint8_t)arg1, (uint8_t)arg2);
              }
              digitalWrite(0, LOW);
              VialOff((uint8_t)arg1, (uint8_t)arg2);
              Serial.println("vial speed test done");
            }
          } else {
            Serial.println("speed <DEVICE> <N>, N = {1..16}");
          }
        } else {
          Serial.println("speed <DEVICE> <N>");
        }
      }  else if ((strcmp(argv[0], "help") == 0) || (strcmp(argv[0], "?") == 0)) {
           Serial.println("valve <DEVICE> <N> {on,off}, N = {1..32}\t ==> \t"
        		   " Turn single solenoid valve on/off");
           Serial.println("vial <DEVICE> <N> {on,off}, N = {1..16}\t ==> \t"
        		   " Turn a vial (pair of valves) on/off");
           Serial.println("vialOn <DEVICE> <N>, N = {1..16}\t ==> \t"
        		   " Turn ON vial(valve pair) N as well as the dummy vial");
           Serial.println("vialOff <DEVICE> <N>, N = {1..16}\t ==> \t"
        		   " Turn OFF vial(valve pair) N, together with the dummy vial"
        		   " only iff they are already ON");
           Serial.println("MFC <DEVICE> <N> {value}, N = {1..2},"
        		   " value = {0.0...1.0}\t ==> \t"
        		   " Set or Read (no value specified) MFC N");
           Serial.println("DMFC <DEVICE> <N> {string}, N = {1..2},"
        		   " string = {ASCII string} \t Send or Read"
        		   " (when no string specified) a command to MFC N");
           Serial.println("analogSet <DEVICE> <N> {value}, N = {1..2},"
        		   " value = {0.0...1.0} ");
           Serial.println("analogRead <DEVICE> <N>, N = {1..6}");
           Serial.println("digitalSet <DEVICE> <N> {value},"
        		   " N = {1..6}, value = 0/1");
           Serial.println("digitalRead <DEVICE> <N>, N = {1..6}");
           Serial.println("digitalMode <DEVICE> <N> {value},"
        		   " N = {1..6), value = 0/1\t ==> \t 0 = input, 1 = output");
      }
      idx = 0;
      Serial.print(">");
    } else if (((c == '\b') || (c == 0x7f)) && (idx > 0)) {
      idx--;
      Serial.write(c);
      Serial.print(" ");
      Serial.write(c);
    } 
    else if ((c >= ' ') && (idx < sizeof(buffer) - 1)) {
      buffer[idx++] = c;
      Serial.write(c);
    }
  }
}
