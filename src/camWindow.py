'''
In-cabin camera monitor & data extractor window class
@Author bh.hwang@iae.re.kr
'''

import pathlib
import paho.mqtt.client as mqtt
from PySide6.QtWidgets import QProgressBar
from PySide6.QtCore import QObject, Slot
from camera import CameraController
# from machine import MachineMonitor
import json

# pre-defined options
WORKING_PATH = pathlib.Path(__file__).parent
APP_NAME = "avsim-cam"



# for message APIs
mqtt_topic_manager = "flame/avsim/manager"


'''
Main window
'''
class CameraWindow(QObject):
    def __init__(self, broker_ip_address, config:dict, callbacks):
        super().__init__()

        self.configure_param = config
        self.opened_camera = {}
        self.machine_monitor = None
        self.is_machine_running = False
        self.message_api = {
            "flame/avsim/cam/mapi_record_start" : self.mapi_record_start,
            "flame/avsim/cam/mapi_record_stop" : self.mapi_record_stop,
            "flame/avsim/mapi_request_active" : self.mapi_notify_active #response directly
        }
        
        self.callbacks = callbacks

        # for mqtt connection
        self.mq_client = mqtt.Client(client_id=APP_NAME,transport='tcp',protocol=mqtt.MQTTv311, clean_session=True)
        self.mq_client.on_connect = self.on_mqtt_connect
        self.mq_client.on_message = self.on_mqtt_message
        self.mq_client.on_disconnect = self.on_mqtt_disconnect
        self.mq_client.connect_async(broker_ip_address, port=1883, keepalive=60)
        self.mq_client.loop_start()

        # for gpu resource monitoring
        # self.machine_monitor = MachineMonitor(1000)
        # self.machine_monitor.gpu_monitor_slot.connect(self.gpu_monitor_update)
        # self.machine_monitor.start()

    # camera open after show this GUI
    def start_monitor(self):
        if self.is_machine_running:
            if self.callbacks.get('show_error_message'):
                self.callbacks['show_error_message']("Already Running", "This Machine is already working...")
            return
        
        # for camera monitoring
        for id in self.configure_param["camera_ids"]:
            camera = CameraController(id)
            if camera.open():
                self.opened_camera[id] = camera
                self.opened_camera[id].image_frame_slot.connect(self.update_frame)
            else:
                self.callbacks['show_error_messgae']("No Camera", "No Camera device connection")

        for camera in self.opened_camera.values():
            camera.begin()
    
    # internal api for starting record
    def _api_record_start(self):
        for camera in self.opened_camera.values():
            print(f"Recording start...({camera.camera_id})")
            camera.start_recording()
        self.show_on_statusbar("Start Recording...")
    
    # internal api for stopping record
    def _api_record_stop(self):
        for camera in self.opened_camera.values():
            print(f"Recording stop...({camera.camera_id})")
            camera.stop_recording()
        self.show_on_statusbar("Stopped Recording...")
        
    # capture image
    def _api_capture_image(self, delay_s:int):
        for camera in self.opened_camera.values():
            camera.start_capturing(delay_s)
        self.show_on_statusbar(f"Captured image after {delay_s} second(s)")

    def _api_capture_image_keypoints(self):
        for camera in self.opened_camera.values():
            camera.start_capturing(delay=0)
    
    # on_select event for starting record
    def on_select_start_data_recording(self):
        self._api_record_start()
    
    # on_select event for stopping record
    def on_select_stop_data_recording(self):
        self._api_record_stop()
        
    # on_select event for capturing to image
    def on_select_capture_image(self):
        self._api_capture_image(0)
    def on_select_capture_after_10s(self):
        self._api_capture_image(10)
    def on_select_capture_after_20s(self):
        self._api_capture_image(20)
    def on_select_capture_after_30s(self):
        self._api_capture_image(30)

    def on_select_capture_with_keypoints(self):
        self._api_capture_image_keypoints()
    
    # connect all camera and show on display continuously
    def on_select_connect_all(self):
        self.start_monitor()
                
    # mapi : record start
    def mapi_record_start(self, payload):
        self._api_record_start()

    # mapi : record stop
    def mapi_record_stop(self, payload):
        self._api_record_stop()
                
    # show message on status bar
    def show_on_statusbar(self, text):
        if self.callbacks.get('show_on_statusbar'):
            self.callbacks['show_on_statusbar'](text)
        else:
            print(text)
        
    

    # update image frame on label area
    def update_frame(self, image, camera_id):
        if self.callbacks.get('update_frame'):
            self.callbacks['update_frame'](image, camera_id)
    
    # gpu monitoring update
    def gpu_monitor_update(self, status:dict):
        gpu_usage_window = self.findChild(QProgressBar, "progress_gpu_usage")
        gpu_memory_usage_window = self.findChild(QProgressBar, "progress_gpu_mem_usage")
        gpu_usage_window.setValue(status["gpu_usage"])
        gpu_memory_usage_window.setValue(status["gpu_memory_usage"])

    # close event callback function by user
    def close(self):
        for device in self.opened_camera.values():
            device.close()

        # if self.machine_monitor!=None:
        #     self.machine_monitor.close()

        
    
    # notification
    def mapi_notify_active(self):
        if self.mq_client.is_connected():
            msg = {"app":APP_NAME, "active":True}
            self.mq_client.publish(mqtt_topic_manager, json.dumps(msg), 0)
        else:
            self.show_on_statusbar("Notified")
    
    # mqtt connection callback function
    def on_mqtt_connect(self, mqttc, obj, flags, rc):
        self.mapi_notify_active()
        
        # subscribe message api
        for topic in self.message_api.keys():
            self.mq_client.subscribe(topic, 0)
        
        self.show_on_statusbar("Connected to Broker({})".format(str(rc)))
    
    # mqtt disconnection callback function
    def on_mqtt_disconnect(self, mqttc, userdata, rc):
        self.show_on_statusbar("Disconnected to Broker({})".format(str(rc)))
    
    # mqtt message receive callback function
    def on_mqtt_message(self, mqttc, userdata, msg):
        mapi = str(msg.topic)
        
        try:
            if mapi in self.message_api.keys():
                payload = json.loads(msg.payload)
                if "app" not in payload:
                    print("Message payload does not contain the app")
                    return
                
                if payload["app"] != APP_NAME:
                    self.message_api[mapi](payload)
            else:
                print("Unknown MAPI was called : {}".format(mapi))
        except json.JSONDecodeError as e:
            print("MAPI message payload connot be converted : {}".format(str(e)))
        