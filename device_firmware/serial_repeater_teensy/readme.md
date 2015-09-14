# teensy_serial_multicaster


This splits one USB port of a Teensy 3.1 into two RS-232 serial ports. It broadcasts messages from the USB serial
to two RS-232 serials, and forwards messages from either of RS-232 serials to the USB serial.

Importantly, there the transmit pins of the RS-232 ports are not cross-connected.


USB SERIAL >---------------> RS-232 SERIAL 1
                  |
                  |
                  ---------> RS-232 SERIAL 2


RS-232 SERIAL 1 >-------------> USB SERIAL

RS-232 SERIAL 2 >-------------> USB SERIAL

This was designed to allow users to put two addressable Alicat MFCs on a single USB serial port.