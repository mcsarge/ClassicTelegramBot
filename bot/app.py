#!/usr/bin/python3

from paho.mqtt import client as mqttclient
from collections import OrderedDict
from picamera import PiCamera, Color
from telegram import Update, ChatAction
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

import json
import time
import socket
import threading
import logging
import os
import sys
from random import randint, seed
from enum import Enum
from time import time_ns, sleep
from datetime import datetime, timedelta
from fractions import Fraction
import subprocess
import sys
from functools import wraps

#Local imports
from support.validate import handleClientArgs
from support.lookups import chargeStates


# --------------------------------------------------------------------------- # 
# GLOBALS
# --------------------------------------------------------------------------- # 
MQTT_MAX_ERROR_COUNT        = 300       #Number of errors on the MQTT before the tool exits
MAIN_LOOP_SLEEP_SECS        = 5         #Seconds to sleep in the main loop

# --------------------------------------------------------------------------- # 
# Default startup values. Can be over-ridden by command line options.
# --------------------------------------------------------------------------- # 
argumentValues = { \
    'classicName':os.getenv('CLASSIC_NAME', "classic"), \
    'mqttHost':os.getenv('MQTT_HOST', "mosquitto"), \
    'mqttPort':os.getenv('MQTT_PORT', "1883"), \
    'mqttRoot':os.getenv('MQTT_ROOT', "ClassicMQTT"), \
    'mqttUser':os.getenv('MQTT_USER', "ClassicClient"), \
    'mqttPassword':os.getenv('MQTT_PASS', "ClassicClient123")}

# --------------------------------------------------------------------------- # 
# Counters and status variables
# --------------------------------------------------------------------------- # 
mqttConnected               = False
doStop                      = False

mqttErrorCount              = 0
mqttClient                  = None

msgRxTime                   = None

batTempC                    = None
batTempF                    = None
batVolts                    = None
batCurrent                  = None
chargeState                 = None
SOC                         = None
chargeStateStr              = None


#Telegram commands
commands = { 
    'start'       : 'Get this party started',
    'help'        : 'Gives you information about the available commands',
    'snap'        : 'Takes a snapshot and sends it to you. can also use /photo, /pic',
    'status'      : 'Returns some simple status about the Raspberry Pi',
    'power'       : 'Returns some information about the solar power system (future)'
}

#Telegram objects
api_key = "1728846249:AAH-xlJXMo7fSJTc2Bze4gaDaogAbHWUTKc"
#api_key = "1580653697:AAFt6RlKL2ABmCaVRWAXx0lz3uIMygDjgLs"
updater = Updater(token = api_key)
#bot = telegram.Bot(token = api_key)

# --------------------------------------------------------------------------- # 
# configure the logging
# --------------------------------------------------------------------------- # 
log = logging.getLogger('classic_telegram_bot')
if not log.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s')
    handler.setFormatter(formatter)
    log.addHandler(handler) 
    log.setLevel(os.getenv('LOGLEVEL', "DEBUG"))


# Typing animation to show to user to imitate human interaction
def send_typing_action(func):
    """Sends typing action while processing func command."""

    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        return func(update, context,  *args, **kwargs)

    return command_func

# Telegram command handlers. Error handlers also receive the raised TelegramError object in error.
@send_typing_action
def start(update: Update, context: CallbackContext):
    update.message.reply_text('Hi!')

@send_typing_action
def help_command(update: Update, context: CallbackContext):
    """Send a message when the command /help is issued."""
    help_text = "The following commands are available: \n"
    for key in commands:  # generate help text out of the commands dictionary defined at the top
        help_text += "/" + key + ": "
        help_text += commands[key] + "\n"

    update.message.reply_text(help_text)


@send_typing_action
def snap_command(update: Update, context: CallbackContext):
    """Snap an picture and sent it back"""
    #update.message.reply_text("Getting a picture...")

    #Get the photo
    camera= PiCamera()
    #camera.resolution = (1024, 768)
    camera.resolution = (640, 480)
    camera.exposure_mode='auto'
    camera.framerate = 24
    #camera.rotation = 180
    sleep(2)
    camera.annotate_background = Color('black')
    camera.annotate_text_size = 18
    camera.annotate_text = buildSolarAnnotation()
    #camera.annotate_text = dt.datetime.now().strftime('%-m/%-d/%Y %H:%M:%S')
    camera.capture('./capture.jpg')
    camera.close()

    update.message.reply_photo( photo=open('./capture.jpg', 'rb'))

@send_typing_action
def no_understand(update: Update, context: CallbackContext):
    update.message.reply_text("I don't understand \"" + update.message.text + "\"\nMaybe try the help page at /help")

@send_typing_action
def status_command(update: Update, context: CallbackContext):
    #Get the status

    # for Pi at island
    #result = subprocess.check_output(["sh","/home/pi/wittyPi/getTemp.sh"],universal_newlines=True)
    #update.message.reply_text(result)

    result=subprocess.run(["sh","/home/pi/wittyPi/getTemp.sh"], capture_output=True, text=True)
    #result=subprocess.run(["sh","/home/pi/GlaserSnap_Bot/getTemp.sh"], capture_output=True, text=True)
    update.message.reply_text(result.stdout)

@send_typing_action
def power_command(update: Update, context: CallbackContext):

    update.message.reply_text(buildPowerMessage())

# --------------------------------------------------------------------------- # 
# MQTT On Connect function
# --------------------------------------------------------------------------- # 
def on_connect(client, userdata, flags, rc):
    global mqttConnected, mqttErrorCount, mqttClient
    if rc==0:
        log.debug("MQTT connected OK Returned code={}".format(rc))
        #subscribe to the commands
        try:
            topic = "{}{}/stat/readings/#".format(argumentValues['mqttRoot'], argumentValues['classicName'])
            client.subscribe(topic)
            log.debug("Subscribed to {}".format(topic))
        except Exception as e:
            log.error("MQTT Subscribe failed")
            log.exception(e, exc_info=True)


        try:
            topic = "{}{}/stat/info/#".format(argumentValues['mqttRoot'], argumentValues['classicName'])
            client.subscribe(topic)
        except Exception as e:
            log.error("MQTT Subscribe failed")
            log.exception(e, exc_info=True)


            #publish that we are Online
            #will_topic = "{}{}/tele/LWT".format(argumentValues['mqttRoot'], argumentValues['classicName'])
            #mqttClient.publish(will_topic, "Online",  qos=0, retain=False)
        except Exception as e:
            log.error("MQTT Subscribe failed")
            log.exception(e, exc_info=True)

        mqttConnected = True
        mqttErrorCount = 0
    else:
        mqttConnected = False
        log.error("MQTT Bad connection Returned code={}".format(rc))

# --------------------------------------------------------------------------- # 
# MQTT On Disconnect
# --------------------------------------------------------------------------- # 
def on_disconnect(client, userdata, rc):
    global mqttConnected, mqttClient
    mqttConnected = False
    #if disconnetion was unexpected (not a result of a disconnect request) then log it.
    if rc!=mqttclient.MQTT_ERR_SUCCESS:
        log.debug("on_disconnect: Disconnected. ReasonCode={}".format(rc))

# --------------------------------------------------------------------------- # 
# MQTT On Message
# --------------------------------------------------------------------------- # 
def on_message(client, userdata, message):
        #print("Received message '" + str(message.payload) + "' on topic '"
        #+ message.topic + "' with QoS " + str(message.qos))

        global mqttConnected, mqttErrorCount, msgRxTime

        #got a message so we must be up again...
        mqttConnected = True 
        mqttErrorCount = 0

        #Convert the JSON message to a Python object and note the receive time
        msgRxTime = datetime.now()
        extractData(json.loads(message.payload.decode(encoding='UTF-8')))

def extractData(rxMsg):

    global batTempC, batTempF, batVolts, batCurrent, chargeState, SOC, chargeStateStr

    log.debug(rxMsg)
    batTempC = rxMsg['BatTemperature']
    batTempF = '{:.1f}'.format((batTempC * 1.8) + 32)
    batVolts = rxMsg['BatVoltage']
    batCurrent = rxMsg['WhizbangBatCurrent']
    chargeState = rxMsg['ChargeState']
    SOC = rxMsg['SOC']

    if chargeState in chargeStates:
        chargeStateStr = chargeStates[chargeState]
    else:
        chargeStateStr = "Unknown Code " + chargeState

    #write out the data...
    log.debug("Battery SOC: {}%".format(SOC))
    log.debug("Charge State: {}".format(chargeStateStr))
    log.debug("Volts: {} V".format(batVolts))
    log.debug("Current: {}A".format(batCurrent))
    log.debug("Battery Temp: {}C {}F".format(batTempC, batTempF))

# --------------------------------------------------------------------------- # 
# Data age check
# --------------------------------------------------------------------------- # 
def isDataTooOld (): 
    global msgRxTime, batVolts
    if batVolts == None:
        log.debug("No data, returning message")
        return "No data received yet."
    
    elapsedTime = datetime.now() - msgRxTime
    if elapsedTime > 1000*60*10: # 10 minutes
        log.debug("Data is old, returning message")
        return "Data has expired, check Classic connection."

    log.debug("Data is recent, returning None")
    return None

# --------------------------------------------------------------------------- # 
# Build message sent back from /power command
# --------------------------------------------------------------------------- # 
def buildPowerMessage():

    global batTempC, batTempF, batVolts, batCurrent, chargeState, SOC, chargeStateStr, msgRxTime

    msg = isDataTooOld()
    if msg != None:
        return msg
    else:

        dt_string = msgRxTime().strftime("%-m/%-d/%-Y %H:%M:%S")

        retString = "Battery SOC: {}%\n".format(SOC) + \
                    "Volts: {}V\n".format(batVolts) + \
                    "Charge State: {}\n".format(chargeStateStr) + \
                    "Current: {}A\n".format(batCurrent) + \
                    "Battery Temp: {}C/{}F\n".format(batTempC,batTempF) + \
                    "as of {}\n".format(dt_string)
        
        log.debug("Sending=" + retString)
        return retString

# --------------------------------------------------------------------------- # 
# Build message put on photo sent back
# --------------------------------------------------------------------------- # 
def buildSolarAnnotation():
    global batTempC, batTempF, batVolts, batCurrent, chargeState, SOC, chargeStateStr, msgRxTime

    msg = isDataTooOld()
    if msg != None:
        return msg
    else:
        dt_string = msgRxTime().strftime("%H:%M")

        retString = "{}%, ".format(SOC) + \
                    "{}V, ".format(batVolts) + \
                    "{}, ".format(chargeStateStr) + \
                    "{}A, ".format(batCurrent) + \
                    "Bat.Temp. {}C/{}F ".format(batTempC,batTempF) + \
                    "at {}\n".format(dt_string)
        
        log.debug("Annotating=" + retString)
        return retString



# --------------------------------------------------------------------------- # 
# Main
# --------------------------------------------------------------------------- # 
def run(argv):

    global doStop, mqttClient, mqttConnected, mqttErrorCount

    log.info("classic_mqtt_client starting up...")

    handleClientArgs(argv, argumentValues)

    #random seed from the OS
    seed(int.from_bytes( os.urandom(4), byteorder="big"))

    mqttErrorCount = 0

    #setup the MQTT Client for publishing and subscribing
    clientId = argumentValues['mqttUser'] + "_mqttclient_" + str(randint(100, 999))
    log.info("Connecting with clientId=" + clientId)
    mqttClient = mqttclient.Client(clientId) 
    mqttClient.username_pw_set(argumentValues['mqttUser'], password=argumentValues['mqttPassword'])
    mqttClient.on_connect = on_connect    
    mqttClient.on_disconnect = on_disconnect  
    mqttClient.on_message = on_message

    try:
        log.info("Connecting to MQTT {}:{}".format(argumentValues['mqttHost'], argumentValues['mqttPort']))
        mqttClient.connect(host=argumentValues['mqttHost'],port=int(argumentValues['mqttPort'])) 
    except Exception as e:
        log.error("Unable to connect to MQTT, exiting...")
        sys.exit(2)

    mqttClient.loop_start()

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler(["snap","photo","picture","pic"], snap_command))
    dispatcher.add_handler(CommandHandler("status", status_command))
    dispatcher.add_handler(CommandHandler("power", power_command))

    # on noncommand i.e message - echo the message on Telegram
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, no_understand))

    # Start the Bot
    updater.start_polling()

    log.debug("Starting main loop...")
    while not doStop:
        try:
            time.sleep(MAIN_LOOP_SLEEP_SECS)

            if not mqttConnected:
                if (mqttErrorCount > MQTT_MAX_ERROR_COUNT):
                    log.error("MQTT Error count exceeded, disconnected, exiting...")
                    doStop = True

        except KeyboardInterrupt:
            log.error("Got Keyboard Interuption, exiting...")
            doStop = True
        except Exception as e:
            log.error("Caught other exception...")
            log.exception(e, exc_info=True)
    
    log.info("Exited the main loop, stopping other loops")

    log.info("Stopping MQTT loop...")
    mqttClient.loop_stop()

    log.info("Exiting classic_mqtt_client")

if __name__ == '__main__':
    run(sys.argv[1:])
