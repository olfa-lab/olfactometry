# Device firmwares

This contains software to run devices related to olfactometry.

### Teensy_olfactometer
Janelia/Admir's creation. An extensible olfactometer that uses a teensy for serial communication with PC. This is
served using the "Teensy" class in the olfactometer module.

### Serial_repeater_teensy (dilutor)
A simple teensy repeater that broadcasts PC commands to 2 serial ports. This is used by the Dilutor class to address 2
MFCs concurrently.