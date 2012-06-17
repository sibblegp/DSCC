__author__ = 'gsibble'

from flask import Flask, jsonify, request, url_for
from tropo import Tropo
from tropo import Result as TropoResult
from tropo import Session as TropoSession

import datetime
import json
import random

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

def error(error):
    return jsonify({'error':error})

#
#  API Calls
#

@APP.route('/dscc/api/setup_call', methods=['POST'])
def setup_conference():

    APP.logger.debug('Received Incoming Call Request...')

    APP.logger.debug('%%%%%%%\n' + str(request.json) + '\n%%%%%%%')

    if request.method == 'POST':
        try:
            initiator_number = request.json['initiator']['number']
            initiator_name = request.json['initiator']['name']
            members = request.json['members']
        except KeyError:
            return error('Invalid JSON elements.')

        #Record Initiator
        APP.logger.debug('Creating Initiator Record...')
        new_initiator = models.ConferenceInitiator(name=initiator_name, number=initiator_number)
        new_initiator.save()

        #Create Conference Call
        APP.logger.debug('Creating New Call Record...')
        tropo_conference_id = 0
        clashing_conference_id = False
        while clashing_conference_id == False:
            tropo_conference_id = random.randint(1, 128)
            clashing_conference_id = models.ConferenceCall.check_id_available(tropo_conference_id)

        dial_in_number = '+16504161940'
        new_call = models.ConferenceCall(tropo_conference_id=tropo_conference_id, dial_in_number=dial_in_number, initiator=new_initiator)
        new_call.save()

        for member in members:
            pass

        response = dict()
        response['dial_in'] = dial_in_number
        response['conference_id'] = tropo_conference_id

        return jsonify(response)
    else:
        return error('GET NOT PUSH!!  DUMBASS.')


#
#  Tropo Web URLs
#

@APP.route('/dscc', methods=['POST'])
def handle_incoming_initiator_call():
    tropo_core = setup_tropo()
    tropo_request = TropoSession(request.data)

    session_data = dict()

    session_data['id'] = tropo_request.id
    session_data['callid'] = tropo_request.callId
    session_data['from'] = tropo_request.fromaddress['id']
    session_data['to'] = tropo_request.to['id']

    tropo_core.say('Welcome to Dead Simple Conference Calling.')
    tropo_core.on(event='continue', next=url_for('connect_conference'))
    response = tropo_core.RenderJson(pretty=True)

    session = models.TropoSession(tropo_session_id=tropo_request.id)
    session.tropo_call_id = tropo_request.callId
    session.from_number = tropo_request.fromaddress['id']

    session.incoming_number = tropo_request.to['id']
    session.initiator_session = True
    session.save()

    return response

@APP.route('/dscc/conference', methods=['POST'])
def connect_conference():
    tropo_core = setup_tropo()
    result = TropoResult(request.data)
    session = models.TropoSession.get_session_with_tropo_id(result._sessionId)

    conference = models.ConferenceCall.get_current_call_for_number(session.from_number)

    if conference:
        tropo_core.say("PLease wait while we connect your other parties.")
        #Initiate Calls and send their redirects to appropriate handler
        access_token = 'd5f6314d8f9e1804b9a00f83c9007247'

        for member in conference.members:
            tropo_core.call(to=member.number)

        tropo_core.on(event='answer', next=url_for('handle_member'))
        tropo_core.conference(id=conference.tropo_conference_id)
    else:
        tropo_core.say("We're sorry, but we cannot find an active conference call for your number.  Goodbye.")
        tropo_core.hangup()

    response = tropo_core.RenderJson(pretty=True)
    return response

@APP.route('/dscc/call_member', methods=['POST'])
def handle_member():
    tropo_core = setup_tropo()
    tropo_request = TropoSession(request.data)

    session_data = dict()

    session_data['id'] = tropo_request.id
    session_data['callid'] = tropo_request.callId
    session_data['from'] = tropo_request.fromaddress['id']
    session_data['to'] = tropo_request.to['id']

    tropo_core.say('Welcome to Dead Simple Conference Calling.')
    tropo_core.on(event='continue', next=url_for('connect_conference'))
    response = tropo_core.RenderJson(pretty=True)

    session = models.TropoSession(tropo_session_id=tropo_request.id)
    session.tropo_call_id = tropo_request.callId
    session.from_number = tropo_request.fromaddress['id']

    session.incoming_number = tropo_request.to['id']
    session.initiator_session = True
    session.save()

    return response

@APP.route('/dscc/error', methods=['POST'])
def handle_error():
    tropo_core = setup_tropo()

    tropo_core.say('Sorry, we have encountered an error.')
    tropo_core.hangup()

    response = tropo_core.RenderJson(pretty=True)

    return response

@APP.route('/dscc/hangup', methods=['POST'])
def handle_hangup():
    pass

if __name__ == '__main__':
    APP.debug = True
    APP.run(host='0.0.0.0', port=5001)