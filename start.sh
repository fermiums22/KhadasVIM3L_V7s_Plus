#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
source /opt/nika-robot/ros_ws/install/setup.bash
exec ros2 launch nika_robot robot.launch.py
