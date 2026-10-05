# 배달로봇 ROS2 프로젝트

실제 하드웨어 연결 전, 가짜 로봇·STM32·ESP32로
배송 제어와 경로 추종을 시험하는 프로젝트입니다.

## 개발 환경

- Ubuntu 24.04
- ROS2 Jazzy
- Python / ament_python

## 현재 구현 및 가상 시험 완료

- 배송 상태머신
- 가짜 STM32·ESP32 명령 및 응답
- 도착 상태 + 주행 정지 확인 후 리프트·잠금 해제 허용
- 통신 오류 및 정지 응답 시간 초과 시 ESTOP
- 주행 감지 시 리프트 정지 명령 전송
- 여러 waypoint 순차 이동 및 최종 도착 판정
- 가짜 장애물 신호에 따른 정지 및 명시적 재개
- 다섯 노드 통합 launch

## 빌드 및 실행

ROS2 Jazzy가 설치된 환경에서 실행합니다.

실행 터미널:

```bash
cd ~/delivery_robot_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select delivery_robot_control delivery_robot_follow
source install/setup.bash
ros2 launch delivery_robot_control mock_system.launch.py
```

실행 터미널은 계속 켜둡니다.
Ctrl + C를 누르면 다섯 노드가 함께 종료됩니다.

별도의 명령 터미널:

```bash
source /opt/ros/jazzy/setup.bash
source ~/delivery_robot_ws/install/setup.bash
ros2 node list
```

다음 노드가 각각 하나씩 보여야 합니다.

- /control_subscriber
- /mock_stm32
- /mock_esp32
- /mock_robot
- /waypoint_follower

## 경로 이동 시험

새 launch 실행 시 위치는 (0, 0)에서 시작합니다.
경로는 (1, 0) → (1, 1) → (0, 1)입니다.

```bash
ros2 topic pub --once /mock_follow_command std_msgs/msg/String "{data: 'START'}"
```

마지막 지점 도착 후 ARRIVED 전환과
STM32 주행 정지 확인 로그를 확인합니다.

반복 시험은 launch를 Ctrl + C로 종료한 뒤
다시 실행하여 위치와 배송 상태를 초기화합니다.

## 장애물 정지 및 재개 시험

경로 이동 중 장애물 신호를 보냅니다.

```bash
ros2 topic pub --once /mock_obstacle std_msgs/msg/Bool "{data: true}"
```

장애물이 남아 있으면 RESUME은 차단됩니다.
장애물을 제거해도 자동 출발하지 않습니다.

```bash
ros2 topic pub --once /mock_obstacle std_msgs/msg/Bool "{data: false}"
ros2 topic pub --once /mock_follow_command std_msgs/msg/String "{data: 'RESUME'}"
```

## 리프트 시험

최종 도착 및 STM32 주행 정지 확인 후 실행합니다.

```bash
ros2 topic pub --once /payload_command std_msgs/msg/String "{data: 'LIFT_UP'}"
```

가짜 ESP32는 5초 뒤 완료 응답을 보냅니다.

## 아직 구현·검증이 필요한 부분

- 실제 STM32·ESP32 통신 및 보드 자체 watchdog
- 실제 구동계·조향과 위치 추정
- LiDAR 기반 장애물 감지
- 배송 상태와 주행 시작 허용 조건의 통합
- 실제 리프트 위치·리미트 및 정지 확인
- GUI 및 실제 하드웨어 반복 시험

현재 시험 결과는 가상 환경 기준이며,
실제 모터 동작과 센서 기반 안전 검증은 포함하지 않습니다.