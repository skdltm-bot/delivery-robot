import math
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Pose2D, Twist


class MockRobot(Node):
    def __init__(self):
        super().__init__('mock_robot')

        self.pose = Pose2D()
        self.velocity = Twist()
        self.last_command_time = None
        self.last_update_time = time.monotonic()

        self.pose_publisher = self.create_publisher(
            Pose2D, 'mock_pose', 10
        )

        self.command_subscription = self.create_subscription(
            Twist,
            'mock_cmd_vel',
            self.command_callback,
            10
        )

        self.timer = self.create_timer(0.1, self.update_pose)
        self.get_logger().info('Mock robot ready')

    def command_callback(self, msg):
        self.velocity = msg
        self.last_command_time = time.monotonic()

    def update_pose(self):
        now = time.monotonic()
        dt = min(now - self.last_update_time, 0.2)
        self.last_update_time = now

        # 속도 명령이 0.5초 동안 안 오면 이동 중단
        if (
            self.last_command_time is None
            or now - self.last_command_time > 0.5
        ):
            self.velocity = Twist()

        speed = self.velocity.linear.x
        turn_rate = self.velocity.angular.z

        self.pose.x += speed * math.cos(self.pose.theta) * dt
        self.pose.y += speed * math.sin(self.pose.theta) * dt
        self.pose.theta += turn_rate * dt

        self.pose.theta = math.atan2(
            math.sin(self.pose.theta),
            math.cos(self.pose.theta)
        )

        self.pose_publisher.publish(self.pose)


def main(args=None):
    rclpy.init(args=args)
    node = MockRobot()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()