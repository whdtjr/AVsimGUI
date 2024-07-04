import sys
import pathlib
import nest_asyncio
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QMessageBox,QFileDialog
from PySide6.QtGui import QPixmap, QCloseEvent, QStandardItemModel,QStandardItem, QColor
from PySide6.QtCore import Qt
from integration import Ui_MainWindow# scenario select gui
from MainWindow import Ui_MainWindow as mainGUI
import argparse
import neon
import camWindow
import manager


#common data parsing
parser = argparse.ArgumentParser()
parser.add_argument('--broker', nargs='?', required=False, help="Broker IP Address", default="127.0.0.1")
parser.add_argument('--config', nargs='?', required=False, help="Configuration File(*.cfg)", default="param.cfg")
args = parser.parse_args()

broker_ip_address = ""
configure = {}
if args.broker is not None:
    broker_ip_address = args.broker
if args.config is not None:
    _config_name = args.config
    configure = {
        "camera_ids":[0,2,4,6],
        "camera_windows_map":{
            0:"window_camera_1",
            2:"window_camera_2",
            4:"window_camera_3",
            6:"window_camera_4"
        }
    }

APP_PATH = pathlib.Path(__file__).parent
APP_NAME = "avsim_test"

# 시나리오 목록을 받아와서 리스트에 넣어두기
scenario_list = ['1', '2']

class MainGUI(QMainWindow, mainGUI):
    
    def __init__(self):
        super(MainGUI, self).__init__()
        self.setupUi(self)

        # manager table name 
        self.scenario_table_columns = ["Time(s)", "MAPI", "Message"]
        self.coapp_table_columns = ["App", "Active", "Status"]

        callbacks = {
            'show_on_statusbar': self.show_on_statusbar,
            'update_frame': self.update_camera_frame,
            'show_error_message': self.show_error_message,
            'mark_row_color' : self._mark_row_color,
            'mark_row_reset' : self._mark_row_reset,
            'mark_inactive' : self._mark_inactive,
            'mark_active': self._mark_active,
            'open_scenario_file' : self.
        }
        #neon도 callback을 매개변수로 넣어줘서 전달할 수 있음
        self.neonController = neon.neonController(broker_ip=broker_ip_address)
        self.neonController.set_status_callback(self.show_on_statusbar)

        self.cameraWindow = camWindow.CameraWindow(broker_ip_address=broker_ip_address, config=configure, callbacks=callbacks)
        self.manageWindow = manager.AVSimManager(broker_ip=broker_ip_address, callbacks=callbacks)

        #manager settings
        # scenario model for scenario table
        self.scenario_model = QStandardItemModel()
        self.scenario_model.setColumnCount(len(self.scenario_table_columns))
        self.scenario_model.setHorizontalHeaderLabels(self.scenario_table_columns)
        self.table_scenario_contents.setModel(self.scenario_model)
        # status model for coapp table
        self.coapp_model = QStandardItemModel()
        self.coapp_model.setColumnCount(len(self.coapp_table_columns))
        self.coapp_model.setHorizontalHeaderLabels(self.coapp_table_columns)
        self.table_coapp_status.setModel(self.coapp_model)
        coapps = ["avsim-cam", "avsim-cdlink", "avsim-neon", "avsim-carla", "avsim-mixer"]
        for row, app in enumerate(coapps):
            self.coapp_model.appendRow([QStandardItem(app), QStandardItem("-"), QStandardItem("-")])
            self.coapp_model.item(row, 0).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        # initialize for default
        for app_row in range(self.coapp_model.rowCount()):
            self._mark_inactive(app_row)
        

        # main gui functions
        self.btn_scenario_run.clicked.connect(self.record_start)
        self.btn_scenario_stop.clicked.connect(self.record_stop)
        self.btn_scenario_pause.clicked.connect(self.record_pause)
        # cam gui functions
        self.actionExit.triggered.connect(self.closeEvent)
        self.actionCapture_img_png.triggered.connect(self.cameraWindow.on_select_capture_image)
        self.action_capture_after_10s.triggered.connect(self.cameraWindow.on_select_capture_after_10s)
        self.action_capture_after_20s.triggered.connect(self.cameraWindow.on_select_capture_after_20s)
        self.action_capture_after_30s.triggered.connect(self.cameraWindow.on_select_capture_after_30s)
        self.actionconnect_All.triggered.connect(self.cameraWindow.on_select_connect_all)
        # manager gui functions
        self.btn_scenario_reload.clicked.connect(self.manageWindow.scenario_reload)
        self.btn_scenario_save.clicked.connect(self.manageWindow.scenario_save)
        #neon functions
        self.update_neon_status()


        

    # camera, glass, manager record all together
    def record_start(self):
        self.neonController.on_click_record_start() # neon record
        self.cameraWindow.on_select_start_data_recording() # cam record
        self.manageWindow.api_run_scenario() # manage start

    def record_stop(self):
        self.neonController.on_click_record_stop()
        self.cameraWindow.on_select_stop_data_recording()
        self.manageWindow.api_stop_scenario()
        
    def record_pause(self):
        self.neonController.on_click_record_stop() # neon은 record pause가 없음..
        self.cameraWindow.on_select_stop_data_recording() # camera record pause가 없음..
        self.manageWindow.api_pause_scenario() # manager는 pause가 존재
    
    # neon
    def update_neon_status(self):
        eyetracker_device = self.neonController.eyetracker.device 
        if eyetracker_device:
            self.label_ip_text.setText(eyetracker_device.address)
            self.label_ip_text.setText(eyetracker_device.phone_name)
            self.label_name_text.setText(eyetracker_device.phone_name)
            self.label_battery_level_text.setText(str(eyetracker_device.battery_level_percent))
            self.label_battery_state_text.setText(str(eyetracker_device.battery_state))
            self.label_free_storage_text.setText(f"{int(eyetracker_device.memory_num_free_bytes/1024**3)}GB")
            self.label_storage_level_text.setText(str(eyetracker_device.memory_state))
    # camera
    def update_camera_frame(self, image, camera_id):
        pixmap = QPixmap.fromImage(image)
        try:
            window = self.findChild(QLabel, configure["camera_windows_map"][camera_id])
            window.setPixmap(pixmap.scaled(window.size(), Qt.AspectRatioMode.KeepAspectRatio))
        except Exception as e:
            print(e)
    # common callback
    def show_error_message(self, title, message):
        QMessageBox.critical(self, title, message)
        
    def show_on_statusbar(self, text):
        self.statusBar().showMessage(text)

    # manager callback
    

    
    # manager draw functions
    # mark inactive
    def _mark_inactive(self, row):
        self.coapp_model.item(row, 1).setBackground(QColor(255,0,0,100))
        self.coapp_model.item(row, 1).setText("INACTIVE")
        self.coapp_model.item(row, 1).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    # mark active
    def _mark_active(self, row):
        self.coapp_model.item(row, 1).setBackground(QColor(0,255,0,100))
        self.coapp_model.item(row, 1).setText("ACTIVE")
        self.coapp_model.item(row, 1).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    
     # change row background color
    def _mark_row_color(self, row):
        for col in range(self.scenario_model.columnCount()):
            self.scenario_model.item(row,col).setBackground(QColor(255,0,0,100))
    
    # reset all rows background color
    def _mark_row_reset(self):
        for col in range(self.scenario_model.columnCount()):
            for row in range(self.scenario_model.rowCount()):
                self.scenario_model.item(row,col).setBackground(QColor(0,0,0,0))


    # 캠 키고 끄려고 하면 제대로 꺼지지 않음,, 
    def closeEvent(self, event:QCloseEvent) -> None: 
        self.neonController.close()
        self.cameraWindow.close()
        self.close()
        return super().closeEvent(event)



class Integration(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(Integration, self).__init__()
        self.setupUi(self)
        self.pushButton.clicked.connect(self.scenario_start)
        self.pushButton_2.clicked.connect(self.scenario_start)
        
        self.mainGUI = None

    def openMainGUI(self):
        if self.mainGUI is None:
            self.mainGUI = MainGUI()
        self.mainGUI.show()

    def scenario_start(self):
        sender = self.sender()  # 이벤트를 발생시킨 객체를 가져옵니다.
        if sender == self.pushButton: # 시나리오 1번 실행 cam, manager, glass 실행
            self.openMainGUI()
        elif sender == self.pushButton_2:
            print(scenario_list[1])
    
    def closeEvent(self, event:QCloseEvent):
        if self.mainGUI:
            self.mainGUI.close()
        super().closeEvent(event)

if __name__ == "__main__":

    nest_asyncio.apply()
    app = QApplication(sys.argv)
    
    window = Integration()
    window.show()
    sys.exit(app.exec())