import sys
import pathlib
import nest_asyncio
from PySide6.QtWidgets import QApplication, QMainWindow
from integration import Ui_MainWindow# scenario select gui
from MainWindow import Ui_MainWindow as mainGUI
import argparse
import neon

# neon data
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

        self.neonController = neon.neonController(broker_ip=broker_ip_address)

        self.btn_scenario_run.connect(self.record_start)
        self.btn_scenario_stop.connect(self.record_stop)
        self.btn_scenario_pause.connect(self.record_pause)

        

    # camera, glass, manager record all together
    def record_start(self):
        self.neonController.on_click_record_start()
        pass
    def record_stop(self):
        self.neonController.on_click_record_stop()
        pass
    def record_pause(self):
        self.neonController.on_click_record_stop() # neon은 record pause가 없음..
        pass


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
    
    def closeEvent(self, event):
        if self.neonWindow:
            self.neonWindow.close()
        super().closeEvent(event)

if __name__ == "__main__":

    nest_asyncio.apply()
    app = QApplication(sys.argv)
    
    window = Integration()
    window.show()
    sys.exit(app.exec())