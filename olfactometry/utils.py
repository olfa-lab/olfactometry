__author__ = 'chris'

import os
import json
import logging


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


class OlfaException(Exception):
    pass