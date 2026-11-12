# 在本项目中组装多台 Elite 机械臂

这份文档可以单独使用。下面两个 launch 文件可以在任意目录创建：

```text
dual_arm_control.launch.py
dual_moveit.launch.py
```

将本文对应章节中的完整代码复制进去。完成工作区编译并 source 后，
进入文件所在目录即可直接按文件名启动：

```bash
cd ~/dual_arm_launch
ros2 launch dual_arm_control.launch.py
ros2 launch dual_moveit.launch.py
```

驱动包提供可复用的单臂入口：

```text
elite_robots_driver/launch/elite_control.launch.py
```

双臂 launch 文件负责把它 include 两次，并为每台机械臂设置独立的
namespace、TF/joint prefix、controller manager、通信端口和控制器。

## 1. 创建双臂 launch 文件

```text
~/dual_arm_launch/
├── dual_arm_control.launch.py
└── dual_moveit.launch.py
```

## 2. 完整双臂驱动 launch

将下面内容完整保存为任意目录下的 `dual_arm_control.launch.py`：

```text
dual_arm_control.launch.py
```

```python
#!/usr/bin/env python3

import re
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.substitutions import FindPackageShare


CONTROLLERS = [
    "joint_state_broadcaster",
    "io_and_status_controller",
    "speed_scaling_state_broadcaster",
    "force_torque_sensor_broadcaster",
    "tcp_pose_broadcaster",
    "scaled_joint_trajectory_controller",
    "forward_position_controller",
    "freedrive_controller",
]


def make_controller_file(namespace, prefix, cs_type):
    controller_filename = (
        "elite_cs_controllers_5f.yaml"
        if cs_type.endswith("h")
        else "elite_cs_controllers.yaml"
    )
    source_path = (
        get_package_share_directory("elite_robots_driver")
        + "/config/"
        + controller_filename
    )
    with open(source_path, "r", encoding="utf-8") as source_file:
        content = source_file.read()

    content = content.replace(
        "controller_manager:",
        f"/{namespace}/controller_manager:",
        1,
    )
    content = content.replace("$(var tf_prefix)", prefix)
    content = re.sub(
        r"^([A-Za-z_][A-Za-z0-9_]*):$",
        lambda match: f"/{namespace}/{match.group(1)}:",
        content,
        flags=re.MULTILINE,
    )

    output = tempfile.NamedTemporaryFile(
        prefix=f"{namespace}_controllers_",
        suffix=".yaml",
        mode="w",
        encoding="utf-8",
        delete=False,
    )
    output.write(content)
    output.close()
    return output.name


def arm_group(
    namespace,
    prefix,
    robot_ip,
    ports,
    cs_type,
    use_fake_hardware,
    headless_mode,
    spawner_timeout,
):
    controller_file = make_controller_file(namespace, prefix, cs_type)
    single_arm_launch = PathJoinSubstitution(
        [
            FindPackageShare("elite_robots_driver"),
            "launch",
            "elite_control.launch.py",
        ]
    )

    fake_hardware = use_fake_hardware.lower() == "true"
    spawner_nodes = []
    for controller_name in CONTROLLERS:
        if fake_hardware and controller_name == "scaled_joint_trajectory_controller":
            controller_name = "joint_trajectory_controller"
        arguments = [
            controller_name,
            "--controller-manager",
            f"/{namespace}/controller_manager",
            "--controller-manager-timeout",
            spawner_timeout,
        ]
        if controller_name in ("forward_position_controller", "freedrive_controller") or (
            fake_hardware and controller_name == "io_and_status_controller"
        ):
            arguments.append("--inactive")
        spawner_nodes.append(
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=arguments,
                output="screen",
            )
        )

    spawner_chain = [spawner_nodes[0]]
    spawner_chain.extend(
        RegisterEventHandler(
            OnProcessExit(target_action=previous, on_exit=[next_node])
        )
        for previous, next_node in zip(spawner_nodes, spawner_nodes[1:])
    )

    if namespace == "arm2":
        spawner_chain.append(
            RegisterEventHandler(
                OnProcessExit(
                    target_action=spawner_nodes[-1],
                    on_exit=[
                        LogInfo(msg="\033[92mAll required controllers are ready.\033[0m")
                    ],
                )
            )
        )

    return GroupAction(
        actions=[
            PushRosNamespace(namespace),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(single_arm_launch),
                launch_arguments={
                    "cs_type": cs_type,
                    "robot_ip": robot_ip,
                    "tf_prefix": prefix,
                    "use_fake_hardware": use_fake_hardware,
                    "headless_mode": headless_mode,
                    "launch_rviz": "false",
                    "controllers_file": controller_file,
                    "controller_spawner_timeout": spawner_timeout,
                    "controller_manager_name": f"/{namespace}/controller_manager",
                    "spawn_controllers": "false",
                    "reverse_port": ports[0],
                    "script_sender_port": ports[1],
                    "trajectory_port": ports[2],
                    "script_command_port": ports[3],
                }.items(),
            ),
        ]
        + spawner_chain
    )


def setup_arms(context, *args, **kwargs):
    arm1_cs_type = LaunchConfiguration("arm1_cs_type").perform(context)
    arm2_cs_type = LaunchConfiguration("arm2_cs_type").perform(context)
    use_fake_hardware = LaunchConfiguration("use_fake_hardware").perform(context)
    return [
        arm_group(
            "arm1", "arm1_", LaunchConfiguration("arm1_ip"),
            (
                LaunchConfiguration("arm1_reverse_port"),
                LaunchConfiguration("arm1_script_sender_port"),
                LaunchConfiguration("arm1_trajectory_port"),
                LaunchConfiguration("arm1_script_command_port"),
            ),
            arm1_cs_type,
            use_fake_hardware,
            LaunchConfiguration("headless_mode"),
            LaunchConfiguration("controller_spawner_timeout"),
        ),
        arm_group(
            "arm2", "arm2_", LaunchConfiguration("arm2_ip"),
            (
                LaunchConfiguration("arm2_reverse_port"),
                LaunchConfiguration("arm2_script_sender_port"),
                LaunchConfiguration("arm2_trajectory_port"),
                LaunchConfiguration("arm2_script_command_port"),
            ),
            arm2_cs_type,
            use_fake_hardware,
            LaunchConfiguration("headless_mode"),
            LaunchConfiguration("controller_spawner_timeout"),
        ),
    ]


def generate_launch_description():
    arm1_ip = LaunchConfiguration("arm1_ip")
    arm2_ip = LaunchConfiguration("arm2_ip")
    arm1_cs_type = LaunchConfiguration("arm1_cs_type")
    arm2_cs_type = LaunchConfiguration("arm2_cs_type")
    use_fake_hardware = LaunchConfiguration("use_fake_hardware")
    headless_mode = LaunchConfiguration("headless_mode")
    spawner_timeout = LaunchConfiguration("controller_spawner_timeout")
    arm1_reverse_port = LaunchConfiguration("arm1_reverse_port")
    arm1_script_sender_port = LaunchConfiguration("arm1_script_sender_port")
    arm1_trajectory_port = LaunchConfiguration("arm1_trajectory_port")
    arm1_script_command_port = LaunchConfiguration("arm1_script_command_port")
    arm2_reverse_port = LaunchConfiguration("arm2_reverse_port")
    arm2_script_sender_port = LaunchConfiguration("arm2_script_sender_port")
    arm2_trajectory_port = LaunchConfiguration("arm2_trajectory_port")
    arm2_script_command_port = LaunchConfiguration("arm2_script_command_port")

    return LaunchDescription(
        [
            DeclareLaunchArgument("arm1_ip", default_value="192.168.1.101"),
            DeclareLaunchArgument("arm2_ip", default_value="192.168.1.102"),
            DeclareLaunchArgument("arm1_cs_type", default_value="cs63"),
            DeclareLaunchArgument("arm2_cs_type", default_value="cs63"),
            DeclareLaunchArgument("use_fake_hardware", default_value="false"),
            DeclareLaunchArgument("headless_mode", default_value="true"),
            DeclareLaunchArgument("controller_spawner_timeout", default_value="30"),
            DeclareLaunchArgument("arm1_reverse_port", default_value="50001"),
            DeclareLaunchArgument("arm1_script_sender_port", default_value="50002"),
            DeclareLaunchArgument("arm1_trajectory_port", default_value="50003"),
            DeclareLaunchArgument("arm1_script_command_port", default_value="50004"),
            DeclareLaunchArgument("arm2_reverse_port", default_value="50101"),
            DeclareLaunchArgument("arm2_script_sender_port", default_value="50102"),
            DeclareLaunchArgument("arm2_trajectory_port", default_value="50103"),
            DeclareLaunchArgument("arm2_script_command_port", default_value="50104"),
            OpaqueFunction(function=setup_arms),
        ]
    )
```

这个模板已经包含：

- 两个独立的 controller manager
- 每台机械臂独立的 TF/joint prefix
- 两组独立通信端口
- 控制器 YAML 自动生成
- 每台机械臂内部按顺序启动控制器
- 最后输出一次绿色的 `All required controllers are ready.`

默认 IP、型号和端口都可以通过启动参数覆盖，不需要修改 Python 文件。

对于 `cs520h` 等五轴型号，模板会自动选择该机械臂对应的五轴控制器配置和关节列表。

Jazzy 的 fake hardware 不提供有效的速度缩放反馈，因此示例在 fake 模式下使用
`joint_trajectory_controller`，MoveIt 也选择同一个控制器。由于模拟硬件缺少运行时
配置命令接口，`io_and_status_controller` 保持 `inactive`。真机模式使用
`scaled_joint_trajectory_controller` 并激活 IO 控制器。

## 3. 编译并启动

```bash
cd ~/elite_ros_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-up-to elite_robots_driver elite_robots_moveit_config
source install/setup.bash
```

fake 双臂：

```bash
ros2 launch dual_arm_control.launch.py \
  use_fake_hardware:=true \
  headless_mode:=false \
  arm1_cs_type:=cs63 \
  arm2_cs_type:=cs63
```

真机双臂：

```bash
ros2 launch dual_arm_control.launch.py \
  use_fake_hardware:=false \
  headless_mode:=true \
  arm1_ip:=192.168.1.101 \
  arm2_ip:=192.168.1.102 \
  arm1_cs_type:=cs63 \
  arm2_cs_type:=cs63
```

真机使用 `headless_mode:=true` 时，机器人需要启用远程控制模式。
如果端口冲突，也可以直接覆盖，例如：

```bash
ros2 launch dual_arm_control.launch.py \
  arm1_ip:=192.168.1.101 \
  arm2_ip:=192.168.1.102 \
  arm1_reverse_port:=51001 \
  arm1_script_sender_port:=51002 \
  arm1_trajectory_port:=51003 \
  arm1_script_command_port:=51004 \
  arm2_reverse_port:=51101 \
  arm2_script_sender_port:=51102 \
  arm2_trajectory_port:=51103 \
  arm2_script_command_port:=51104
```

## 4. 检查和控制

```bash
ros2 control list_controllers -c /arm1/controller_manager
ros2 control list_controllers -c /arm2/controller_manager
ros2 action list | grep follow_joint_trajectory
```

轨迹 action 分别是：

```text
/arm1/scaled_joint_trajectory_controller/follow_joint_trajectory
/arm2/scaled_joint_trajectory_controller/follow_joint_trajectory
```

发送 action 时，joint 名称必须带对应 prefix，例如 `arm1_wrist_1_joint`。

## 5. 完整双臂 MoveIt launch（可选）

不使用 MoveIt 时，到第 4 节就结束。使用 MoveIt 时，在任意目录创建：

```text
dual_moveit.launch.py
```

下面是可以直接复制的完整代码。示例默认使用 `cs63`，并为两台机械臂自动生成
独立的 MoveIt controller、kinematics 和 RViz 临时配置：

```python
#!/usr/bin/env python3

import os
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    GroupAction,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import PushRosNamespace
from launch_ros.substitutions import FindPackageShare


def make_controller_file(prefix, cs_type):
    controller_filename = "controllers_5f.yaml" if cs_type.endswith("h") else "controllers.yaml"
    source_path = os.path.join(
        get_package_share_directory("elite_robots_moveit_config"),
        "config",
        controller_filename,
    )
    with open(source_path, "r", encoding="utf-8") as source_file:
        content = source_file.read()
    content = content.replace("shoulder_", prefix + "shoulder_")
    content = content.replace("elbow_joint", prefix + "elbow_joint")
    content = content.replace("wrist_", prefix + "wrist_")
    output = tempfile.NamedTemporaryFile(
        prefix=prefix + "moveit_controllers_",
        suffix=".yaml",
        mode="w",
        encoding="utf-8",
        delete=False,
    )
    output.write(content)
    output.close()
    return output.name


def make_kinematics_file(group):
    source_path = os.path.join(
        get_package_share_directory("elite_robots_moveit_config"),
        "config",
        "kinematics.yaml",
    )
    with open(source_path, "r", encoding="utf-8") as source_file:
        content = source_file.read().replace("cs_manipulator:", group + ":")
    output = tempfile.NamedTemporaryFile(
        prefix=group + "_kinematics_",
        suffix=".yaml",
        mode="w",
        encoding="utf-8",
        delete=False,
    )
    output.write(content)
    output.close()
    return output.name


def make_rviz_file(group, namespace):
    source_path = os.path.join(
        get_package_share_directory("elite_robots_moveit_config"),
        "rviz",
        "view_robot.rviz",
    )
    with open(source_path, "r", encoding="utf-8") as source_file:
        content = source_file.read()
    content = content.replace("Planning Group: cs_manipulator", "Planning Group: " + group)
    content = content.replace(
        'Move Group Namespace: ""',
        "Move Group Namespace: /" + namespace,
    )
    content = content.replace(
        "Trajectory Topic: /display_planned_path",
        "Trajectory Topic: /" + namespace + "/display_planned_path",
    )
    output = tempfile.NamedTemporaryFile(
        prefix=group + "_rviz_",
        suffix=".rviz",
        mode="w",
        encoding="utf-8",
        delete=False,
    )
    output.write(content)
    output.close()
    return output.name


def arm_moveit(namespace, prefix, cs_type, use_fake_hardware, launch_rviz):
    group = namespace + "_cs_manipulator"
    moveit_launch = PathJoinSubstitution(
        [
            FindPackageShare("elite_robots_moveit_config"),
            "launch",
            "elite_moveit.launch.py",
        ]
    )
    return GroupAction(actions=[
        PushRosNamespace(namespace),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(moveit_launch),
            launch_arguments={
                "cs_type": cs_type,
                "prefix": prefix,
                "use_fake_hardware": use_fake_hardware,
                "launch_rviz": launch_rviz,
                "launch_servo": "false",
                "moveit_controllers_file": make_controller_file(prefix, cs_type),
                "kinematics_file": make_kinematics_file(group),
                "rviz_config_file": make_rviz_file(group, namespace),
                "prefer_scaled_controller": "false" if use_fake_hardware.lower() == "true" else "true",
            }.items(),
        ),
    ])


def setup_arms(context, *args, **kwargs):
    arm1_cs_type = LaunchConfiguration("arm1_cs_type").perform(context)
    arm2_cs_type = LaunchConfiguration("arm2_cs_type").perform(context)
    use_fake_hardware = LaunchConfiguration("use_fake_hardware").perform(context)
    return [
        arm_moveit(
            "arm1", "arm1_", arm1_cs_type,
            use_fake_hardware,
            LaunchConfiguration("launch_rviz"),
        ),
        arm_moveit(
            "arm2", "arm2_", arm2_cs_type,
            use_fake_hardware,
            LaunchConfiguration("launch_rviz"),
        ),
    ]


def generate_launch_description():
    use_fake_hardware = LaunchConfiguration("use_fake_hardware")
    launch_rviz = LaunchConfiguration("launch_rviz")
    return LaunchDescription([
        DeclareLaunchArgument("use_fake_hardware", default_value="false"),
        DeclareLaunchArgument("launch_rviz", default_value="true"),
        DeclareLaunchArgument("arm1_cs_type", default_value="cs63"),
        DeclareLaunchArgument("arm2_cs_type", default_value="cs63"),
        OpaqueFunction(function=setup_arms),
    ])
```

fake 双臂启动：

```bash
ros2 launch dual_moveit.launch.py \
  use_fake_hardware:=true \
  launch_rviz:=true
```

如果某台机械臂是五轴型号，可设置 `arm1_cs_type:=cs520h` 或
`arm2_cs_type:=cs520h`，模板会自动选择五轴 MoveIt 控制器列表。真机则使用
`use_fake_hardware:=false`。启动顺序是先启动第 2 节的
`dual_arm_control.launch.py`，再启动：

```bash
ros2 launch dual_moveit.launch.py
```

## 6. 单臂启动不受影响

```bash
ros2 launch elite_robots_driver elite_control.launch.py \
  robot_ip:=192.168.1.101 \
  cs_type:=cs63
```

单臂默认使用 `/controller_manager`，并由单臂 launch 自己启动控制器。
