import time
import _thread
from base.PinConn import PIR
from base.measureTemp import BME
import socket
import urllib3
import struct
import requests, json
from network import Sigfox
import socket

# init Sigfox for RCZ1 (Europe)
sigfox = Sigfox(mode=Sigfox.SIGFOX, rcz=Sigfox.RCZ1)

# create a Sigfox socket
s = socket.socket(socket.AF_SIGFOX, socket.SOCK_RAW)

# make the socket blocking
s.setblocking(True)

# configure it as uplink (Disabled downlink for now)
s.setsockopt(socket.SOL_SIGFOX, socket.SO_RX, False)

# PIR (Output to pin 13 (G5))
pir = PIR('G5')
_thread.start_new_thread(pir.run_pir, ())

# BME680 (Output to Pin 9 and 10 (G16 and G17))
bme = BME(('P9', 'P10'))

while True:
    # Get the movement count since last time (Currently once / hour)
    count_last_hour = pir.get_count_last_h()

    # Get air condition values
    temp, humidity, pressure, air_quality = bme.get_values()

    # Print all
    print(temp, humidity, pressure, air_quality, count_last_hour)

    # Prepare the data by packing it before sending it to sigfox

    # Payload format is: >bBHHH where
    # b = Temperature (1 byte, 8 bits, signed) Range: -128 to 127
    # B = Humidity (1 byte, 8 bits, unsigned) Range: 0 to 255
    # H = Pressure (2 bytes, 16 bits, unsigned) Range: 0 to 65,535
    # B = Air Quality (2 byte, 16 bits, unsigned) Range: 0 to 65,535
    # I = Movement last hour (2 bytes, 16 bits, unsigned) Range: 0 to 65,535
    package = struct.pack('>bBHHH', int(temp), int(humidity), int(pressure), int(air_quality), int(count_last_hour))

    # Send the data to sigfox backend
    s.send(package)

    # Sleep for 60 minutes
    time.sleep(3600)


ssl_private_key_filepath = 'rsa_private.pem'
ssl_algorithm = 'RS256' # Either RS256 or ES256
root_cert_filepath = 'roots.pem'
project_id = 'analog-period-235204'
gcp_location = 'us-central1'
#gcp_location = 'us-central1'
registry_id = 'my-registry'
device_id = 'my-device'

# end of user-variables

cur_time = datetime.datetime.utcnow()

def create_jwt():
  token = {
      'iat': cur_time,
      'exp': cur_time + datetime.timedelta(minutes=60),
      'aud': project_id
  }

  with open(ssl_private_key_filepath, 'r') as f:
    private_key = f.read()

  return jwt.encode(token, private_key, ssl_algorithm)

_CLIENT_ID = 'projects/{}/locations/{}/registries/{}/devices/{}'.format(project_id, gcp_location, registry_id, device_id)
_MQTT_TOPIC = '/devices/{}/events'.format(device_id)

client = mqtt.Client(client_id=_CLIENT_ID)
# authorization is handled purely with JWT, no user/pass, so username can be whatever
client.username_pw_set(
    username='unused',
    password=create_jwt())

def error_str(rc):
    return '{}: {}'.format(rc, mqtt.error_string(rc))

def on_disconnect(unusued_client, unused_userdata, unused_flags, rc):
    print('on_connect', error_str(rc))
    
def on_connect(unusued_client, unused_userdata, unused_flags, rc):
    print('on_connect', error_str(rc))

def on_publish(unused_client, unused_userdata, unused_mid):
    print('on_publish')

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_publish = on_publish

client.tls_set(ca_certs=root_cert_filepath) # Replace this with 3rd party cert if that was used when creating registry
client.connect('mqtt.googleapis.com', 8883)
client.loop_start()

# Could set this granularity to whatever we want based on device, monitoring needs, etc
temperature = 0
humidity = 0
pressure = 0

#sense = SenseHat()

#for i in range(1, 2):   #1,11
while True:
  #cur_temp = sense.get_temperature()
  #cur_pressure = sense.get_pressure()
  #cur_humidity = sense.get_humidity()
  cur_temp = random.randint(10,55)
  cur_pressure = random.randint(100,200)
  cur_humidity = random.randint(30,80)
  
  #if cur_temp == temperature and cur_humidity == humidity and cur_pressure == pressure:
  #  time.sleep(1)
  #  continue

  temperature = cur_temp
  pressure = cur_pressure
  humidity = cur_humidity

  payload = '{{ "ts": {}, "temperature": {}, "pressure": {}, "humidity": {} }}'.format(int(time.time()), temperature, pressure, humidity)

  # Uncomment following line when ready to publish
  client.publish(_MQTT_TOPIC, payload, qos=1)

  print("{}\n".format(payload))

  time.sleep(60)

client.loop_stop()