# 2026-11-02 ROS2 백업

원본: ~/delivery_robot_ws, 기준 커밋 bc366f29b335523c3e8d8d3acaab6cd981818ca4.
Nav2 상태 브리지, 동일한 루트 사본, setup.py 실행 명령 등록을 보관한다.
상태머신, control_subscriber, STM32/ESP32 Mock과 mock_system.launch.py는 기존 커밋 그대로 포함한다.
브리지는 EXECUTING → NAVIGATING, SUCCEEDED → GOAL_REACHED, ABORTED/CANCELED → FAILED로 전달한다.
실행: `ros2 run delivery_robot_control nav2_status_bridge`.
현재 package.xml에는 새 import인 action_msgs 의존성 선언이 없으므로 실행 환경에 action_msgs가 필요하다.

## 팀원 변경 참고 패치 (자동 적용하지 않음)

원본 저장소: https://github.com/dubaijjondeukbai/delivery_robot_ws
기준 커밋: 2f8dbaf (전체 SHA는 아래 SOURCE 파일 참고).
패치는 위 기준에 대한 로컬 수정 두 파일만 기록한다. 팀원 커밋이나 전체 워크스페이스를 병합하지 않았다.
- Gazebo 분기에서 inf_is_clear=sim 전달. 실물 센서에 무조건 True를 적용하면 안 된다.
- Lyrical용 BT를 Jazzy 호환 형태로 교체한 현재 테스트 변경.
- 교체 결과 기존 INVALID_PATH 전용 재계획 분기가 제거되고 BackUp이 복원된다.
  기존 후진 차단 정책과 충돌할 수 있으므로 실물 적용 전 안전 검토가 필요하다.
팀원 워크스페이스에서 `git apply --check <패치경로>`로 먼저 검토하며, 이 백업 저장소에는 대상 패키지가 없어 적용하지 않는다.

## 검증 범위와 제외

Python 문법 및 XML 파싱, 중복 브리지 일치, 패치의 기준 커밋 적용 가능성을 확인한다.
이번 백업에서 ROS2/Gazebo 통합 주행을 재실행하지 않았다. 과거 실행 보고는 새 검증 결과로 간주하지 않는다.
build/, install/, log/, Python 캐시와 팀원 .backup/.bak 파일은 제외한다.
원본 두 워크스페이스의 파일, 브랜치와 커밋은 변경하지 않는다.
