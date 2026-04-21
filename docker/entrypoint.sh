#!/bin/bash
set -e
# Source ROS so rclpy + ament + ros2 CLIs resolve for both static and runtime checks.
source /opt/ros/humble/setup.bash
exec "$@"
