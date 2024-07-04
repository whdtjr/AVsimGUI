from pupil_labs.realtime_api.simple import discover_one_device
from pupil_labs.realtime_api import device
import asyncio

class neon_device():
    def __init__(self):
        super().__init__()
        self.device = asyncio.run(self.device_discover())
        
    def __delattr__(self, __name: str) -> None:
        print("closing..")
        #self.close() # device close

    # device discover
    async def device_discover(self):
        return discover_one_device(max_search_duration_seconds=5)
    
    # device close
    def close(self):
        try:
            
            if self.device:
                self.device.close()
                print("Neon device is closed")
        except RuntimeError as e:
            print(f"Runtime Error : {e}")
    
    # recording start
    def record_start(self):
        if self.device:
            try:
                record_id = self.device.recording_start()
                print("start recording")
                print(record_id)
            except device.DeviceError as e:
                print(f"Device Error : {e}")

    # recording stop
    def record_stop(self):
        if self.device:
            try:
                ret = self.device.recording_stop_and_save()
                print("stop recording")
                print(ret)
            except device.DeviceError as e:
                print(f"Device Error : {e}")

'''
Flame AVSim Pupil-Labs Neon Control S/W
@author Byunghun Hwang<bh.hwang@iae.re.kr>
'''


import pathlib
import json


import paho.mqtt.client as mqtt

from pupil_labs.realtime_api.simple import discover_one_device
from pupil_labs.realtime_api import device



WORKING_PATH = pathlib.Path(__file__).parent # working path
APP_UI = WORKING_PATH / "MainWindow.ui" # Qt-based UI file
APP_NAME = "avsim-neon" # application name

'''
Pupil Labs. NEON Device controller (with Automatically device discovery)
'''
class neon_device():
    def __init__(self):
        super().__init__()
        self.device = asyncio.run(self.device_discover())
        
    def __delattr__(self, __name: str) -> None:
        print("closing..")
        #self.close() # device close

    # device discover
    async def device_discover(self):
        return discover_one_device(max_search_duration_seconds=5)
    
    # device close
    def close(self):
        try:
            
            if self.device:
                self.device.close()
                print("Neon device is closed")
        except RuntimeError as e:
            print(f"Runtime Error : {e}")
    
    # recording start
    def record_start(self):
        if self.device:
            try:
                record_id = self.device.recording_start()
                print("start recording")
                print(record_id)
            except device.DeviceError as e:
                print(f"Device Error : {e}")

    # recording stop
    def record_stop(self):
        if self.device:
            try:
                ret = self.device.recording_stop_and_save()
                print("stop recording")
                print(ret)
            except device.DeviceError as e:
                print(f"Device Error : {e}")


class neonController():
    def __init__(self, broker_ip:str):
        super().__init__()

        self.eyetracker = neon_device() # eyetracker device instance
        
        self.status_callback = None

        self.message_api_internal = {
            "flame/avsim/mapi_request_active" : self._mapi_request_active
        }
        
        # mapi interface function (subscribe the mapi)
        self.message_api = {
            "flame/avsim/mapi_notify_active" : self.mapi_notify_active,
            "flame/avsim/neon/mapi_record_start" : self.mapi_record_start,
            "flame/avsim/neon/mapi_record_stop" : self.mapi_record_stop
        }
        
        # for mqtt connection
        self.mq_client = mqtt.Client(client_id=APP_NAME, transport='tcp', protocol=mqtt.MQTTv311, clean_session=True)
        self.mq_client.on_connect = self.on_mqtt_connect
        self.mq_client.on_message = self.on_mqtt_message
        self.mq_client.on_disconnect = self.on_mqtt_disconnect
        self.mq_client.connect_async(broker_ip, port=1883, keepalive=60)
        self.mq_client.loop_start()

    def set_status_callback(self, callback):
        self.status_callback = callback

    def show_on_statusbar(self, text):
        if self.status_callback:
            self.status_callback(text)
        else:
            print(text)


    # record start event callback
    def on_click_record_start(self):
        self.eyetracker.record_start()

    # record stop event callback
    def on_click_record_stop(self):
        self.eyetracker.record_stop()
        
    def mapi_record_start(self, payload):
        pass
    
    def mapi_record_stop(self, payload):
        pass    
                
    # request active notification
    def _mapi_request_active(self):
        if self.mq_client.is_connected():
            msg = {'app':APP_NAME}
            self.mq_client.publish("flame/avsim/mapi_request_active", json.dumps(msg), 0)
    
    # MAPI for active status notification
    def mapi_notify_active(self, payload):
        if type(payload)!= dict:
            print("error : payload must be dictionary type")
            return
        
        active_key = "active"
        if active_key in payload.keys():
            active_value = payload[active_key] # boolean
            # find row
            for row in range(self.coapp_model.rowCount()):
                if self.coapp_model.index(row, 0).data() == payload["app"]:
                    # update item data
                    if active_value == True:
                        self._mark_active(row)
                    else:
                        self._mark_inactive(row)
                    break
        

    def close(self):
        if self.eyetracker:
            self.eyetracker.close()
        if self.mq_client:
            self.mq_client.loop_stop()
            self.mq_client.disconnect()
        print("neon controller resources released")
    
    # mqtt connection callback
    def on_mqtt_connect(self, mqttc, obj, flags, rc):
        # subscribe message api
        for topic in self.message_api.keys():
            self.mq_client.subscribe(topic, 0)
        
        self.show_on_statusbar("Connected to Broker({})".format(str(rc)))

    # mqtt disconnection callback
    def on_mqtt_disconnect(self, mqttc, userdata, rc):
        self.show_on_statusbar("Disconnected to Broker({})".format(str(rc)))
    


    # mqtt message receive callback
    def on_mqtt_message(self, mqttc, userdata, msg):
        mapi = str(msg.topic)
        
        try:
            if mapi in self.message_api.keys():
                payload = json.loads(msg.payload)
                if "app" not in payload:
                    print("message payload does not contain the app")
                    return
                
                if payload["app"] != APP_NAME:
                    self.message_api[mapi](payload)
            else:
                print("Unknown MAPI was called :", mapi)

        except json.JSONDecodeError as e:
            print("MAPI Message payload cannot be converted")
            

