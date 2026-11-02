import rclpy
from rclpy.node import Node
from action_msgs.msg import GoalStatus, GoalStatusArray
from std_msgs.msg import String


class Nav2StatusBridge(Node):
    def __init__(self):
        super().__init__('nav2_status_bridge')

        self.publisher = self.create_publisher(
            String, '/navigation_status', 10
        )

        self.subscription = self.create_subscription(
            GoalStatusArray,
            '/navigate_to_pose/_action/status',
            self.status_callback,
            10
        )

        self.active_goal = None
        self.get_logger().info('Nav2 status bridge ready')

    def send_status(self, status):
        msg = String()
        msg.data = status
        self.publisher.publish(msg)
        self.get_logger().info(f'Published: {status}')

    def status_callback(self, msg):
        statuses = {
            bytes(s.goal_info.goal_id.uuid): s.status
            for s in msg.status_list
        }

        # 실행 중인 목표 추적
        running = [
            goal_id for goal_id, status in statuses.items()
            if status == GoalStatus.STATUS_EXECUTING
        ]

        if running:
            goal_id = running[-1]
            if self.active_goal != goal_id:
                self.active_goal = goal_id
                self.send_status('NAVIGATING')

        if self.active_goal is None:
            return

        status = statuses.get(self.active_goal)

        if status == GoalStatus.STATUS_SUCCEEDED:
            self.send_status('GOAL_REACHED')
            self.active_goal = None

        elif status in (
            GoalStatus.STATUS_ABORTED,
            GoalStatus.STATUS_CANCELED
        ):
            self.send_status('FAILED')
            self.active_goal = None


def main():
    rclpy.init()
    node = Nav2StatusBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
