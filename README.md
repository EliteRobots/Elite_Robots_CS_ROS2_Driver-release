[中文](./README_CN.md)

# Elite CS Robot Ros2 Driver

This driver is developed on top of `Elite_Robots_CS_SDK` and support some key cobot functionalities like: motion, set digital io. In addition the ExternalControl EliCOs makes it possible to include ROS2 behaviors in the robot program.

## Requirements
- Elite_Robots_CS_SDK
- ROS2 - jazzy
- Ubuntu24.04


## Packages in the Repository
- `elite_robots_msgs` - some common service or message interface.
- `elite_robots_dashboard_msgs` - package defining messages used by dashboard node.
- `elite_robots_controllers` - implementations of controllers specific for Elite CS robots.
- `elite_robots_calibration` - tool for extracting calibration information from a real robot.
- `elite_robots_driver` - driver / hardware interface for communication with Elite CS robots, including dashboard_client and primary_client service nodes.
- `elite_robots_moveit_config` - example MoveIt configuration for Elite CS robots.

## Getting Started

To get started, download the quick-start guide from the [Elite_Robots_CS_ROS2_Tutorials releases page](https://github.com/EliteRobots/Elite_Robots_CS_ROS2_Tutorials/releases) and follow its instructions to set up your environment, install the driver, and bring up the robot.

For details on driver launch parameters and usage, see the [driver usage documentation](elite_robots_driver/doc/Usage.md).
