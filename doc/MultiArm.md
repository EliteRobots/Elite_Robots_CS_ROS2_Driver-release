# Composing Multiple Elite Arms in This Project

This document is self-contained. The two launch files can be created in any
directory; they do not need to be installed into a ROS package:

```text
dual_arm_control.launch.py
dual_moveit.launch.py
```

Copy the complete code from the corresponding sections below into those files.
After sourcing the workspace, run them directly by filename from their
directory:

```bash
cd ~/dual_arm_launch
ros2 launch dual_arm_control.launch.py
ros2 launch dual_moveit.launch.py
```

The driver package provides the reusable single-arm entry point:

```text
elite_robots_driver/launch/elite_control.launch.py
```

The dual-arm launch file includes it twice and assigns each arm its own
namespace, TF/joint prefix, controller manager, communication ports, and
controllers.

## 1. Create the dual-arm launch files

```text
~/dual_arm_launch/
├── dual_arm_control.launch.py
└── dual_moveit.launch.py
```

## 2. Complete dual-arm driver launch

Save the following complete content as `dual_arm_control.launch.py` in any
directory:

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

    spawner_nodes = []
    for controller_name in CONTROLLERS:
        arguments = [
            controller_name,
            "--controller-manager",
            f"/{namespace}/controller_manager",
            "--controller-manager-timeout",
            spawner_timeout,
        ]
        if controller_name in ("forward_position_controller", "freedrive_controller"):
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
            LaunchConfiguration("use_fake_hardware"),
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
            LaunchConfiguration("use_fake_hardware"),
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

This template provides:

- Two independent controller managers.
- An independent TF/joint prefix for each arm.
- Two independent communication-port groups.
- Automatic generation of controller YAML files.
- Sequential controller startup for each arm.
- One final green `All required controllers are ready.` message.

The default IP addresses, robot models, and ports can all be overridden with
launch arguments; no Python-file edits are required.

For five-axis models such as `cs520h`, the template automatically selects the
five-axis controller configuration and joint list for that arm.

Note: fake hardware mock interfaces do not provide GPIO command interfaces, so
`io_and_status_controller` may be shown as `inactive` during fake tests. This
is a known fake-hardware limitation, not a dual-arm namespace or trajectory
controller failure. On real hardware, this controller should activate when the
corresponding interfaces are available.

## 3. Build and start

```bash
cd ~/elite_ros_ws
source /opt/ros/humble/setup.bash
colcon build --packages-up-to elite_robots_driver elite_robots_moveit_config
source install/setup.bash
```

Fake dual-arm startup:

```bash
ros2 launch dual_arm_control.launch.py \
  use_fake_hardware:=true \
  headless_mode:=false \
  arm1_cs_type:=cs63 \
  arm2_cs_type:=cs63
```

Real dual-arm startup:

```bash
ros2 launch dual_arm_control.launch.py \
  use_fake_hardware:=false \
  headless_mode:=true \
  arm1_ip:=192.168.1.101 \
  arm2_ip:=192.168.1.102 \
  arm1_cs_type:=cs63 \
  arm2_cs_type:=cs63
```

With `headless_mode:=true`, each robot must be in remote-control mode. If
ports conflict, override them directly, for example:

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

## 4. Check and control

```bash
ros2 control list_controllers -c /arm1/controller_manager
ros2 control list_controllers -c /arm2/controller_manager
ros2 action list | grep follow_joint_trajectory
```

The trajectory actions are:

```text
/arm1/scaled_joint_trajectory_controller/follow_joint_trajectory
/arm2/scaled_joint_trajectory_controller/follow_joint_trajectory
```

When sending a trajectory action, joint names must include the corresponding
prefix, for example `arm1_wrist_1_joint`.

## 5. Complete dual-arm MoveIt launch (optional)

If MoveIt is not needed, stop after Section 4. To use MoveIt, create the
following file in any directory:

```text
dual_moveit.launch.py
```

The following complete code can be copied directly. It defaults to `cs63` and
automatically generates independent MoveIt controller, kinematics, and RViz
temporary configuration files for both arms:

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
                "prefer_scaled_controller": "true",
            }.items(),
        ),
    ])


def setup_arms(context, *args, **kwargs):
    arm1_cs_type = LaunchConfiguration("arm1_cs_type").perform(context)
    arm2_cs_type = LaunchConfiguration("arm2_cs_type").perform(context)
    return [
        arm_moveit(
            "arm1", "arm1_", arm1_cs_type,
            LaunchConfiguration("use_fake_hardware"),
            LaunchConfiguration("launch_rviz"),
        ),
        arm_moveit(
            "arm2", "arm2_", arm2_cs_type,
            LaunchConfiguration("use_fake_hardware"),
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

Fake dual-arm MoveIt startup:

```bash
ros2 launch dual_moveit.launch.py \
  use_fake_hardware:=true \
  launch_rviz:=true
```

Use `arm1_cs_type:=cs520h` or `arm2_cs_type:=cs520h` for a five-axis arm; its
five-axis MoveIt controller list is selected automatically. For real hardware,
use `use_fake_hardware:=false`. Start the Section 2
`dual_arm_control.launch.py` first, then run:

```bash
ros2 launch dual_moveit.launch.py
```

## 6. Single-arm startup remains unchanged

```bash
ros2 launch elite_robots_driver elite_control.launch.py \
  robot_ip:=192.168.1.101 \
  cs_type:=cs63
```

Single-arm startup still uses `/controller_manager`, and the single-arm launch
file starts its controllers itself.
