## 실행 방법
로컬에서는 돌아가지 않고, 기계 setting이 다 되어 있는 상황에서 실행 가능


flame-avism-test 
```bash
python3 main.py
```
flame-avsim-cdlink
```bash
make run
```

## GUI 사용법

처음 페이지에서 id를 enroll하면 자신의 폴더가 만들어진다.
자신의 폴더를 더블클릭 한다.

![login](img/login.png)


그러면 전체 gui 화면이 보이는데 우선 FIle로 들어가서 scenario를 load하고 camera에서 connect all을 선택하면 전체 카메라가 켜지고 setting이 완료된다.


![full_gui](img/full_gui.png)

run을 누르면 시나리오가 시작되고 만들어진 scenario 대로 움직인다. 여기서 저장되는 위치는 코드가 저장된 위치에서 names 파일 안에 자신의 id 파일들이 있고 거기에서 camera data와 cdlink의 버튼 클릭 시간을 기록하는 csv파일이 저장된다.


## 구현되지 않은 기능
HPE model 선택 기능 : YOLO 모델 선택하여 적용
mixer의 fade in, fade out 기능
status 상태 실시간 기록 기능
