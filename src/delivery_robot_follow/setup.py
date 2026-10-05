from setuptools import find_packages, setup

package_name = 'delivery_robot_follow'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='jeongjonghee',
    maintainer_email='jeongjonghee@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'navigation_publisher = delivery_robot_follow.navigation_publisher:main',
            'mock_robot = delivery_robot_follow.mock_robot:main',
            'waypoint_follower = delivery_robot_follow.waypoint_follower:main',
        ],
    },
)