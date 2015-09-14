#define LED_PIN      20 // Green LED.
#define VD_PIN        0 // Valve driver SPI chip select pin.
// HIGH if any valve is on(this is pin 7 1n the 10-pin connector).
#define VALVE_PIN     2
 // HIGH if any vial pair is on (this is pin 8 in the 10-pin connector).
#define VIAL_PIN      3
#define DAC_PIN       4 // DAC SPI chip select pin.
#define I2C_A0       12 // I2C address DIP switch bits A0 is LSB.
#define I2C_A1       13
#define I2C_A2       14
#define I2C_A3       15

// Commands received from master via I2C interface.
#define SET_VALVE     1    // Set state of an individual solenoid valve.
#define SET_VIAL      2    // Set setate of a vial (solenoid pair).
#define VALVE_STATUS  3    // Report back status of an individual solenoid valve
#define VIAL_STATUS   4    // Report back status of a vial (ON/OFF).
#define SET_MFC       5    // Set MFC to an analog value.
#define READ_MFC      6    // Read analog output of MFC.
#define VIAL_ON       7    // Turn ON a vial (solenoid pair).
#define VIAL_OFF      8    // Turn OFF a vial (solenoid pair).
#define SET_ANALOG    9    // Output an analog voltage value.
#define READ_ANALOG  10    // Read an analog input.
#define SET_DIGITAL  11    // Set a digital pin HIGH or LOW.
#define READ_DIGITAL 12    // Read the status of a digital pin.
#define MODE_DIGITAL 13    // Switch the mode of a digital pin (input or output)
#define SET_D_MFC   14    // Send a message to an MFC via serial interface.
#define READ_D_MFC   15    // Read a serial message from an MFC.

// Command used to advance the state of a Serial read command (READ_D_MFC)
// Internally changed only. We need an extra state since a read can return
// a variable length response. In the comm. protocol, first we sent back the
// number of bytes read on the Serial, then we send the bytes when so requested
// by the master.
#define GET_D_MFC    16

#define MAP_LED_TO_VIAL  // Map the onboard LED to VIAL-ON
//#define MAP_LED_TO_VALVE // Map the LED to VALVE-ON

// Bit masks for which valves are ON (value = 1) or OFF (value = 0)
uint32_t valves, bits;
uint8_t address;			// I2C address of the ATmega chip. 4 bit long.
volatile uint8_t cmd;		// Command received from the master
// Used to send back the state of a valve or vial (ON or OFF or error).
volatile uint8_t state;
// Used to hold the value of a READ on one of the 10bit analog-IN channels
// of the ATmega.
volatile uint16_t analogReadValue;
// Used to hold the value of a read on a digital pin of the ATmega.
volatile uint8_t digitalReadValue;
volatile uint8_t cmdResp;			// Response code to the master command
// 32 bytes capacity buffer to be used for Serial communication
// One Rx and one Tx buffer for both serials since we only use them one at a
// time and when asked by the master. If more devices are communicating with
// each other over the i2c, obviously this protocol needs to change.
char sbuffer_rx[32];
char sbuffer_tx[32];

// Flag that is used to indicate need of sending data over serial.
uint8_t sendSerialFlag = 0;
// Flag that is used to indicate a read request over serial.
uint8_t readSerialFlag = 0;
// Counter for maximum number of tries to attempt reading a Serial port.
uint8_t remainingTries = 10;
boolean inSerialReading = false;
boolean doneSerialReading = false;

// include the library code:
#include <SPI.h>
#include <Wire.h>

// AD5666 DAC write routine
void dacWrite(uint8_t dac, uint16_t value) {
	// dac = dac output channel, 0 - 3
	// value = 16 bit output value
	digitalWrite(DAC_PIN, LOW);
	SPI.transfer(0x03);				// CMD = 0011, write & update dac channel
	SPI.transfer(((dac & 0x0f) << 4) | ((value & 0xf000) >> 12));
	SPI.transfer((value & 0x0ff0) >> 4);
	SPI.transfer((value & 0x000f) << 4);
	digitalWrite(DAC_PIN, HIGH);
	digitalRead(DAC_PIN);			// adding extra time?
}

void vdTransfer(uint16_t vd1, uint16_t vd2, uint16_t vd3, uint16_t vd4) {
	digitalWrite(VD_PIN, LOW);
	SPI.transfer(vd4 >> 8);
	SPI.transfer(vd4 & 0xff);
	SPI.transfer(vd3 >> 8);
	SPI.transfer(vd3 & 0xff);
	SPI.transfer(vd2 >> 8);
	SPI.transfer(vd2 & 0xff);
	SPI.transfer(vd1 >> 8);
	SPI.transfer(vd1 & 0xff);
	digitalWrite(VD_PIN, HIGH);
	digitalRead(VD_PIN);
}

void setValves(void) {
	int i;
	uint32_t mask;
	digitalWrite(VD_PIN, LOW);
	SPI.transfer(0xc7);
	SPI.transfer(valves >> 24);
	SPI.transfer(0xc7);
	SPI.transfer(valves >> 16);
	SPI.transfer(0xc7);
	SPI.transfer(valves >> 8);
	SPI.transfer(0xc7);
	SPI.transfer(valves);
	digitalWrite(VD_PIN, HIGH);
	digitalRead(VD_PIN);
	if (valves == 0) {
		digitalWrite(VALVE_PIN, LOW);
#ifdef MAP_LED_TO_VALVE
		digitalWrite(LED_PIN, LOW);
#endif
	} else {
		digitalWrite(VALVE_PIN, HIGH);
#ifdef MAP_LED_TO_VALVE
		digitalWrite(LED_PIN, HIGH);
#endif
	}
	// check if pairs of valves (i.e vials) are ON
	// (0x03 = binary 11 = both pairs ON)
	for (i = 0; i < 16; i++) {
		mask = (valves >> (i * 2)) & 0x03;
		if (mask == 0x03) {
			digitalWrite(VIAL_PIN, HIGH);
#ifdef MAP_LED_TO_VIAL
			digitalWrite(LED_PIN, HIGH);
#endif
			break;
		}
	}
	if (i == 16) {
		digitalWrite(VIAL_PIN, LOW);
#ifdef MAP_LED_TO_VIAL
		digitalWrite(LED_PIN, LOW);
#endif
	}
}

// Reads a line from I2C and puts it in a buffer
// Line length is equal to numBytes
// TODO: Error handling? It is needed for all of the commands!!!
void read_line_i2c(uint8_t numBytes) {
	int c;
	// Read numBytes bytes from the Wire buffer. This is put into the transmit
	// serial buffer so that we can send the bytes when required.
	for (c = 0; c < numBytes; c++)
		sbuffer_tx[c] = Wire.read();
	sbuffer_tx[c] = '\0';   // end of string
}

// Reads a line from Serial and puts it in the buffer
void read_line_serial() {

	int size_of_buffer = sizeof(sbuffer_rx) / sizeof(sbuffer_rx[0]);
	byte chars_read = 0;

	// Ran out of attempts. Place the end of string character at the start
	// of the buffer to denote no response (i.e 0 characters read).
	if (remainingTries == 1) {
		sbuffer_rx[0] = '\0';
		remainingTries = 10;  // Restart counter
		readSerialFlag = 0;   // Remove the read flag
		doneSerialReading = true;
	}

	// First Serial port, i.e mfc 1
	else if (readSerialFlag == 1) {
		if (!Serial.available())
			remainingTries -= 1;
		else {
			// Carriage return is the separator of lines/commands to read
			chars_read = Serial.readBytesUntil('\r', sbuffer_rx,
					size_of_buffer - 1);
			sbuffer_rx[chars_read] = '\0';  // mark end of string
			readSerialFlag = 0;
			remainingTries = 10;
//			Serial1.print("Read ");
//			Serial1.print(chars_read);
//			Serial1.print(" characters successfully. Try: ");
//			Serial1.println(remainingTries);
//			Serial1.print("Buffer: ");
//			Serial1.print((char *)sbuffer_rx);
//			Serial1.print("\tsize: ");
//			Serial1.println(strlen((char *) sbuffer_rx));
//			Serial1.print("More data available? ");
//			Serial1.println(Serial.available());
			doneSerialReading = true;
		}
	}
	// Second Serial port, i.e mfc 2
	else if (readSerialFlag == 2) {
		if (!Serial1.available()) {
			remainingTries -= 1;
		} else {
			// Carriage return is the separator of lines/commands to read
			chars_read = Serial1.readBytesUntil('\r', sbuffer_rx,
					size_of_buffer - 1);
			sbuffer_rx[chars_read] = '\0';  // mark end of string
			readSerialFlag = 0;
			remainingTries = 10;
			doneSerialReading = true;
		}
	}
//	Serial1.print("Attempted to read. Try: ");
//	Serial1.println(remainingTries);
//	Serial1.print("Buffer: ");
//	Serial1.print((char *)sbuffer_rx);
//	Serial1.print("\tsize: ");
//	Serial1.println(strlen((char *) sbuffer_rx));
}

void setup() {
	pinMode(LED_PIN, OUTPUT);
	pinMode(VD_PIN, OUTPUT);
	pinMode(VALVE_PIN, OUTPUT);
	pinMode(VIAL_PIN, OUTPUT);

	digitalWrite(LED_PIN, LOW);
	digitalWrite(VD_PIN, HIGH);

	// initialize SPI:
	SPI.begin();
	// use SPI clock mode 2
	SPI.setDataMode(SPI_MODE1);
	// set clock mode to FCLK/4
	SPI.setClockDivider(SPI_CLOCK_DIV4);

	// DAC1 (AD5666) setup
	// Setup DAC REF register
	digitalWrite(DAC_PIN, LOW);
	SPI.transfer(0x08); // CMD = 1000
	SPI.transfer(0x00);
	SPI.transfer(0x00);
	SPI.transfer(0x01); // Standalone mode, REF on
	digitalWrite(DAC_PIN, HIGH);
	digitalRead(DAC_PIN); // add some time

	// Power up all four DACs
	digitalWrite(DAC_PIN, LOW);
	SPI.transfer(0x04); // CMD = 0100
	SPI.transfer(0x00);
	SPI.transfer(0x00); // Normal operation (power-on)
	SPI.transfer(0x0f); // All four DACs
	digitalWrite(DAC_PIN, HIGH);
	digitalRead(DAC_PIN);

	// Set DAC outputs to 0V
	dacWrite(0, 0x0000); // 0V
	dacWrite(1, 0x0000); // 0V
	dacWrite(2, 0x0000); // 0V
	dacWrite(3, 0x0000); // 0V

	valves = 0x00000000;
	setValves();

	// get the I2C address
	address = 0;
	if (digitalRead(I2C_A3))
		address |= 0x08;
	if (digitalRead(I2C_A2))
		address |= 0x04;
	if (digitalRead(I2C_A1))
		address |= 0x02;
	if (digitalRead(I2C_A0))
		address |= 0x01;

	Wire.begin(address);
	Wire.onReceive(receiveEvent); // register event
	Wire.onRequest(requestEvent); // register event

	// MFC communications
	Serial.begin(38400);
	Serial1.begin(38400);

	// Status message
	//Serial.println("Restarting!\n");

}

// Function that executes whenever data is received from master.
// This function is registered as an event, see setup().
// int parameter is the number of bytes read from the master. It's maximum is 32
void receiveEvent(int howMany) {
	noInterrupts();
	cmdResp = 255; // default is unrecognized command
	cmd = Wire.read(); // receive byte as a character
	if ((cmd == SET_VALVE) && (howMany == 3)) {
		uint8_t valve = Wire.read();
		state = Wire.read();
		if ((valve > 0) && (valve < 33) && (state < 2)) {
			bits = 0x00000001;
			bits = bits << (valve - 1);
			if (state == 1)
				valves = valves | bits;
			else
				valves = valves & ~bits;
			setValves();
			cmdResp = 0;
		}
	} else if ((cmd == SET_VIAL) && (howMany == 3)) {
		uint8_t vial = Wire.read();
		state = Wire.read();
		if ((vial > 0) && (vial < 17) && (state < 2)) {
			bits = 0x00000003;
			bits = bits << ((vial - 1) * 2);
			if (state == 1)
				valves = valves | bits;
			else
				valves = valves & ~bits;
			setValves();
			cmdResp = 0;
		}
	} else if ((cmd == VALVE_STATUS) && (howMany == 2)) {
		uint8_t valve = Wire.read();
		if ((valve > 0) && (valve < 33)) {
			state = (uint8_t)((valves >> (valve - 1)) & 0x0001);
		}
	} else if ((cmd == VIAL_STATUS) && (howMany == 2)) {
		uint8_t vial = Wire.read();
		if ((vial > 0) && (vial < 17)) {
			bits = 0x00000003;
			bits = bits << ((vial - 1) * 2);
			if ((valves & bits) == bits)
				state = 1;
			else if ((~valves & bits) == bits)
				state = 0;
			else
				state = 0xff;
			cmdResp = 0;
		}
	} else if ((cmd == SET_MFC) && (howMany == 4)) {
		uint8_t mfc = Wire.read();
		uint8_t low = Wire.read();
		uint16_t value = Wire.read();
		value = (value << 8) | low;
		if (mfc > 0 && mfc < 3) {
			dacWrite(mfc - 1, value);
			cmdResp = 0;
		}
	} else if ((cmd == READ_MFC) && (howMany == 2)) {
		uint8_t mfc = Wire.read();
		if (mfc > 0 && mfc < 3) {
			analogReadValue = analogRead(mfc - 1);
			cmdResp = 0;
		}
	} // Send command to MFC via digital serial communication
	else if ((cmd == SET_D_MFC) && (howMany > 1)) {
		 // Grab mfc number (Also corresponding to Serial port number)
		uint8_t mfc = Wire.read();

		// Read the command line from I2C and use the global buffer
		// to place it in. First byte of the request was the command code.
		// Second byte was the mfc number. We already read those two bytes.
		if (howMany > 2)
			read_line_i2c((uint8_t) howMany - 2);

		// Set flag to forward the filled buffer to the appropriate serial.
		// This handler currently is running with interrupts disabled.
		// Wait till the end for re-enabling them to actually send the string
		// over Serial. The sending is done in the loop when flags are set.
		if (mfc == 1)
			sendSerialFlag = 1;
		else if (mfc == 2)
			sendSerialFlag = 2;
		// Meaning we got the command and did the appropriate actions.
		cmdResp = 0;
	}   // Read back a serial string from MFC
	else if ((cmd == READ_D_MFC) && (howMany > 1)) {
		 // Grab mfc number (Also corresponding to Serial port number).
		uint8_t mfc = Wire.read();

		// Set flags to read the Serial outside interrupts.
		// This way we do not make the master wait.
		if (mfc == 1) {
			readSerialFlag = 1;
			inSerialReading = true;
		}

		else if (mfc == 2) {
			readSerialFlag = 2;
			inSerialReading = true;
		}
		// Meaning we got the command and started the appropriate actions.
		cmdResp = 0;
	} else if ((cmd == SET_ANALOG) && (howMany == 4)) {
		uint8_t ch = Wire.read();
		uint8_t low = Wire.read();
		uint16_t value = Wire.read();
		value = (value << 8) | low;
		if (ch > 0 && ch < 3) {
			dacWrite(ch + 1, value);
			cmdResp = 0;
		}
	} else if ((cmd == READ_ANALOG) && (howMany == 2)) {
		uint8_t ch = Wire.read();
		if (ch > 0 && ch < 7) {
			analogReadValue = analogRead(ch + 1);
			cmdResp = 0;
		}
	} else if ((cmd == SET_DIGITAL) && (howMany == 3)) {
		uint8_t ch = Wire.read();
		uint8_t value = Wire.read();
		if (ch > 0 && ch < 7 && value < 2) {
			digitalWrite(ch + 23, value);
			cmdResp = 0;
		}
	} else if ((cmd == READ_DIGITAL) && (howMany == 2)) {
		uint8_t ch = Wire.read();
		if (ch > 0 && ch < 7) {
			digitalReadValue = digitalRead(ch + 23);
			cmdResp = 0;
		}
	} else if ((cmd == MODE_DIGITAL) && (howMany == 3)) {
		uint8_t ch = Wire.read();
		uint8_t value = Wire.read();
		if (ch > 0 && ch < 7 && value < 2) {
			pinMode(ch + 23, value);
			cmdResp = 0;
		}
	} else if ((cmd == VIAL_ON) && (howMany == 2)) {
		uint8_t vial = Wire.read();
		if ((vial > 0) && (vial < 17)) {
			bits = 0x00000003;
			bits = bits << ((vial - 1) * 2);
			bits |= 0x000000c0; // Turn on the dummy as well
			valves = bits;
			setValves();
			cmdResp = 0;
		}
	} else if ((cmd == VIAL_OFF) && (howMany == 2)) {
		uint8_t vial = Wire.read();
		if ((vial > 0) && (vial < 17)) {
			bits = 0x00000003;
			bits = bits << ((vial - 1) * 2);
			bits |= 0x000000c0; // Turn off the dummy as well
			// check added to make sure that the selected vial and dummy is on.
			if (valves == bits) {
				valves = 0;
				setValves();
				cmdResp = 0;
			}
		}
	} else {
		// Unknown command, flush the rest of the receive buffer
		for (int i = 1; i < howMany; i++)
			Wire.read();
	}
	interrupts();

	// Sending to serial was requested. Currently we terminate the
	if (sendSerialFlag == 1) {
		Serial.write((char *) sbuffer_tx);
		Serial.write('\r');
		sendSerialFlag = 0;
	} else if (sendSerialFlag == 2) {
		Serial1.write((char *) sbuffer_tx);
		Serial1.write('\r');
		sendSerialFlag = 0;
	}
}

// function that executes whenever data is requested by master
// this function is registered as an event, see setup()
void requestEvent() {
	uint8_t respBuffer[2];
	if ((cmd == SET_MFC) || (cmd == SET_ANALOG) || (cmd == SET_DIGITAL)
			|| (cmd == MODE_DIGITAL) || (cmd == VIAL_ON) || (cmd == VIAL_OFF)
			|| (cmd == SET_D_MFC)) {
		Wire.write(cmdResp);
	} else if ((cmd == VALVE_STATUS) || (cmd == VIAL_STATUS)) {
		Wire.write(state);
	} else if ((cmd == READ_MFC) || (cmd == READ_ANALOG)) {
		respBuffer[0] = analogReadValue & 0xff;
		respBuffer[1] = analogReadValue >> 8;
		Wire.write(respBuffer, 2);
	} else if (cmd == READ_DIGITAL) {
		Wire.write(digitalReadValue);
	} else if (cmd == READ_D_MFC) {
		// transmit back the length of the read string
		// Reading from Serial was requested but we haven't finished reading yet
		if (!doneSerialReading) {
			// Code that we have not yet read the data from our Serial
			// The buffer is smaller than 255 and we will not mistakenly send
			// a byte indicating number of bytes in the buffer by mistake.
			// This is needed as the underlying implementation of the Wire
			// library, sends a single byte of value 0, if we don't fill the
			// buffer. For us, 0 means no data reported from Serial and 255
			// serves as the code that we have not checked yet.
			Wire.write(255);
		}
		else {
			uint8_t string_length = strlen((char *) sbuffer_rx);
			Wire.write(&string_length, 1);
			// change cmd so that next time we are requested something,
			// we send the actual buffer.
			cmd = GET_D_MFC;
			doneSerialReading = false;
			inSerialReading = false;
		}
	} else if (cmd == GET_D_MFC) {
		// transmit back the actual buffer
		uint8_t string_length = strlen((char *) sbuffer_rx);
		Wire.write((uint8_t *) sbuffer_rx, string_length);
		// reset buffer
		sbuffer_rx[0] = '\0';
	}
}

void loop() {
	// A read Serial request was sent but has not been serviced yet.
	if (inSerialReading && !doneSerialReading) {
	  read_line_serial();
	}
}
