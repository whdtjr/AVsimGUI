'''
Flame AVSim S/W Manager Application
@author Byunghun Hwang<bh.hwang@iae.re.kr>
'''

import sys, os
import typing
from PyQt6 import QtGui
import pathlib
import json
from PyQt6.QtGui import QImage, QPixmap, QCloseEvent, QStandardItem, QStandardItemModel, QIcon, QColor
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableView, QLabel, QPushButton, QMessageBox
from PyQt6.QtWidgets import QFileDialog
from PyQt6.uic import loadUi
from PyQt6.QtCore import QModelIndex, QObject, Qt, QTimer, QThread, pyqtSignal, QAbstractTableModel
import timeit
import paho.mqtt.client as mqtt
from datetime import datetime
import csv
import math
import argparse

WORKING_PATH = pathlib.Path(__file__).parent # working path
APP_UI = WORKING_PATH / "MainWindow.ui" # Qt-based UI file
APP_NAME = "avsim-manager" # application name

'''
scenario execution thread
'''
class ScenarioRunner(QTimer):

    scenario_act_slot = pyqtSignal(float, str, str) #arguments : time_key, mapi, message
    scenario_end_slot = pyqtSignal()

    def __init__(self, interval_ms):
        super().__init__()
        self.time_interval = interval_ms # default interval_ms = 100ms
        self.setInterval(interval_ms)
        self.timeout.connect(self.on_timeout_callback) # timer callback
        self.current_time_idx = 0  # time index
        self.scenario_container = {} # scenario data container
        
        self._end_time = 0.0
    
    # reset all params    
    def initialize(self):
        self.current_time_idx = 0
        self.scenario_container.clear()
        
    # scenario running callback by timeout event
    def on_timeout_callback(self):
        time_key = round(self.current_time_idx, 1)
        if self._end_time<self.current_time_idx:
            self.scenario_end_slot.emit()
        else:
            if time_key in self.scenario_container.keys():
                for msg in self.scenario_container[time_key]:
                    self.scenario_act_slot.emit(time_key, msg["mapi"], msg["message"])
            
        self.current_time_idx += self.time_interval/1000 # update time index
    
    # open & load scenario file
    def load_scenario(self, scenario:dict) -> bool:
        self.stop_scenario() # if timer is running, stop the scenario runner

        if len(scenario)<1:
            print("> Empty Scenario. Please check your scenario")
            return False
        
        try:
            if "scenario" in scenario:
                for scene in scenario["scenario"]:
                    self.scenario_container[scene["time"]] = [] # time indexed container
                    for event in scene["event"]: # for every events
                        self.scenario_container[scene["time"]].append(event) # append event
            self._end_time = max(list(self.scenario_container.keys()))

        except json.JSONDecodeError as e:
            print("JSON Decode error", str(e))
            return False

        return True
    
    # start timer
    def run_scenario(self):
        if self.isActive(): # if the timer is now active(=running)
            self.stop() # stop the timer
        self.start() # then restart the timer
    
    # stop timer
    def stop_scenario(self):
        self.current_time_idx = 0 # timer index set 0
        self.stop() # timer stop
        
    # pause timer
    def pause_scenario(self):
        self.stop() # stop the timer, but timer index does not set 0

'''
Main window
'''
class AVSimManager():
    def __init__(self, broker_ip:str, callbacks):
        super().__init__()
        self.callbacks = callbacks
        self.message_api_internal = {
            "flame/avsim/mapi_request_active" : self._mapi_request_active
        }
        
        # mapi interface function (subscribe the mapi)
        self.message_api = {
            "flame/avsim/mapi_notify_active" : self.mapi_notify_active,
            "flame/avsim/mapi_nofity_status" : self.mapi_notify_status
        }

         
        # for mqtt connection
        self.mq_client = mqtt.Client(client_id=APP_NAME, transport='tcp', protocol=mqtt.MQTTv311, clean_session=True)
        self.mq_client.on_connect = self.on_mqtt_connect
        self.mq_client.on_message = self.on_mqtt_message
        self.mq_client.on_disconnect = self.on_mqtt_disconnect
        self.mq_client.connect_async(broker_ip, port=1883, keepalive=60)
        self.mq_client.loop_start()
    
        # runner instance (with time interval value, 100ms)
        self.runner = ScenarioRunner(interval_ms=100)
        self.runner.scenario_act_slot.connect(self.do_process)
        self.runner.scenario_end_slot.connect(self.end_process)
        
        self.scenario_filepath = ""
        
        
    def _mark_row_color(self, row):
        if self.callbacks.get('mark_row_color'):
            self.callbacks['mark_row_color'](row)

    def _mark_row_reset(self):
        if self.callbacks.get('mark_row_reset'):
            self.callbacks['mark_row_reset']()

    def _mark_inactive(self, row):
        if self.callbacks.get('mark_inactive'):
            self.callbacks['mark_inactive'](row)

    def _mark_active(self, row):
        if self.callbacks.get('mark_active'):
            self.callbacks['mark_active'](row)

    def show_on_statusbar(self, text):
        if self.callbacks.get('show_on_statusbar'):
            self.callbacks['show_on_statusbar'](text)

    def open_scenario_file(self):
        if self.callbacks.get('open_scenario_file'):
            return self.callbacks['open_scenario_file']()

    def load_scenario(self, scenario_data):
        if self.callbacks.get('clear_scenario_model'):
            self.callbacks['clear_scenario_model']()
        if "scenario" in scenario_data:
            for data in scenario_data["scenario"]:
                for event in data["event"]:
                    if self.callbacks.get('append_scenario_row'):
                        self.callbacks['append_scenario_row'](str(data["time"]), event["mapi"], event["message"])


    # open & load scenario file    
    def open_scenario_file(self):
        selected_file = QFileDialog.getOpenFileName(self, 'Open scenario file', './')
        if selected_file[0]:
            sfile = open(selected_file[0], "r")
            self.scenario_filepath = selected_file[0]
            
            with sfile:
                try:
                    scenario_data = json.load(sfile)
                except Exception as e:
                    QMessageBox.critical(self, "Error", "Scenario file read error {}".format(str(e)))
                    
                # parse scenario file
                self.runner.load_scenario(scenario_data)
                self.scenario_model.setRowCount(0)
                if "scenario" in scenario_data:
                    for data in scenario_data["scenario"]:
                        for event in data["event"]:
                            self.scenario_model.appendRow([QStandardItem(str(data["time"])), QStandardItem(event["mapi"]), QStandardItem(event["message"])])

                # table view column width resizing
                self.table_scenario_contents.resizeColumnsToContents()
            

                
    
    
    # scenario reload
    def scenario_reload(self):
        if self.scenario_filepath:
            sfile = open(self.scenario_filepath, "r")
            with sfile:
                try:
                    # init
                    self.scenario_model.clear()
                    self.runner.initialize()
                    
                    # reload
                    scenario_data = json.load(sfile)
                except Exception as e:
                    QMessageBox.critical(self, "Error", "Scenario file read error {}".format(str(e)))
                    
                # parse scenario file
                self.runner.load_scenario(scenario_data)
                self.scenario_model.setRowCount(0)
                if "scenario" in scenario_data:
                    for data in scenario_data["scenario"]:
                        for event in data["event"]:
                            self.scenario_model.appendRow([QStandardItem(str(data["time"])), QStandardItem(event["mapi"]), QStandardItem(event["message"])])

                # table view column width resizing
                self.table_scenario_contents.resizeColumnsToContents()
                
                self.show_on_statusbar("Scenario is reloaded")
        
    def scenario_save(self):
        print("Not implemented yet.")
        self.show_on_statusbar("Scenario is updated")
                
    # run scenario with timer
    def api_run_scenario(self):
        self._mark_row_reset()
        self.runner.run_scenario()
        self.show_on_statusbar("Scenario runner is running...")

    # end of scenario
    def api_end_scenario(self):
        self.runner.stop_scenario()
        self.show_on_statusbar("Scenario runner works done")
        QMessageBox.information(self, "Info", "Scenario runner works done")
    
    # stop scenario with timer
    def api_stop_scenario(self):
        self.runner.stop_scenario()
        self.show_on_statusbar("Scenario runner is stopped")
    
    # pause scenario with timer
    def api_pause_scenario(self):
        self.runner.pause_scenario()
        self.show_on_statusbar("Scenario runner is paused")
    
    # message api implemented function
    def do_process(self, time, mapi, message):
        message.replace("'", "\"")
        self.mq_client.publish(mapi, message, 0) # publish mapi interface

        self._mark_row_reset()
        for row in range(self.scenario_model.rowCount()):
            if time == float(self.scenario_model.item(row, 0).text()):
                self._mark_row_color(row)

    # end process
    def end_process(self):
        self.api_end_scenario()
        
                
    # request active notification
    def _mapi_request_active(self):
        if self.mq_client.is_connected():
            msg = {"app":APP_NAME}
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
        
     
    def mapi_notify_status(self, payload):
        pass
                
    # show message on status bar
    def show_on_statusbar(self, text):
        self.statusBar().showMessage(text)
    

    # close event callback function by user
    def closeEvent(self, a0: QCloseEvent) -> None:
        self.api_stop_scenario()

        return super().closeEvent(a0)
    
    # MQTT callbacks
    def on_mqtt_connect(self, mqttc, obj, flags, rc):
        # subscribe message api
        for topic in self.message_api.keys():
            self.mq_client.subscribe(topic, 0)
        
        self.show_on_statusbar("Connected to Broker({})".format(str(rc)))
        
    def on_mqtt_disconnect(self, mqttc, userdata, rc):
        self.show_on_statusbar("Disconnected to Broker({})".format(str(rc)))
        
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
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--broker', nargs='?', required=False, help="Broker Address")
    args = parser.parse_args()

    broker_address = "127.0.0.1"
    if args.broker is not None:
        broker_address = args.broker
    
    app = QApplication(sys.argv)
    window = AVSimManager(broker_ip=broker_address)
    window.show()
    sys.exit(app.exec())