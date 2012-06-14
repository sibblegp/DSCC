__author__ = 'gsibble'

from flask import Flask, jsonify, request, url_for
from tropo import Tropo
from tropo import Result as TropoResult
from tropo import Session as TropoSession


import datetime
import json

import models

APP = Flask(__name__)

#
#  Utility Functions
#

def setup_tropo():

    tropo_core = Tropo()
    tropo_core.on(event='hangup', next=url_for('handle_hangup'))
    tropo_core.on(event='error', next=url_for('handle_error'))

    return tropo_core

#
#  Web URLs
#

@APP.route('/wc', methods=['POST'])
def handle_incoming_call():
    pass

if __name__ == '__main__':
    APP.debug = True
    APP.run(host='0.0.0.0', port=5001)