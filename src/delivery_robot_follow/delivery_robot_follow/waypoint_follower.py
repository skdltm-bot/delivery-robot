from std_msgs.msg import Bool
import math
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Pose2D, Twist
from std_msgs.msg import String


class WaypointFollower(Node):
    def __init__(self):
        super().__init__('waypoint_follower')

        self.waypoints = [
            (1.0, 0.0),
            (1.0, 1.0),
            (0.0, 1.0),
        ]
        self.waypoint_index = 0
        self.goal_tolerance = 0.05

        self.pose = None
        self.last_pose_time = None
        self.active = False
        self.obstacle_detected = False
        self.paused_by_obstacle = False

        self.obstacle_subscription = self.create_subscription(
            Bool,
            'mock_obstacle',
            self.obstacle_callback,
            10
        )
    

        self.velocity_publisher = self.create_publisher(
            Twist, 'mock_cmd_vel', 10
        )
        self.status_publisher = self.create_publisher(
            String, 'navigation_status', 10
        )

        self.pose_subscription = self.create_subscription(
            Pose2D, 'mock_pose', self.pose_callback, 10
        )
        self.start_subscription = self.create_subscription(
            String, 'mock_follow_command', self.command_callback, 10
        )
        self.stop_subscription = self.create_subscription(
            String, 'control_command', self.stop_callback, 10
        )
        self.bridge_subscription = self.create_subscription(
            String, 'bridge_status', self.bridge_callback, 10
        )

        self.timer = self.create_timer(0.1, self.follow)
        self.get_logger().info(
            'Waypoint follower ready: 3 waypoints'
        )
       
    def obstacle_callback(self, msg):
        self.obstacle_detected = msg.data

        if msg.data:
            if self.active:
                self.active = False
                self.paused_by_obstacle = True
                self.velocity_publisher.publish(Twist())
                self.publish_status('OBSTACLE_STOP')

                self.get_logger().warning(
                    '장애물 감지: 이동 정지, 재개 명령 대기'
                )

        elif self.paused_by_obstacle:
            self.get_logger().info(
                '장애물 사라짐: RESUME 명령으로 재개 가능'
            )

    def pose_callback(self, msg):
        self.pose = msg
        self.last_pose_time = time.monotonic()

    def publish_status(self, status):
        msg = String()
        msg.data = status
        self.status_publisher.publish(msg)

    def stop(self):
        self.active = False
        self.paused_by_obstacle = False
        self.velocity_publisher.publish(Twist())

    def pose_is_fresh(self):
        return (
            self.last_pose_time is not None
            and time.monotonic() - self.last_pose_time <= 0.5
        )

    def log_target(self):
        x, y = self.waypoints[self.waypoint_index]
        self.get_logger().info(
            f'목표 {self.waypoint_index + 1}/'
            f'{len(self.waypoints)}: ({x:.1f}, {y:.1f})'
        )

    def command_callback(self, msg):
        if msg.data == 'START':
            if self.active:
                self.get_logger().warning('이미 경로 추종 중')
                return

            if self.paused_by_obstacle:
                self.get_logger().warning(
                    '시작 차단: 장애물로 중단된 경로는 RESUME 사용'
                )
                return

            if self.obstacle_detected:
                self.get_logger().warning(
                    '시작 차단: 장애물이 있음'
                )
                return

            if not self.pose_is_fresh():
                self.get_logger().warning(
                    '시작 차단: 최신 위치 정보가 없음'
                )
                return

            if not self.waypoints:
                self.get_logger().warning(
                    '시작 차단: 경로가 비어 있음'
                )
                return

            self.waypoint_index = 0
            self.active = True
            self.publish_status('NAVIGATING')
            self.get_logger().info('경로 이동 시작')
            self.log_target()

        elif msg.data == 'RESUME':
            if not self.paused_by_obstacle:
                self.get_logger().warning(
                    '재개 차단: 장애물로 중단된 경로가 없음'
                )
                return

            if self.obstacle_detected:
                self.get_logger().warning(
                    '재개 차단: 아직 장애물이 있음'
                )
                return

            if not self.pose_is_fresh():
                self.get_logger().warning(
                    '재개 차단: 최신 위치 정보가 없음'
                )
                return

            self.paused_by_obstacle = False
            self.active = True
            self.publish_status('NAVIGATING')
            self.get_logger().info('장애물 정지 후 경로 재개')
            self.log_target()

        elif msg.data == 'STOP':
            self.stop()
            self.get_logger().info('경로 추종 중단')

        else:
            self.get_logger().warning(
                f'Unknown follow command: {msg.data}'
            )

    def stop_callback(self, msg):
        if msg.data == 'STOP':
            self.stop()

    def bridge_callback(self, msg):
        if msg.data in ['COMM_TIMEOUT', 'COMM_FAILED']:
            self.stop()

    def follow(self):
        if not self.active:
            return

        if not self.pose_is_fresh():
            self.stop()
            self.publish_status('FAILED')
            self.get_logger().error(
                '위치 정보 수신 끊김: 경로 추종 중단'
            )
            return

        target_x, target_y = self.waypoints[self.waypoint_index]

        dx = target_x - self.pose.x
        dy = target_y - self.pose.y
        distance = math.hypot(dx, dy)

        if distance <= self.goal_tolerance:
            # 지점 전환 시 잠깐 정지
            self.velocity_publisher.publish(Twist())

            self.get_logger().info(
                f'지점 {self.waypoint_index + 1} 도착: '
                f'x={self.pose.x:.2f}, y={self.pose.y:.2f}'
            )
            self.waypoint_index += 1

            if self.waypoint_index >= len(self.waypoints):
                self.stop()
                self.publish_status('GOAL_REACHED')
                self.get_logger().info('전체 경로 완료')
            else:
                self.log_target()

            return

        target_angle = math.atan2(dy, dx)
        angle_error = target_angle - self.pose.theta
        angle_error = math.atan2(
            math.sin(angle_error),
            math.cos(angle_error)
        )

        command = Twist()
        command.angular.z = max(
            -0.6, min(0.6, 1.5 * angle_error)
        )

        if abs(angle_error) < 0.3:
            command.linear.x = min(0.2, 0.8 * distance)

        self.velocity_publisher.publish(command)


def main(args=None):
    rclpy.init(args=args)
    node = WaypointFollower()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()