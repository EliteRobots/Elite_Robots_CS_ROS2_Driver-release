# Elite CS MoveIt Cartesian Pose Goal

This package provides the MoveIt configuration and the Cartesian pose goal example for ELITE CS robots.

## Before Running

Start the driver first:

```bash
ros2 launch elite_robots_driver elite_control.launch.py \
  cs_type:=cs63a \
  robot_ip:=172.16.100.82 \
  launch_rviz:=false \
  headless_mode:=true
```

Then start MoveIt:

```bash
ros2 launch elite_robots_moveit_config elite_moveit.launch.py \
  cs_type:=cs63a \
  launch_rviz:=true
```

## Cartesian Pose Goal

Plan to a Cartesian pose with MoveIt and optionally execute the planned trajectory.

Before executing any plan, carefully inspect the trajectory in RViz and make sure the robot
motion is safe for the current workspace and nearby people.

Pose format:

```text
x y z rx ry rz
```

`x y z` are in meters. `rx ry rz` are RPY angles in radians.

C++:

```bash
ros2 run elite_robots_moveit_config example_moveit_pose_goal --ros-args \
  -p target_pose:="[0.4,0.0,0.523,0.3,-1.0,0.5]" \
  -p execute:=true
```

Python:

```bash
ros2 run elite_robots_moveit_config example_moveit_pose_goal_py \
  --target-pose "[0.4,0.0,0.523,0.3,-1.0,0.5]" \
  --execute
```

Plan only without executing:

```bash
ros2 run elite_robots_moveit_config example_moveit_pose_goal --ros-args \
  -p target_pose:="[0.4,0.0,0.523,0.3,-1.0,0.5]"
```
