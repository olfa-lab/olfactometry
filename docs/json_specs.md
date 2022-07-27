# Olfactometer configuration JSON.

A JSON structured text file provides the specs for olfactometry devices. This file is read by the Olfactometers class
and is used to configure devices and build the olfactometer gui based on the devices present and their specs.

This is imported and propagated through the Olfactometry package as a raw python object (dict) once it is read. This
means that adding new specifications for future devices is extremely straightforward. Adding objects to this JSON will
not break current functionality, and these objects can be easily addressed in the configuration dictionary.

While it is not currently used, this file is also writable using the json package. So, modules can edit this to change
configuration information programmatically. Until this is implemented, I recommend installing JSONedit:
http://tomeko.net/software/JSONedit/

## Basic Structure

1.Olfactometers
    1. Olfactometer #1
        1. *olfa specs*
        2. MFCs (list)
            1. MFC 1
            2. MFC 2
        3. Dilutors (list)
            1. Dilutor 1
        4. Vials (object)
            1. Vial 1
            2. Vial 2
    2. Olfactometer #2
        1. ...




### Olfactometers
The configuration file is a JSON object (like a python dict). It contains a list of Olfactometers.

### Olfactometer:
An Olfactometer is a JSON object with the following attributes. Most of these are specific to the teensy olfactometer.
If another type of olfa is created, it can remove or add required attributes as needed.

1. interface. This is the type of olfactometer. This will be "teensy" until someone makes a new type of olfactometer.
2. com_port. Where to communicate. Integer
3. slave_index. This is the device ID for the olfactometer. It is usually 1.

### MFCs
MFCs are always nested within an olfactometer object or a dilutor object. They use their parent devices communication
protocol to actually make contact with the MFC.
1. MFC_type: this is the type of interface.
2. capacity: the capacity in SCCM for the MFC device
3. gas: they type of gas. Mainly used for naming.

For alicat_digital_arduino MFCs, the following additional attributes are required:
1. address: This is the address of the MFC. This is set on the Alicat.
2. arduino_port_number: This is the address that the arduino uses. It is specific to the port (RJ-45) that the MFC is
plugged in to on the arduino board.

### Dilutors
Dilutors are specified as a list. While Dilutors can be stand alone devices (ie they could be used to dilute 2 olfactometers),
they are usually nested within olfactometer objects.

1. dilutor_type: currently this should be "serial_forwarding"
2. com_port: com port where the dilutor is attached (integer)
3. MFCs: these are MFCs typically "alicat_digital_raw", as there is no olfactometer layer, just forwarded serial commands

### Vials
These are what hold your odors. They are always nested within Olfactometer objects under a Vials heading. Each object
a name that is string specifying the number of the vial. It is a string because JSON insists that names are strings.

1. odor: string specifying the odor contained in the vial
2. conc: floating point number specifying the concentration of the odor in the vial.
3. status_str: (optional) this gives a specific string for the vial to be displayed as a status tip for the vial. Usually
the tip is defined by the odor and concentration.

## Example

```json

{
  "Olfactometers": [
    {
      "interface": "teensy",
      "com_port": 4,
      "master_sn": 212,
      "cassette_1_sn": 1222,
      "cassette_2_sn": 1234,
      "cleandate": 20140101,
      "slave_index": 1,


      "MFCs": [
        {
          "MFC_type": "alicat_digital",
          "capacity": 100,
          "arduino_port_num": 2,
          "address": "A",
          "gas": "Nitrogen"
        }
      ],

      "Dilutors": [
        {
          "dilutor_type": "serial_forwarding",
          "com_port": 11,
          "MFCs": [
            {
              "MFC_type": "alicat_digital_raw",
              "capacity": 2000,
              "address": "A",
              "gas": "vac"
            },
            {
              "MFC_type": "alicat_digital_raw",
              "capacity": 2000,
              "address": "B",
              "gas": "Air"
            }
          ]
        }
      ],


      "Vials": {
        "4": {
          "odor": "dummy",
          "conc": 0
        },
        "5": {
          "odor": "a(+)-pinene",
          "conc": 0.01
        },
        "6": {
          "odor": "amyl acetate",
          "conc": 0.01
        },
        "7": {
          "odor": "2-hydroxy acetophenone",
          "conc": 0.01
        },
        "8": {
          "odor": "ethyl tiglate",
          "conc": 0.01
        },
        "9": {
          "odor": "menthone",
          "conc": 0.01
        },
        "10": {
          "odor": "acetophenone",
          "conc": 0.01
        },
        "11": {
          "odor": "heptaldehyde",
          "conc": 0.01
        },
        "12": {
          "odor": "R(+)-limonene",
          "conc": 0.01
        }
      }

    }
  ]
}
```