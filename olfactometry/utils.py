__author__ = 'chris'

import os
import json
import logging
import serial
from serial.tools import list_ports
import time


CONFIG_FILENAME_DEFAULT = 'C:\\voyeur_rig_config\\olfa_config.json'


def get_olfa_config(config_filename=''):
    """
    Find and parse olfactometer configuration JSON.

    :param config_filename: string with path to configuration.
    :return: returns a tuple with (config_fn, config_dict)
    :rtype: tuple
    """
    if not config_filename:
        logging.info("No olfa config file specified, looking for default in OLFA_CONFIG os variable")
        config_filename = os.environ.get("OLFA_CONFIG")
        #if it didnt find it there, it tries the legacy default
        if config_filename < 1:
            config_filename = CONFIG_FILENAME_DEFAULT
            logging.info("No OLFA_CONFIG os variable, trying with legacy default " + CONFIG_FILENAME_DEFAULT)

    if os.path.exists(config_filename):
        with open(config_filename) as f:
            config = json.load(f)
    else:
        raise Exception('No olfactometer configuration file found at {0}'.format(config_filename))

    return config_filename, config


def flatten_dictionary(dictionary, separator=':', flattened_dict=None, parent_string=''):
    """
    Flattens nested dictionary into a single dictionary:
        {'hello': {'world': 1,
                   'moon': 2}}
    becomes:
        {'hello:world': 1,
         'hello:moon': 2}

    Uses recursion to flatten as many layers as exist in your dictionary.

    :param dictionary: nested dictionary you wish to flatten.
    :param flattened_dict: (used for recursion) current flattened dictionary to add to
    :param parent_string: (used for recursion) current key string to use as prefix for
    :return: flattened dictionary
    :type dictionary: dict
    :type flattened_dict: dict
    :type parent_string: str
    :rtype: dict
    """

    if flattened_dict is None:  # dicts are mutable, so we shouldn't use a dict as the default argument!!!
        flattened_dict = {}  # instead, redeclare an empty dictionary here.
    for k, v in dictionary.iteritems():
        if parent_string:
            full_key = "{0}{1}{2}".format(parent_string, separator, k)
        else:
            full_key = k
        if isinstance(v, dict):  # use recursion to flatten and add nested dictionaries to the product.
            _ = flatten_dictionary(v, flattened_dict=flattened_dict, parent_string=full_key)
        else:
            flattened_dict[full_key] = v
    return flattened_dict


def connect_serial(port, baudrate=115200, timeout=1, writeTimeout=1):
    """
    Return Serial object after making sure that the port is accessible and that the port is expressed as a string.

    :param port: str or int (ie "COM4" or 4 for Windows).
    :param baudrate: baudrate.
    :param timeout: read timeout in seconds, default 1 sec.
    :param writeTimeout: write timeout in seconds, default 1 sec.
    :return: serial port object.
    :rtype: serial.Serial
    """

    if isinstance(port, int):
        port = "COM{0}".format(port)
    names_list = list()
    for i in list_ports.comports():
        names_list.append(i[0])
    if port not in names_list:
        print("Serial not found on {0}.".format(port))
        print('Listing current serial ports with devices:')
        for ser in list_ports.comports():
            ser_str = '\t{0}: {1}'.format(ser[0], ser[1])
            print ser_str
        time.sleep(.01)  # just to let the above lines print before the exemption is raised. cleans console output.
        raise serial.SerialException('Requested COM port: {0} is not listed as connected.'.format(port))
    else:
        return serial.Serial(port, baudrate=baudrate, timeout=timeout, writeTimeout=writeTimeout)


class OlfaException(Exception):
    pass