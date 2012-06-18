__author__ = 'gsibble'

from flask import Flask, jsonify, request, url_for
from tropo import Tropo
from tropo import Result as TropoResult
from tropo import Session as TropoSession
from tropo import Choices as TropoChoices

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

def makeChoices(value):
    return TropoChoices(value=value, mode='dtmf')

def error(error):
    return jsonify({'error':error})

#
#  API Calls
#

@APP.route('/dscc/api/setup_call', methods=['POST'])
def setup_conference():

    APP.logger.debug('Received Incoming Call Request...')

    #APP.logger.debug('%%%%%%%\n' + str(request.json) + '\n%%%%%%%')

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

        dial_in_number = '+14153266627'
        new_call = models.ConferenceCall(tropo_conference_id=tropo_conference_id, dial_in_number=dial_in_number, initiator=new_initiator)
        new_call.save()

        for member in members:
            new_member = models.ConferenceMember(name=member['name'], number=member['number'])
            new_member.save()
            new_call.members.append(new_member)
            new_call.save()


        response = dict()
        response['dial_in'] = dial_in_number
        response['conference_id'] = tropo_conference_id

        APP.logger.debug('Created conference %i' % tropo_conference_id)

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

    APP.logger.debug('Incoming call....')
    APP.logger.debug('Call Data: ' + str(tropo_request))

    initiator_call = False

    if hasattr(tropo_request, 'parameters'):
        #The call is an outgoing call to a member
        initiator_call = False
    else:
        #The call is an incoming initiator
        initiator_call = True
        #session_data['id'] = tropo_request.id
        #session_data['callid'] = tropo_request.callId
        #session_data['from'] = tropo_request.fromaddress['id']
        #session_data['to'] = tropo_request.to['id']

    if initiator_call:
        APP.logger.debug('Call identified for initiator %s' % tropo_request.fromaddress['id'])
        tropo_core.say('Hello and welcome to a Simple Conference Call.')
        tropo_core.on(event='continue', next=url_for('connect_conference'))
        session = models.TropoSession(tropo_session_id=tropo_request.id)
        session.tropo_call_id = tropo_request.callId
        session.member_number = '+1' + tropo_request.fromaddress['id']
        #session.incoming_number = tropo_request.to['id']
        session.initiator_session = True
    else:
        session = models.TropoSession(tropo_session_id=tropo_request.id)
        session.member_number = '+1' + tropo_request.parameters['member_number']
        session.save()

        conference = models.ConferenceCall.get_current_call_for_member(session.member_number)

        if conference:
            APP.logger.debug('Adding member %s to conference %s...' % session.member_number, conference.id)
            session.conference_call = conference
            session.save()
            tropo_core.call(to=session.member_number, allowSignals=True, _from=conference.initiator.number, timeout=90)
            tropo_core.on(event="continue", next=url_for('member_answered'))
        else:
            APP.logger.debug('No active conference found for member: ' + session.member_number)
            tropo_core.hangup()


    response = tropo_core.RenderJson(pretty=True)
    session.save()

    return response

@APP.route('/dscc/conference', methods=['POST'])
def connect_conference():
    tropo_core = setup_tropo()
    result = TropoResult(request.data)
    session = models.TropoSession.get_session_with_tropo_id(result._sessionId)

    conference = models.ConferenceCall.get_current_call_for_initiator(session.member_number)

    if conference:
        session.conference_call = conference
        session.save()
        tropo_core.say("PLease wait while we connect your other parties.")

        #Initiate Calls and send their redirects to appropriate handler
        for member in conference.members:
            #Kick off sessions
            pass

        #tropo_core.on(event='answer', next=url_for('handle_member'))
        tropo_core.conference(id=str(conference.tropo_conference_id), name=str(conference.tropo_conference_id), allowSignals=True, required=True)
    else:
        tropo_core.say("We're sorry, but we cannot find an active conference call for your number.  Goodbye.")
        tropo_core.hangup()

    response = tropo_core.RenderJson(pretty=True)
    return response

@APP.route('/dscc/call_member', methods=['POST'])
def call_member():
    tropo_core = setup_tropo()
    result = TropoResult(request.data)
    session = models.TropoSession.get_session_with_tropo_id(result._sessionId)

    conference = models.ConferenceCall.get_current_call_for_member(session.member_number)

    if conference:
        session.conference_call = conference
        session.save()
        tropo_core.call(to=session.member_number, allowSignals=True, _from=conference.initiator.number, timeout=90)
        tropo_core.on(event="answer", next=url_for('member_answered'))
    else:
        APP.logger.debug('No active conference found for member: ' + session.member_number)

    response = tropo_core.RenderJson(pretty=True)
    return response

@APP.route('/dscc/member_answer', methods=['POST'])
def member_answered():
    tropo_core = setup_tropo()
    result = TropoResult(request.data)
    session = models.TropoSession.get_session_with_tropo_id(result._sessionId)
    conference = session.conference_call

    tropo_core.say("Hello and welcome to a simple conference call. " +  conference.initiator.name + "has initiated this call to you.")
    tropo_core.ask(say='Press one to join the conference or two to decline.', choices=makeChoices('[1 DIGIT]'), attempts=2)
    tropo_core.on(event='continue', next=url_for('member_question'))

    response = tropo_core.RenderJson(pretty=True)
    return response

@APP.route('/dscc/member_question', methods=['POST'])
def member_question():
    tropo_core = setup_tropo()
    result = TropoResult(request.data)
    session = models.TropoSession.get_session_with_tropo_id(result._sessionId)
    conference = session.conference_call

    selection = int(result.getValue())

    if selection == 1:
        tropo_core.say("Please wait while we join you to the conference")
        tropo_core.conference(id=str(conference.tropo_conference_id), name=str(conference.tropo_conference_id), allowSignals=True, required=True)
        tropo_core.on(event='continue', next=url_for('member_joined'))
    elif selection == 2:
        tropo_core.say("Thank you.  Goodbye.")
        tropo_core.hangup()
    else:
        tropo_core.on(event='continue', next=url_for('member_answered'))

    response = tropo_core.RenderJson(pretty=True)
    return response

@APP.route('/dscc/member_joined', methods=['POST'])
def member_joined():
    APP.logger.debug('Member joined conference...')

    tropo_core.say("Welcome to the conference.  Enjoy.")
    response = tropo_core.RenderJson(pretty=True)
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
    return {}

if __name__ == '__main__':
    APP.debug = True
    APP.run(host='0.0.0.0', port=5001)