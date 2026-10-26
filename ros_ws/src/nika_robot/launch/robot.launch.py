from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([Node(package='nika_robot', executable=name,
                                   output='screen', respawn=True, respawn_delay=5)
                              for name in ('diagnostics', 'motion', 'odometry', 'server_bridge')])
