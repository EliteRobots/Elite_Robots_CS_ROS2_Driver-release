# Elite CS MoveIt 笛卡尔位姿示例

本包提供 ELITE CS 机器人的 MoveIt 配置和笛卡尔位姿规划示例。

## 运行前

先启动 driver：

```bash
ros2 launch elite_robots_driver elite_control.launch.py \
  cs_type:=cs63a \
  robot_ip:=172.16.100.82 \
  launch_rviz:=false \
  headless_mode:=true
```

然后启动 MoveIt：

```bash
ros2 launch elite_robots_moveit_config elite_moveit.launch.py \
  cs_type:=cs63a \
  launch_rviz:=true
```

## 笛卡尔位姿示例

通过 MoveIt 规划到指定笛卡尔位姿，并可选择是否执行规划出的轨迹。

在执行任何规划前，请先在 RViz 中仔细观察路径是否合理，并确保机器人当前工作空间和周围人员都处于安全状态，避免造成人身伤害。

位姿格式：

```text
x y z rx ry rz
```

`x y z` 的单位是米，`rx ry rz` 是 RPY 欧拉角，单位是弧度。

C++：

```bash
ros2 run elite_robots_moveit_config example_moveit_pose_goal --ros-args \
  -p target_pose:="[0.4,0.0,0.523,0.3,-1.0,0.5]" \
  -p execute:=true
```

Python：

```bash
ros2 run elite_robots_moveit_config example_moveit_pose_goal_py \
  --target-pose "[0.4,0.0,0.523,0.3,-1.0,0.5]" \
  --execute
```

只规划不执行：

```bash
ros2 run elite_robots_moveit_config example_moveit_pose_goal --ros-args \
  -p target_pose:="[0.4,0.0,0.523,0.3,-1.0,0.5]"
```
