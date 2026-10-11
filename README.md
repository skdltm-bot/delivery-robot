# 배달로봇 ROS2 프로젝트

Raspberry Pi 4에서 ROS2 Jazzy 기반 상위제어를 수행하고,
STM32는 주행·조향, ESP32는 리프트·잠금·LED를 담당하는 배달로봇 프로젝트입니다.
현재 저장소는 상위제어와 MCU 통신 브리지, 가짜 로봇·STM32·ESP32를 이용한
배송 제어 및 경로 추종 시험 코드를 포함합니다.

**ROS2 상태머신·안전 정지 및 통신의 Mock 테스트는 진행했으나,
실제 하드웨어 통신과 자율주행팀 연동은 아직 미검증입니다.**
Mock 시험 결과를 실제 모터·센서 동작이나 현장 안전 검증 완료로 해석하지 않습니다.

문서 기준 코드: [`3467874`](https://github.com/skdltm-bot/delivery-robot/commit/346787401bd48afe982b5537a83ec07631878004)
(`Update ROS2 control and MCU bridge`, 2026-10-11).
이 커밋에는 `stm32_serial_bridge.py` 추가, `control_subscriber.py` 및
브리지 `setup.py` 수정, 백업 파일 추가가 포함됩니다.

## 개발 환경

- 상위제어 대상: Raspberry Pi 4
- Ubuntu 24.04
- ROS2 Jazzy
- Python / ament_python

## 아키텍처 및 패키지 역할

| 구성 | 역할 | 현재 코드와 검증 범위 |
| --- | --- | --- |
| Raspberry Pi 4 / ROS2 Jazzy | 배송 상태 판단, 명령 허용 조건, 안전 정지 요청, MCU 통신 | Python 상위제어 구현, Mock 시험 진행. 실제 Raspberry Pi와 보드 연결 검증은 별도 필요 |
| STM32 | 주행·조향 제어 | ROS2 시리얼 브리지 구현. MCU 펌웨어·실제 주행·조향 검증은 이 저장소에 포함되지 않음 |
| ESP32 | 리프트·적재함 잠금·앞/뒤 LED 제어 | ROS2 시리얼 브리지와 Mock 응답 구현. MCU 펌웨어·실제 액추에이터 검증은 이 저장소에 포함되지 않음 |
| 자율주행팀 | 실제 위치 추정·경로 계획·장애물 감지 연동 | 현재는 Mock 위치와 waypoint 추종 사용. 팀 간 인터페이스 합의 및 통합 시험 필요 |

- `delivery_robot_control`: `control_subscriber`, 배송 상태머신, ROS2 노드형 `mock_stm32`·`mock_esp32`, 통합 Mock launch.
- `delivery_robot_follow`: `waypoint_follower`, `mock_robot`, 시험용 `navigation_publisher`.
- `delivery_robot_bridge`: `stm32_serial_bridge`·`esp32_serial_bridge` 실행 진입점.
  기존 `command_subscriber.py`와 브리지 내부 `mock_stm32.py`는 이전 Mock 통신 코드이며,
  현재 `setup.py`의 실행 진입점과 통합 launch에 등록되어 있지 않습니다.
  `*_backup.py`도 현재 실행 대상이 아닙니다.

실제 보드 연결을 위한 코드 경로는 다음과 같습니다. 실제 연결 성공을 뜻하지 않습니다.

```text
자율주행 상태 → /navigation_status → control_subscriber
                                      ├─ /control_command → stm32_serial_bridge → STM32 (주행·조향)
                                      │                     └─ /stm32_status → 상위제어
                                      └─ /esp32_command → esp32_serial_bridge → ESP32 (리프트·잠금·LED)
                                                            └─ /esp32_status → 상위제어
시리얼 입출력 오류 → /bridge_status → 상위제어의 ESTOP 및 정지 명령
```

현재 waypoint 추종의 속도 명령은 `/mock_cmd_vel`로 `mock_robot`에만 전달됩니다.
이 속도 명령을 STM32의 실제 주행·조향 명령으로 변환하는 경로는 아직 없습니다.

## 현재 구현 및 Mock 시험 현황

다음 항목은 구현되어 있으며 기존 개발 과정에서 가상 시험을 진행한 범위입니다.
모든 항목에 대한 자동 회귀 테스트나 실제 보드 검증 완료를 의미하지 않습니다.

- 배송 상태머신
- 가짜 STM32·ESP32 명령 및 응답
- 도착 상태 + 주행 정지 확인 후 리프트·잠금 해제 허용
- 통신 오류 및 정지 응답 시간 초과 시 ESTOP
- 주행 감지 시 리프트 정지 명령 전송
- 여러 waypoint 순차 이동 및 최종 도착 판정
- 가짜 장애물 신호에 따른 정지 및 명시적 재개
- 다섯 노드 통합 launch

### 상태머신과 안전 로직의 범위

- 기본 흐름: `IDLE → DELIVERING → ARRIVED`. 장애물 정지는 `OBSTACLE_STOP`,
  주행 실패는 `FAILED`, 통신 오류 또는 도착 정지 응답 시간 초과는 `ESTOP`으로 처리합니다.
- `GOAL_REACHED` 수신 시 `STOP`을 전송하고, 현재 도착 정지 요청에 대한
  `DRIVE_STOPPED` 응답을 받은 뒤에만 `LIFT_UP`·`LIFT_DOWN`·`UNLOCK`을 허용합니다.
  정지 응답 제한은 3초입니다.
- `DRIVE_MOVING` 수신 시 정지 확인을 해제하고 `LIFT_STOP`을 전송합니다.
  `COMM_TIMEOUT`·`COMM_FAILED` 수신 또는 정지 응답 시간 초과 시 `STOP`과 `LIFT_STOP`을 전송합니다.
- `COMPLETE` 전이는 상태머신에 있지만, 현재 `control_subscriber`에는 해당 이벤트를
  발생시키는 입력이 없습니다. `/control_reset`의 `RESET`은 `COMPLETE`·`FAILED`·`ESTOP`에서만 허용됩니다.
- waypoint 추종은 최신 위치가 없으면 시작·재개를 차단하고, 주행 중 위치 수신이
  0.5초를 넘겨 끊기면 정지 및 `FAILED`를 발행합니다.
  `mock_robot`도 속도 명령이 0.5초 넘게 없으면 이동을 중단합니다. 이 감시는 실제 MCU watchdog이 아닙니다.
- 현재 경로 추종의 `START`·`RESUME`은 배송 상태머신의 허가를 받는 구조가 아닙니다.
  ESTOP 이후 임의 재출발을 막는 통합 조건은 남은 작업입니다.

### 현재 ROS2 인터페이스

아래 토픽은 기본 네임스페이스 기준이며, 사용자 정의 메시지 없이 표준 메시지를 사용합니다.
현재 코드의 인터페이스를 기록한 것으로, 자율주행팀과 최종 합의된 규격은 아닙니다.

| 토픽 | 메시지 형식 | 값 또는 용도 |
| --- | --- | --- |
| `/navigation_status` | `std_msgs/msg/String` | `NAVIGATING`, `OBSTACLE_STOP`, `GOAL_REACHED`, `FAILED` |
| `/control_command` | `std_msgs/msg/String` | 상위제어가 발행하는 주행 정지 `STOP` |
| `/stm32_status` | `std_msgs/msg/String` | `DRIVE_STOPPED`, `DRIVE_MOVING` |
| `/payload_command` | `std_msgs/msg/String` | `LOCK`, `UNLOCK`, `LIFT_UP`, `LIFT_DOWN`, `LIFT_STOP`, `FRONT_LED_ON/OFF`, `REAR_LED_ON/OFF` |
| `/esp32_command` | `std_msgs/msg/String` | 허용된 적재함 명령 또는 안전 정지 `LIFT_STOP` |
| `/esp32_status` | `std_msgs/msg/String` | `LOCK_DONE`, `UNLOCK_DONE`, `LIFT_UP_DONE`, `LIFT_DOWN_DONE`, `LIFT_STOPPED`, LED 명령의 `_DONE`, `BUSY:<명령>` |
| `/bridge_status` | `std_msgs/msg/String` | 제어 측에서 `COMM_OK`, `COMM_TIMEOUT`, `COMM_FAILED` 처리 |
| `/control_reset` | `std_msgs/msg/String` | `RESET` |
| `/mock_follow_command` | `std_msgs/msg/String` | `START`, `RESUME`, `STOP` |
| `/mock_obstacle` | `std_msgs/msg/Bool` | 가짜 장애물 유무 |
| `/mock_cmd_vel` | `geometry_msgs/msg/Twist` | 가짜 로봇 속도 |
| `/mock_pose` | `geometry_msgs/msg/Pose2D` | 가짜 로봇 위치 |

두 시리얼 브리지는 UTF-8 문자열에 개행(`\n`)을 붙여 송신하고,
개행 단위로 수신한 문자열을 각각의 상태 토픽으로 그대로 전달합니다.
기본 포트는 STM32 `/tmp/ttySTM32`, ESP32 `/tmp/ttyESP32`, baudrate는 각각 `115200`입니다.
`port`·`baudrate` ROS2 파라미터로 변경할 수 있습니다.

현재 시리얼 브리지는 입출력 예외나 연결 없는 상태에서의 명령 수신 시 `COMM_FAILED`를 발행하지만,
응답 타임아웃·heartbeat·자동 재연결·응답 유효성 검사는 구현되어 있지 않습니다.
`COMM_OK`·`COMM_TIMEOUT`을 자동 발행하지 않으며, 초기 포트 열기 실패 자체는 로그만 남깁니다.
두 보드가 `/bridge_status`를 공유하여 오류 발생 보드를 구분할 수 없는 점도 개선 대상입니다.

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

## 안전 정지 및 통신 오류 Mock 시험

각 시나리오는 새 launch에서 독립적으로 실행합니다. 명령 터미널에서 토픽을 관찰할 수 있습니다.

```bash
ros2 topic echo /control_command
# 다른 터미널에서 실행
ros2 topic echo /esp32_command
```

### 도착 전 적재함 명령 차단

`IDLE` 상태에서 아래 명령은 차단되고 `/esp32_command`로 전달되지 않아야 합니다.

```bash
ros2 topic pub --once /payload_command std_msgs/msg/String "{data: 'LIFT_UP'}"
ros2 topic pub --once /payload_command std_msgs/msg/String "{data: 'UNLOCK'}"
```

도착 후에는 STM32 Mock이 `STOP` 수신 약 2초 뒤 `DRIVE_STOPPED`를 발행합니다.
정지 확인 로그를 확인한 뒤 기존 리프트 시험을 실행합니다.

### 통신 오류 처리

```bash
ros2 topic pub --once /bridge_status std_msgs/msg/String "{data: 'COMM_TIMEOUT'}"
```

`ESTOP` 전환 로그와 `STOP`·`LIFT_STOP` 발행, 가짜 로봇 정지를 확인합니다.
새 launch에서 `COMM_FAILED`로도 반복합니다.
이 시험은 오류 상태를 주입해 제어 로직을 확인하며, 시리얼 브리지가 실제 통신 단절을
자동 검출하는지 검증하는 시험은 아닙니다. 기본 Mock launch는 `/bridge_status`를 자동 발행하지 않습니다.

### 주행 감지 시 리프트 정지

도착·정지 확인 후 `LIFT_UP`을 보내고, 완료 응답 전 다음 상태를 주입합니다.

```bash
ros2 topic pub --once /stm32_status std_msgs/msg/String "{data: 'DRIVE_MOVING'}"
```

정지 확인 해제 로그, `LIFT_STOP` 발행, Mock ESP32의 `LIFT_STOPPED` 응답을 확인합니다.

### 도착 정지 응답 시간 초과

기본 launch의 Mock STM32는 약 2초 뒤 응답하므로 그대로는 3초 시간 초과가 발생하지 않습니다.
통합 launch를 종료하고, 새 터미널마다 위의 ROS2 환경을 적용한 뒤
아래 네 노드만 각각 실행합니다. `mock_stm32`는 실행하지 않습니다.

```bash
ros2 run delivery_robot_control control_subscriber
ros2 run delivery_robot_control mock_esp32
ros2 run delivery_robot_follow mock_robot
ros2 run delivery_robot_follow waypoint_follower
```

명령 터미널에서 `/mock_follow_command`에 `START`를 보냅니다.
최종 도착 후 `STOP`에 응답할 노드가 없으므로 약 3초 후
`STM32 정지 응답 시간 초과 -> ESTOP` 로그와 `STOP`·`LIFT_STOP` 발행을 확인합니다.
시험 후 네 노드를 모두 종료합니다.

## 시리얼 브리지 실행 준비 (실제 통신 미검증)

브리지의 `import serial`에는 pyserial이 필요하지만 현재 `package.xml`·`setup.py`에
의존성이 선언되어 있지 않습니다. Ubuntu 환경에서는 별도로 설치합니다.

```bash
sudo apt install python3-serial
cd ~/delivery_robot_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select delivery_robot_control delivery_robot_bridge
source install/setup.bash
```

다음은 실제 포트가 확인된 뒤 사용할 실행 예시입니다.
`/dev/ttyACM0`·`/dev/ttyUSB0`는 예시이므로 연결된 보드의 포트와 접근 권한을 확인해 변경합니다.
각 노드는 환경을 적용한 별도 터미널에서 실행합니다.

```bash
ros2 run delivery_robot_control control_subscriber
ros2 run delivery_robot_bridge stm32_serial_bridge --ros-args -p port:=/dev/ttyACM0 -p baudrate:=115200
ros2 run delivery_robot_bridge esp32_serial_bridge --ros-args -p port:=/dev/ttyUSB0 -p baudrate:=115200
```

이 실행은 통합 하드웨어 launch나 실제 주행 명령 변환을 제공하지 않습니다.
실제 보드 시험 시 같은 명령에 가짜 응답이 섞이지 않도록 기본 Mock launch와 동시에 실행하지 않습니다.
MCU 펌웨어가 위의 명령·응답과 개행 규칙을 지원하는지는 별도 확인해야 합니다.

## 아직 구현·검증이 필요한 부분

- 실제 Raspberry Pi 4 ↔ STM32·ESP32 통신: 포트·baudrate·개행·응답 규격 및 연결 해제 시험
- MCU 펌웨어 구현/연동 확인, 보드 자체 watchdog 및 실제 비상 정지
- 시리얼 브리지의 응답 타임아웃·heartbeat·재연결·보드별 오류 식별
- 자율주행팀과 토픽·메시지·발행 주기·상태 의미·재개 조건 합의 및 통합 시험
- 실제 속도 명령을 STM32 주행·조향 명령으로 변환하는 인터페이스
- 실제 구동계·조향과 위치 추정
- LiDAR 기반 장애물 감지
- 배송 상태와 주행 시작·재개 허용 조건의 통합, 배송 완료 이벤트 연결
- 실제 리프트 위치·리미트 및 정지 확인
- GUI 및 실제 하드웨어 반복 시험
- pyserial 등 실행 의존성 선언 정리와 기능 회귀 테스트 추가

현재 `test/`에는 ament의 저작권·스타일·docstring 검사 파일만 있으며,
배송 상태머신·통신·안전 로직을 검증하는 기능 자동 테스트는 포함되어 있지 않습니다.

현재 시험 결과는 가상 환경 기준이며,
실제 모터 동작과 센서 기반 안전 검증은 포함하지 않습니다.
