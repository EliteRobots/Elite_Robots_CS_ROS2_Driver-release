# Humble memory-locking regression

Build the workspace, source its `install/setup.bash`, and install `python3-pytest`
and `ros-humble-joint-state-broadcaster`. From this repository, run:

```bash
python3 -m pytest test/test_memory_locking.py -v
```

The six cases start `eli_ros2_control_node` with virtual hardware, load and
activate a joint state broadcaster, inspect `/proc/<pid>/status` for locked
memory, and check clean shutdown. They cover automatic locking and explicit
`lock_memory` overrides with finite and unlimited soft limits. No robot connection
is made. Tests use loopback discovery and ROS domain 181; set
`ELITE_TEST_DOMAIN_ID` to another unused domain if needed. Run them sequentially.

Full coverage requires a real-time kernel and an unlimited **hard** memlock
allowance. Cases that require a higher allowance than the test process can set
are skipped. The tests change only their child processes' soft limits. In an
isolated Docker container on a real-time host, use `--ulimit memlock=-1` and run
the tests as an ordinary user without `CAP_IPC_LOCK`. On a non-real-time kernel,
the automatic cases instead verify that locking stays disabled.

`ELITE_CONTROL_NODE=/absolute/path/to/eli_ros2_control_node` selects a different
compiled executable, for example to demonstrate that the original Humble node
fails the automatic/finite case:

```bash
ELITE_CONTROL_NODE=/absolute/path/to/original_node \
  python3 -m pytest test/test_memory_locking.py -v -k 'auto and finite'
```

## Validation on 2026-11-02

Validated in an Ubuntu 22.04.5 / ROS Humble container on kernel
`6.8.1-1039-realtime`, using controller_manager 2.54.3, realtime_tools 2.15.1,
and joint_state_broadcaster 2.54.1. The test user had UID 1000, no effective
capabilities, and `rtprio=0`; the container supplied an unlimited hard memlock
allowance. The finite cases used a 2 GiB soft limit.

The driver, controllers, description, SDK, and two message packages all built
successfully with `colcon build --packages-up-to elite_robots_driver
elite_robots_controllers`. All six runtime cases passed, including broadcaster
activation and clean shutdown with no ERROR logs.

The original node from `humble` commit `f36c671` failed the automatic/finite
regression: its `VmLck` was 1,257,812 KiB instead of zero. The fixed node reported
zero for that case and both explicit-disable cases, and nonzero locked memory
for automatic/unlimited and both explicit-enable cases. This comparison verifies
the locking policy; it does not claim that the small virtual robot reproduces
the original controller-allocation failure. FIFO permission warnings remained
expected with `rtprio=0`.
