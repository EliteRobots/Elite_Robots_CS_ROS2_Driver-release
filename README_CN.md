[英文](./README.md)

# Elite CS Robot Ros2 Driver

此驱动基于 `Elite_Robots_CS_SDK` 开发，支持一些关键的机器人功能，如：运动、设置数字IO。此外，ExternalControl EliCOs 是一个实现这些行为的重要的机器人插件。

## Requirements
- Elite_Robots_CS_SDK
- ROS2 - humble
- Ubuntu22.04


## 此仓库中的包
- `elite_robots_msgs` - 定义了一些共用的服务或消息接口。
- `elite_robots_dashboard_msgs` - 定义了dashboard节点会用到的消息接口。
- `elite_robots_controllers` - Elite CS 机器人控制器的具体实现。
- `elite_robots_calibration` - 从真实机器人上获取标定数据的工具。
- `elite_robots_driver` - 与机器人通信的硬件接口、驱动，包括dashboard_client和primary_client服务节点。
- `elite_robots_moveit_config` - Elite CS机器人的MoveIt配置与示例。

## Getting Started

首次使用时，请前往 [Elite_Robots_CS_ROS2_Tutorials 发布页面](https://github.com/EliteRobots/Elite_Robots_CS_ROS2_Tutorials/releases)下载快速使用手册，并按照手册完成环境配置、驱动安装与机器人启动。

有关驱动启动参数和使用方式的详细说明，请参阅[驱动使用文档](elite_robots_driver/doc/Usage_CN.md)。
