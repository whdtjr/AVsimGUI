import pathlib
import nest_asyncio
import asyncio
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
from PySide6.QtCore import QObject

from pupil_labs.realtime_api.simple import discover_one_device
from pupil_labs.realtime_api.simple import Device
from pupil_labs.realtime_api import device, StatusUpdateNotifier
import json
'''
Pupil Labs. NEON Device controller (with Automatically device discovery)
'''
APP_PATH = pathlib.Path(__file__).parent
APP_NAME = "avsim-neon" # application name

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

class NeonWindow(QWidget, Ui_neon):
    def __init__(self):
        super(NeonWindow, self).__init__()
        self.setupUi(self)

        self.eyetracker = neon_device()  # eyetracker device instance
        self.status_update()

        self.message_api_internal = {
            "flame/avsim/mapi_request_active": self._mapi_request_active
        }

        # mapi interface function (subscribe the mapi)
        self.message_api = {
            "flame/avsim/mapi_notify_active": self.mapi_notify_active,
            "flame/avsim/neon/mapi_record_start": self.mapi_record_start,
            "flame/avsim/neon/mapi_record_stop": self.mapi_record_stop
        }

        # callback function connection for menu
        self.btn_record_start.clicked.connect(self.on_click_record_start)  # scenario stop click event function
        self.btn_record_stop.clicked.connect(self.on_click_record_stop)  # scenario pause click event function

    # record start event callback
    def on_click_record_start(self):
        self.eyetracker.record_start()

    # request active notification
    def _mapi_request_active(self):
        if self.mq_client.is_connected():
            msg = {'app': APP_NAME}
            self.mq_client.publish("flame/avsim/mapi_request_active", json.dumps(msg), 0)

    # record stop event callback
    def on_click_record_stop(self):
        self.eyetracker.record_stop()

    def mapi_record_start(self, payload):
        pass

    def mapi_record_stop(self, payload):
        pass

    # MAPI for active status notification
    def mapi_notify_active(self, payload):
        if type(payload) != dict:
            print("error : payload must be dictionary type")
            return

        # # for mqtt connection
        # self.mq_client = mqtt.Client(client_id=APP_NAME, transport='tcp', protocol=mqtt.MQTTv311, clean_session=True)
        # self.mq_client.on_connect = self.on_mqtt_connect
        # self.mq_client.on_message = self.on_mqtt_message
        # self.mq_client.on_disconnect = self.on_mqtt_disconnect
        # self.mq_client.connect_async(broker_ip, port=1883, keepalive=60)
        # self.mq_client.loop_start()
    # Device status update
    def status_update(self):
        if self.eyetracker.device:
            self.label_ip_text.setText(self.eyetracker.device.address)
            self.label_name_text.setText(self.eyetracker.device.phone_name)
            self.label_battery_level_text.setText(str(self.eyetracker.device.battery_level_percent))
            self.label_battery_state_text.setText(str(self.eyetracker.device.battery_state))
            self.label_free_storage_text.setText(f"{int(self.eyetracker.device.memory_num_free_bytes/1024**3)}GB")
            self.label_storage_level_text.setText(str(self.eyetracker.device.memory_state))