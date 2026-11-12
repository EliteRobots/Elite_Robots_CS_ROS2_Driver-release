"""Opt-in integration tests against an installed workspace, without a robot.

Run after sourcing Jazzy and the workspace:
  ROS_DOMAIN_ID=176 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST \
    python3 -m pytest -q test/test_jazzy_integration.py
"""

import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

import pytest
import rclpy
from ament_index_python.packages import get_package_prefix
from control_msgs.action import FollowJointTrajectory
from controller_manager_msgs.srv import ListControllers
from moveit_msgs.msg import Constraints, JointConstraint
from moveit_msgs.srv import GetMotionPlan
from rclpy.action import ActionClient
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectoryPoint


FAKE_CONTROLLER_STATES = {
    "joint_trajectory_controller": "active",
    "joint_state_broadcaster": "active",
    "force_torque_sensor_broadcaster": "active",
    "speed_scaling_state_broadcaster": "active",
    "tcp_pose_broadcaster": "active",
    "io_and_status_controller": "inactive",
    "forward_position_controller": "inactive",
    "freedrive_controller": "inactive",
}


def wait_future(node, future, timeout=30):
    rclpy.spin_until_future_complete(node, future, timeout_sec=timeout)
    assert future.done(), "ROS request timed out"
    return future.result()


@pytest.mark.parametrize("lock_memory", [None, False])
def test_control_node_with_finite_memlock(lock_memory, tmp_path):
    """Exercise the custom executable without connecting to any robot hardware."""
    assert os.environ.get("ROS_DOMAIN_ID"), "Use an isolated ROS_DOMAIN_ID"
    executable = (Path(get_package_prefix("elite_robots_driver")) / "lib"
                  / "elite_robots_driver" / "eli_ros2_control_node")
    # Apply the limit in a child interpreter, without preexec_fn in a ROS process.
    command = [sys.executable, "-c", """
import os
import resource
import sys
_, hard = resource.getrlimit(resource.RLIMIT_MEMLOCK)
limit = 1536 * 1024 * 1024
if hard != resource.RLIM_INFINITY:
    limit = min(limit, hard)
resource.setrlimit(resource.RLIMIT_MEMLOCK, (limit, hard))
os.execv(sys.argv[1], sys.argv[1:])
""", str(executable), "--ros-args", "-p", "update_rate:=125"]
    if lock_memory is not None:
        command += ["-p", f"lock_memory:={str(lock_memory).lower()}"]
    log_path = tmp_path / "control_node.log"
    with log_path.open("w") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                assert process.poll() is None, log_path.read_text()
                if "Waiting for data on 'robot_description'" in log_path.read_text():
                    break
                time.sleep(0.1)
            else:
                pytest.fail(log_path.read_text())
            status = Path(f"/proc/{process.pid}/status").read_text()
            assert re.search(r"^VmLck:\s+0 kB$", status, re.MULTILINE), status
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
    output = log_path.read_text()
    assert process.returncode == 0, output
    assert "[ERROR]" not in output, output
    assert "Exception" not in output, output


@pytest.mark.parametrize("model", ["cs63a", "cs630", "cs520h"])
def test_fake_motion_and_moveit(model, tmp_path):
    assert os.environ.get("ROS_DOMAIN_ID"), "Use an isolated ROS_DOMAIN_ID"
    processes = []
    logs = []

    def launch(package, filename, **arguments):
        log = (tmp_path / f"{package}.log").open("w")
        logs.append(log)
        processes.append(subprocess.Popen(
            ["ros2", "launch", package, filename]
            + [f"{key}:={value}" for key, value in arguments.items()],
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        ))

    rclpy.init()
    node = rclpy.create_node("jazzy_parity_test")
    states = []
    subscription = node.create_subscription(JointState, "/joint_states", states.append, 10)
    try:
        launch("elite_robots_driver", "elite_control.launch.py", cs_type=model,
               robot_ip="127.0.0.1", use_fake_hardware="true", launch_rviz="false",
               controller_spawner_timeout="60")
        client = node.create_client(ListControllers, "/controller_manager/list_controllers")
        assert client.wait_for_service(timeout_sec=30)
        deadline = time.monotonic() + 90
        controllers = {}
        while time.monotonic() < deadline:
            response = wait_future(node, client.call_async(ListControllers.Request()))
            controllers = {item.name: item.state for item in response.controller}
            if all(controllers.get(name) == state
                   for name, state in FAKE_CONTROLLER_STATES.items()):
                break
            rclpy.spin_once(node, timeout_sec=0.5)
        for name, expected_state in FAKE_CONTROLLER_STATES.items():
            assert controllers.get(name) == expected_state, controllers
        deadline = time.monotonic() + 10
        while not states and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.5)
        assert states
        state = states[-1]
        assert len(state.name) == (5 if model.endswith("h") else 6)

        action = ActionClient(node, FollowJointTrajectory,
                              "/joint_trajectory_controller/follow_joint_trajectory")
        assert action.wait_for_server(timeout_sec=10)
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = list(state.name)
        target = [value + 0.02 for value in state.position]
        point = JointTrajectoryPoint(positions=target)
        point.time_from_start.sec = 2
        goal.trajectory.points = [point]
        handle = wait_future(node, action.send_goal_async(goal))
        assert handle.accepted
        result = wait_future(node, handle.get_result_async()).result
        assert result.error_code == 0, result.error_string

        launch("elite_robots_moveit_config", "elite_moveit.launch.py", cs_type=model,
               use_fake_hardware="true", launch_rviz="false", launch_servo="false")
        planner = node.create_client(GetMotionPlan, "/plan_kinematic_path")
        assert planner.wait_for_service(timeout_sec=30)
        request = GetMotionPlan.Request()
        request.motion_plan_request.group_name = "cs_manipulator"
        request.motion_plan_request.allowed_planning_time = 5.0
        request.motion_plan_request.num_planning_attempts = 3
        request.motion_plan_request.max_velocity_scaling_factor = 0.1
        request.motion_plan_request.max_acceleration_scaling_factor = 0.1
        request.motion_plan_request.start_state.is_diff = True
        request.motion_plan_request.goal_constraints = [Constraints(joint_constraints=[
            JointConstraint(joint_name=name, position=value, tolerance_above=0.01,
                            tolerance_below=0.01, weight=1.0)
            for name, value in zip(state.name, target)
        ])]
        response = wait_future(node, planner.call_async(request))
        assert response.motion_plan_response.error_code.val == 1, response
        assert response.motion_plan_response.trajectory.joint_trajectory.points
    finally:
        node.destroy_subscription(subscription)
        node.destroy_node()
        rclpy.shutdown()
        for process in reversed(processes):
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        for log in logs:
            log.close()
        # Keep logs in pytest's temporary directory on both success and failure.


def test_documented_dual_arm_launch(tmp_path):
    """Exercise absolute YAML paths and separate controller managers from the guide."""
    assert os.environ.get("ROS_DOMAIN_ID"), "Use an isolated ROS_DOMAIN_ID"
    guide = Path(__file__).resolve().parents[1] / "elite_robots_driver/doc/MultiArm.md"
    code = re.findall(r"```python\n(.*?)```", guide.read_text(), re.DOTALL)[0]
    launch_file = tmp_path / "dual_arm.launch.py"
    launch_file.write_text(code)
    rclpy.init()
    node = rclpy.create_node("jazzy_dual_arm_test")
    log = (tmp_path / "dual_arm.log").open("w")
    process = subprocess.Popen([
        "ros2", "launch", str(launch_file), "use_fake_hardware:=true",
        "arm1_cs_type:=cs63a", "arm2_cs_type:=cs630",
        "arm1_ip:=127.0.0.1", "arm2_ip:=127.0.0.1",
        "controller_spawner_timeout:=60",
    ], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        for arm in ("arm1", "arm2"):
            client = node.create_client(ListControllers, f"/{arm}/controller_manager/list_controllers")
            assert client.wait_for_service(timeout_sec=30), arm
            deadline = time.monotonic() + 90
            controllers = {}
            while time.monotonic() < deadline:
                response = wait_future(node, client.call_async(ListControllers.Request()))
                controllers = {item.name: item for item in response.controller}
                trajectory = controllers.get("joint_trajectory_controller")
                io = controllers.get("io_and_status_controller")
                if all(name in controllers and controllers[name].state == state
                       for name, state in FAKE_CONTROLLER_STATES.items()):
                    break
                rclpy.spin_once(node, timeout_sec=0.5)
            for name, expected_state in FAKE_CONTROLLER_STATES.items():
                assert name in controllers and controllers[name].state == expected_state, (arm, controllers)
            assert trajectory and trajectory.state == "active", (arm, controllers)
            assert io and io.state == "inactive", (arm, controllers)
            assert len(trajectory.claimed_interfaces) == 6
            assert all(name.startswith(arm + "_") for name in trajectory.claimed_interfaces)
    finally:
        node.destroy_node()
        rclpy.shutdown()
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        log.close()
