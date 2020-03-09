# azureiotmqtt.py
# A library for connecting to Azure IoT with Circuitpython

import adafruit_requests as requests
import adafruit_hashlib as hashlib
import adafruit_logging as logging
from adafruit_minimqtt import MQTT
import time
import base64
import hmac
import parse
import json

# -------------------- Class for handling message responses ---------------------------------------- #
class IOTCallbackInfo:
  def __init__(self, client, eventName, payload, tag, status, msgid):
    self._client = client
    self._eventName = eventName
    self._payload = payload
    self._tag = tag
    self._status = status
    self._responseCode = None
    self._responseMessage = None
    self._msgid = msgid

  def setResponse(self, responseCode, responseMessage):
    self._responseCode = responseCode
    self._responseMessage = responseMessage

  def getClient(self):
    return self._client

  def getEventName(self):
    return self._eventName

  def getPayload(self):
    return self._payload

  def getTag(self):
    return self._tag

  def getStatusCode(self):
    return self._status

  def getResponseCode(self):
    return self._responseCode

  def getResponseMessage(self):
    return self._responseMessage

  def getMessageId(self):
    return self._msgid

# -------------------- IOT specific connectiion settings ---------------------------------------- #

class IOTConnectType:
  IOTC_CONNECT_SYMM_KEY  = 1
  #IOTC_CONNECT_X509_CERT = 2

class IOTQosLevel:
  IOTC_QOS_AT_MOST_ONCE  = 0
  IOTC_QOS_AT_LEAST_ONCE = 1

class IOTLogLevel:
  IOTC_LOGGING_DISABLED =  1
  IOTC_LOGGING_API_ONLY =  2
  IOTC_LOGGING_ALL      = 16

# set global logging and QOS level
gLOG_LEVEL = IOTLogLevel.IOTC_LOGGING_ALL
gQOS_LEVEL = IOTQosLevel.IOTC_QOS_AT_MOST_ONCE

# -------------------- Start defining global functions ---------------------------------------- #

def LOG_IOTC(msg, level=IOTLogLevel.IOTC_LOGGING_API_ONLY):
  global gLOG_LEVEL
  if gLOG_LEVEL > IOTLogLevel.IOTC_LOGGING_DISABLED:
    if level <= gLOG_LEVEL:
      print(time.time(), msg)
  return 0

def MAKE_CALLBACK(client, eventName, payload, tag, status, msgid = None):
  LOG_IOTC("- iotc :: MAKE_CALLBACK :: " + eventName, IOTLogLevel.IOTC_LOGGING_ALL)
  try:
    obj = client["_events"]
  except:
    obj = client._events

  if obj != None and (eventName in obj) and obj[eventName] != None:
    cb = IOTCallbackInfo(client, eventName, payload, tag, status, msgid)
    obj[eventName](cb)
    return cb
  return 0

def _quote(a, b):
  return parse.quote(a, safe=b)


def _createMQTTClient(__self, username, passwd):
    print('User: ', username)
    print('Password: ', passwd)
    __self._mqtts = MQTT(__self.socket,
                         broker=__self._hostname,
                         username=username,
                         password=passwd,
                         network_manager=__self.network_manager,
                         port=8883,
                         keep_alive=120,
                         is_ssl=True,
                         client_id=__self._deviceId,
                         log=True)

    __self._mqtts.logger.setLevel(logging.DEBUG)

    # set actions to take throughout connection lifecycle
    __self._mqtts.on_connect = __self._onConnect
    __self._mqtts.on_message = __self._onMessage
    __self._mqtts.on_log = __self._onLog
    __self._mqtts.on_publish = __self._onPublish
    __self._mqtts.on_disconnect = __self._onDisconnect

    # initiate the connection using the adafruit_minimqtt library
    __self._mqtts.last_will()
    __self._mqtts.connect()

# function to make an http request
def _request(device, target_url, method, body, headers):
  success = False
  while not success:
    try:
      response = requests.request(method, target_url, data=body, headers=headers)
      return response.text
    except RuntimeError as e:
      print("Could not make request, retrying: ",e)
      continue # this has a tendency to enter a never-ending loop, should add more resiliency here

# -------------------- Class for the device itself ---------------------------------------- #
class Device:
  def __init__(self, scopeId, keyORCert, deviceId, credType, socket, connection, network_manager):
    self._mqtts = None
    self._loopInterval = 2
    self._mqttConnected = False
    self._deviceId = deviceId
    self._scopeId = scopeId
    self._credType  = credType
    self._hostname = None
    self._auth_response_received = None
    self._messages = {}
    self._loopTry = 0
    self._dpsEndPoint = "global.azure-devices-provisioning.net"
    self._modelData = None
    self._sslVerificiationIsEnabled = True
    self._dpsAPIVersion = "2018-11-01"
    self._addMessageTimeStamp = False
    self._exitOnError = False
    self._tokenExpires = 21600
    self._events = {
      "MessageSent": None,
      "ConnectionStatus": None,
      "Command": None,
      "SettingUpdated": None
    }
    self.socket = socket
    self.connection = connection
    self.network_manager = network_manager

    # ----- this section is only necessary if we want to add support for authenticating with a certificate file --- #
    #self._keyfile = None
    #self._certfile = None

    #if credType == IOTConnectType.IOTC_CONNECT_SYMM_KEY:
    self._keyORCert = keyORCert
    #else:
    #  self._keyfile = keyORCert["keyfile"]
    #  self._certfile = keyORCert["certfile"]

  def setLogLevel(self, logLevel):
    global gLOG_LEVEL
    if logLevel < IOTLogLevel.IOTC_LOGGING_DISABLED or logLevel > IOTLogLevel.IOTC_LOGGING_ALL:
      LOG_IOTC("ERROR: (setLogLevel) invalid argument.")
      return 1
    gLOG_LEVEL = logLevel
    return 0

  def _computeDrivedSymmetricKey(self, secret, regId):
    secret = base64.b64decode(secret)
    return base64.b64encode(hmac.new(secret, msg=regId.encode('utf8'), digestmod=hashlib.sha256).digest())

  def _loopAssign(self, operationId, headers):
    uri = "https://%s/%s/registrations/%s/operations/%s?api-version=%s" % (self._dpsEndPoint, self._scopeId, self._deviceId, operationId, self._dpsAPIVersion)
    LOG_IOTC("- iotc :: _loopAssign :: " + uri, IOTLogLevel.IOTC_LOGGING_ALL)
    target = parse.urlparse(uri)

    content = _request(self, target.geturl(), "GET", None, headers)
    try:
      data = json.loads(content.decode("utf-8"))
    except:
      try:
        data = json.loads(content)
      except Exception as e:
        err = "ERROR: %s => %s", (str(e), content)
        LOG_IOTC(err)
        return self._mqttConnect(err, None)

    if data != None and 'status' in data:
      if data['status'] == 'assigning':
        time.sleep(3)
        if self._loopTry < 20:
          self._loopTry = self._loopTry + 1
          return self._loopAssign(operationId, headers)
        else:
          LOG_IOTC("ERROR: Unable to provision the device.") # todo error code
          data = "Unable to provision the device."
          return 1
      elif data['status'] == "assigned":
        state = data['registrationState']
        self._hostName = state['assignedHub']
        return self._mqttConnect(None, self._hostName)
    else:
      data = str(data)

    return self._mqttConnect("DPS L => " + str(data), None)

  def _onConnect(self, client, userdata, _, rc):
    LOG_IOTC("- iotc :: _onConnect :: rc = " + str(rc), IOTLogLevel.IOTC_LOGGING_ALL)
    if rc == 0:
      self._mqttConnected = True
    self._auth_response_received = True

# function used for receiving an incoming desired property
  def _echoDesired(self, msg, topic):
    LOG_IOTC("- iotc :: _echoDesired :: " + topic, IOTLogLevel.IOTC_LOGGING_ALL)
    obj = None

    try:
      obj = json.loads(msg)
    except Exception as e:
      LOG_IOTC("ERROR: JSON parse for SettingsUpdated message object has failed. => " + msg + " => " + str(e))
      return

    version = None
    if 'desired' in obj:
      obj = obj['desired']

    if not '$version' in obj:
      LOG_IOTC("ERROR: Unexpected payload for settings update => " + msg)
      return 1

    version = obj['$version']

    for attr, value in obj.items():
      if attr != '$version':
        try:
          eventValue = json.loads(json.dumps(value))
          if version != None:
            eventValue['$version'] = version
        except:
          continue

        ret = MAKE_CALLBACK(self, "SettingsUpdated", json.dumps(eventValue), attr, 0)

        if not topic.startswith('$iothub/twin/res/200/?$rid=') and version != None:
          ret_code = 200
          ret_message = "completed"
          if ret.getResponseCode() != None:
            ret_code = ret.getResponseCode()
          if ret.getResponseMessage() != None:
            ret_message = ret.getResponseMessage()

          value["statusCode"] = ret_code
          value["status"] = ret_message
          value["desiredVersion"] = version
          wrapper = {}
          wrapper[attr] = value
          msg = json.dumps(wrapper)
          topic = '$iothub/twin/PATCH/properties/reported/?$rid={}'.format(int(time.time()))
          self._sendCommon(topic, msg, True)

# handles an incoming message. Could be an incoming desired property (echoDesired), a cloud to device method (command and send callback)
  def _onMessage(self, client, msg_topic, payload):
    topic = ""
    msg = None

    LOG_IOTC("- iotc :: _onMessage :: topic(" + str(msg_topic) + ") payload(" + str(payload) + ")", IOTLogLevel.IOTC_LOGGING_ALL)

    if payload != None:
      try:
        msg = payload.decode("utf-8")
      except:
        msg = str(payload)

    if msg_topic != None:
      try:
        topic = msg_topic.decode("utf-8")
      except:
        topic = str(msg_topic)

    if topic.startswith('$iothub/'): # twin
      # DO NOT need to echo twin response since IOTC api takes care of the desired messages internally
      # if topic.startswith('$iothub/twin/res/'): # twin response
      #   self._handleTwin(topic, msg)
      #
      if topic.startswith('$iothub/twin/PATCH/properties/desired/') or topic.startswith('$iothub/twin/res/200/?$rid='): # twin desired property change
        self._echoDesired(msg, topic)
      elif topic.startswith('$iothub/methods'): # C2D
        index = topic.find("$rid=")
        method_id = 1
        method_name = "None"
        if index == -1:
          LOG_IOTC("ERROR: C2D doesn't include topic id")
        else:
          method_id = topic[index + 5:]
          topic_template = "$iothub/methods/POST/"
          len_temp = len(topic_template)
          method_name = topic[len_temp:topic.find("/", len_temp + 1)]

        ret = MAKE_CALLBACK(self, "Command", msg, method_name, 0)
        ret_code = 200
        ret_message = "{}"
        if ret.getResponseCode() != None:
          ret_code = ret.getResponseCode()
        if ret.getResponseMessage() != None:
          ret_message = ret.getResponseMessage()

        next_topic = '$iothub/methods/res/{}/?$rid={}'.format(ret_code, method_id)
        LOG_IOTC("C2D: => " + next_topic + " with data " + ret_message  + " and name => " + method_name, IOTLogLevel.IOTC_LOGGING_ALL)
        self._mqtts.publish(next_topic, ret_message, qos=gQOS_LEVEL)
      else:
        if not topic.startswith('$iothub/twin/res/'): # not twin response
          LOG_IOTC('ERROR: unknown twin! {} - {}'.format(topic, msg))
    else:
      LOG_IOTC('ERROR: (unknown message) {} - {}'.format(topic, msg))

# function for logging MQTT traffic
  def _onLog(self, client, userdata, level, buf):
    global gLOG_LEVEL
    if gLOG_LEVEL > IOTLogLevel.IOTC_LOGGING_API_ONLY:
      LOG_IOTC("mqtt-log : " + buf)
    elif level <= 8:
      LOG_IOTC("mqtt-log : " + buf) # transport layer exception
      if self._exitOnError:
        sys.exit()

# gracefully handle disconnects
  def _onDisconnect(self, client, userdata, rc):
    LOG_IOTC("- iotc :: _onDisconnect :: rc = " + str(rc), IOTLogLevel.IOTC_LOGGING_ALL)
    self._auth_response_received = True

    if rc == 5:
      LOG_IOTC("on(disconnect) : Not authorized")
      self.disconnect()

    if rc == 1:
      self._mqttConnected = False

    if rc != 5:
      MAKE_CALLBACK(self, "ConnectionStatus", userdata, "", rc)

  def _onPublish(self, client, data, topic, msgid):
    LOG_IOTC("- iotc :: _onPublish :: " + str(data), IOTLogLevel.IOTC_LOGGING_ALL)
    if data == None:
      data = ""

    if msgid != None and (str(msgid) in self._messages) and self._messages[str(msgid)] != None:
      MAKE_CALLBACK(self, "MessageSent", self._messages[str(msgid)], data, 0)
      if (str(msgid) in self._messages):
        del self._messages[str(msgid)]

  def _sendCommon(self, topic, data):
    self._mqtts.publish(topic, data, qos=gQOS_LEVEL)
    return 0

  def sendProperty(self, data):
    LOG_IOTC("- iotc :: sendProperty :: " + data, IOTLogLevel.IOTC_LOGGING_ALL)
    topic = '$iothub/twin/PATCH/properties/reported/?$rid={}'.format(int(self.connection.get_time()))
    return self._sendCommon(topic, data)
  
  def sendTelemetry(self, data, systemProperties = None):
    LOG_IOTC("- iotc :: sendTelemetry :: " + data, IOTLogLevel.IOTC_LOGGING_ALL)
    topic = 'devices/{}/messages/events/'.format(self._deviceId)

    if systemProperties != None:
      firstProp = True
      for prop in systemProperties:
        if not firstProp:
          topic += "&"
        else:
          firstProp = False
        topic += prop + '=' + str(systemProperties[prop])

    return self._sendCommon(topic, data)

# abstract types of telemetry sent (state changes and events)
  def sendState(self, data):
    return self.sendTelemetry(data)

  def sendEvent(self, data):
    return self.sendTelemetry(data)


  def disconnect(self):
    if not self.isConnected():
      return

    LOG_IOTC("- iotc :: disconnect :: ", IOTLogLevel.IOTC_LOGGING_ALL)
    self._mqttConnected = False
    self._mqtts.disconnect()
    return 0

  def on(self, eventName, callback):
    self._events[eventName] = callback
    return 0

  def _gen_sas_token(self, hub_host, device_name, key):
    token_expiry = int(self.connection.get_time() + self._tokenExpires)
    uri = hub_host + "%2Fdevices%2F" + device_name
    signed_hmac_sha256 = self._computeDrivedSymmetricKey(key, uri + "\n" + str(token_expiry))
    signature = _quote(signed_hmac_sha256, '~()*!.\'')
    if signature.endswith('\n'):  # somewhere along the crypto chain a newline is inserted
      signature = signature[:-1]
    token = 'SharedAccessSignature sr={}&sig={}&se={}'.format(uri, signature, token_expiry)
    return token

  def _mqttConnect(self, err, hostname):
    if err != None:
      LOG_IOTC("ERROR : (_mqttConnect) " + str(err))
      return 1

    LOG_IOTC("- iotc :: _mqttConnect :: " + hostname, IOTLogLevel.IOTC_LOGGING_ALL)

    self._hostname = hostname
    passwd = None

    username = '{}/{}/api-version=2016-11-14'.format(self._hostname, self._deviceId)
    if self._credType == IOTConnectType.IOTC_CONNECT_SYMM_KEY:
      passwd = self._gen_sas_token(self._hostname, self._deviceId, self._keyORCert)

    _createMQTTClient(self, username, passwd)

    LOG_IOTC(" - iotc :: _mqttconnect :: created mqtt client. connecting..", IOTLogLevel.IOTC_LOGGING_ALL)
    while self._auth_response_received == None:
      self.doNext()
    LOG_IOTC(" - iotc :: _mqttconnect :: on_connect must be fired. Connected ? " + str(self.isConnected()), IOTLogLevel.IOTC_LOGGING_ALL)
    if not self.isConnected():
      return 1
    else:
      self._mqttConnected = True
      self._auth_response_received = True

    self._mqtts.subscribe('devices/{}/messages/events/#'.format(self._deviceId))
    self._mqtts.subscribe('devices/{}/messages/deviceBound/#'.format(self._deviceId))
    self._mqtts.subscribe('$iothub/twin/PATCH/properties/desired/#') # twin desired property changes
    self._mqtts.subscribe('$iothub/twin/res/#') # twin properties response
    self._mqtts.subscribe('$iothub/methods/#')

    if self.getDeviceSettings() == 0:
      MAKE_CALLBACK(self, "ConnectionStatus", None, None, 0)
    else:
      return 1

    return 0

  def getDeviceSettings(self):
    LOG_IOTC("- iotc :: getDeviceSettings :: ", IOTLogLevel.IOTC_LOGGING_ALL)
    self.doNext()
    return self._sendCommon("$iothub/twin/GET/?$rid=0", " ")

  def connect(self, hostName = None):
    LOG_IOTC("- iotc :: connect :: ", IOTLogLevel.IOTC_LOGGING_ALL)

    if hostName != None:
      self._hostName = hostName
      return self._mqttConnect(None, self._hostName)

    expires = int(self.connection.get_time() + self._tokenExpires)
    authString = None
    
    if self._credType == IOTConnectType.IOTC_CONNECT_SYMM_KEY:
      sr = self._scopeId + "%2Fregistrations%2F" + self._deviceId
      sigNoEncode = self._computeDrivedSymmetricKey(self._keyORCert, sr + "\n" + str(expires))
      sigEncoded = _quote(sigNoEncode, '~()*!.\'')
      authString = "SharedAccessSignature sr=" + sr + "&sig=" + sigEncoded + "&se=" + str(expires) + "&skn=registration"

    headers = {
      "content-type": "application/json; charset=utf-8",
      "user-agent": "iot-central-client/1.0",
      "Accept": "*/*"
    }

    if authString != None:
      headers["authorization"] = authString

    if self._modelData != None:
      body = "{\"registrationId\":\"%s\",\"data\":%s}" % (self._deviceId, json.dumps(self._modelData))
    else:
      body = "{\"registrationId\":\"%s\"}" % (self._deviceId)

    uri = "https://%s/%s/registrations/%s/register?api-version=%s" % (self._dpsEndPoint, self._scopeId, self._deviceId, self._dpsAPIVersion)
    target = parse.urlparse(uri)

    LOG_IOTC('Connecting...', IOTLogLevel.IOTC_LOGGING_API_ONLY)
    content = _request(self, target.geturl(), "PUT", body, headers)

    LOG_IOTC('Connection request made...', IOTLogLevel.IOTC_LOGGING_API_ONLY)

    data = None
    try:
      data = json.loads(content.decode("utf-8"))
    except:
      try:
        data = json.loads(content)
      except Exception as e:
        err = "ERROR: non JSON is received from %s => %s .. message : %s", (self._dpsEndPoint, content, str(e))
        LOG_IOTC(err)
        return self._mqttConnect(err, None)

    if 'errorCode' in data:
      err = "DPS => " + str(data)
      return self._mqttConnect(err, None)
    else:
      time.sleep(1)
      return self._loopAssign(data['operationId'], headers)

  def isConnected(self):
    return self._mqttConnected

# listen for messages
  def doNext(self, idleTime=1):
    if not self.isConnected():
      return

    self._mqtts.loop()
    time.sleep(idleTime)

# ------------------------------------ END OF DEVICE CLASS ------------------------------------- #
