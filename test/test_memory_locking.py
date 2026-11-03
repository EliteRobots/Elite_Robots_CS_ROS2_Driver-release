"""Runtime regressions for eli_ros2_control_node's memory-locking policy."""

import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

from ament_index_python.packages import get_package_prefix
import pytest
import yaml


ROBOT_DESCRIPTION = """
<robot name="memory_locking_test">
  <link name="base"/>
  <link name="tip"/>
  <joint name="joint1" type="continuous">
    <parent link="base"/><child link="tip"/>
    <axis xyz="0 0 1"/>
  </joint>
  <ros2_control name="test_system" type="system">
    <hardware><plugin>mock_components/GenericSystem</plugin></hardware>
    <joint name="joint1">
      <command_interface name="position"/>
      <state_interface name="position">
        <param name="initial_value">0.25</param>
      </state_interface>
      <state_interface name="velocity"/>
    </joint>
  </ros2_control>
</robot>
"""

# Apply limits in the child without changing the test runner's allowance.
EXEC_WITH_LIMIT = """
import os, resource, sys
hard = resource.getrlimit(resource.RLIMIT_MEMLOCK)[1]
resource.setrlimit(resource.RLIMIT_MEMLOCK, (int(sys.argv[1]), hard))
os.execv(sys.argv[2], sys.argv[2:])
"""


def has_realtime_kernel():
    realtime = Path('/sys/kernel/realtime')
    return (
        (realtime.exists() and realtime.read_text().strip() == '1')
        or 'PREEMPT_RT' in os.uname().version
    )


def locked_memory_kib(pid):
    for line in Path(f'/proc/{pid}/status').read_text().splitlines():
        if line.startswith('VmLck:'):
            return int(line.split()[1])
    raise AssertionError('VmLck is missing from /proc status')


@pytest.mark.parametrize('allowance', ['finite', 'unlimited'])
@pytest.mark.parametrize('override', [None, False, True], ids=['auto', 'off', 'on'])
def test_memory_locking(allowance, override, tmp_path, record_property):
    hard_limit = resource.getrlimit(resource.RLIMIT_MEMLOCK)[1]
    if allowance == 'unlimited':
        if hard_limit != resource.RLIM_INFINITY:
            pytest.skip('an unlimited hard memlock allowance is required')
        soft_limit = resource.RLIM_INFINITY
    else:
        soft_limit = 2 * 1024 ** 3
        if hard_limit != resource.RLIM_INFINITY:
            if hard_limit < soft_limit and override is True:
                pytest.skip('explicit locking requires a 2 GiB memlock allowance')
            soft_limit = min(soft_limit, hard_limit)

    binary = os.environ.get('ELITE_CONTROL_NODE')
    if not binary:
        binary = str(Path(get_package_prefix('elite_robots_driver')) /
                     'lib/elite_robots_driver/eli_ros2_control_node')
    spawner = str(Path(get_package_prefix('controller_manager')) /
                  'lib/controller_manager/spawner')
    parameters = {
        'update_rate': 125,
        'robot_description': ROBOT_DESCRIPTION,
        'joint_state_broadcaster': {'type': 'joint_state_broadcaster/JointStateBroadcaster'},
    }
    if override is not None:
        parameters['lock_memory'] = override
    config = tmp_path / 'controllers.yaml'
    config.write_text(yaml.safe_dump({'controller_manager': {'ros__parameters': parameters}}))
    env = os.environ.copy()
    env.update({
        'ROS_DOMAIN_ID': env.get('ELITE_TEST_DOMAIN_ID', '181'),
        'ROS_LOCALHOST_ONLY': '1',
        'ROS_LOG_DIR': str(tmp_path / 'ros_logs'),
        'RCUTILS_COLORIZED_OUTPUT': '0',
    })
    log_path = tmp_path / 'control_node.log'
    expected_locked = override if override is not None else (
        allowance == 'unlimited' and has_realtime_kernel())

    with log_path.open('w') as log:
        process = subprocess.Popen(
            [sys.executable, '-c', EXEC_WITH_LIMIT, str(soft_limit), binary,
             '--ros-args', '--params-file', str(config)],
            env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 15
            while 'Spawning controller_manager RT thread' not in log_path.read_text():
                assert process.poll() is None, log_path.read_text()
                assert time.monotonic() < deadline, log_path.read_text()
                time.sleep(0.1)

            # Loading a broadcaster after mlockall exercises later allocations and
            # the RealtimePublisher thread that originally exhausted the allowance.
            result = subprocess.run(
                [spawner, 'joint_state_broadcaster', '-c', '/controller_manager',
                 '--controller-manager-timeout', '15'],
                env=env, capture_output=True, text=True, timeout=30,
            )
            assert result.returncode == 0, result.stdout + result.stderr + log_path.read_text()
            assert process.poll() is None, log_path.read_text()
            locked = locked_memory_kib(process.pid)
            record_property('locked_memory_kib', locked)
            record_property('soft_memlock_bytes', soft_limit)
            assert (locked > 0) == expected_locked, log_path.read_text()
            diagnostic = 'Automatic memory locking disabled:'
            assert (diagnostic in log_path.read_text()) == (
                override is None and allowance == 'finite' and has_realtime_kernel())
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
                pytest.fail('control node did not stop after SIGINT: ' + log_path.read_text())

    assert process.returncode == 0, log_path.read_text()
    assert '[ERROR]' not in log_path.read_text(), log_path.read_text()
