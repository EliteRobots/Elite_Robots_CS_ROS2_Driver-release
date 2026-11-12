# Jazzy parity validation — 2026-10-23

Validated the working trees of Driver and Description on Ubuntu 24.04 / ROS 2
Jazzy, in `/tmp/elite-jazzy-parity-20261023` on the supplied test host.
Both local repositories use branch `codex/sync-jazzy-features`; Humble is unchanged.
Driver reuses `8daf453` from `origin/codex/jazzy-feature-parity` and adds the
runtime fixes and integration tests in this working tree.

Dependencies used:

- Elite CS SDK `2911a08`, package version `1.6.0`, development version.
- ros2_control `4.39.2`, ros2_controllers `4.34.0`.
- MoveIt libraries `2.12.3` from the remote ROS installation.

Results:

- Full build: all 9 workspace packages succeeded. SDK emitted libssh SCP
  deprecation warnings; no package failed.
- Description: 26 model cases passed (13 models, each with and without a TF
  prefix). Xacro expansion, URDF validation, joint count, and mesh paths checked.
- Description `colcon test-result --verbose`: 29 tests, 0 errors, 0 failures,
  0 skipped (includes CTest/pytest aggregate entries).
- Integration: 4 passed. CS63A, CS630, and CS520H accepted and completed virtual
  joint trajectories and produced time-parameterized MoveIt plans. The documented
  dual-arm launch loaded separate controller managers with six correctly prefixed
  claimed joint interfaces per arm.
- The Driver external-control script matches the SDK's bundled script exactly.

Fixes found during validation:

- Single-arm fake hardware now uses the unscaled trajectory controller and leaves
  IO inactive, matching the documented multi-arm fake setup.
- Empty MoveIt prefixes no longer add literal quote characters to joint-limit
  parameter names, which previously caused time parameterization to fail.

Limitations:

- No physical robot was connected. Primary/Dashboard services, collision and
  mounting configuration, and robot-side script behavior were compiled and
  reviewed, but were not exercised on hardware.
- The installed MoveIt `move_group` process reports a segmentation fault in
  `rclcpp::CallbackGroup` destruction after SIGINT. Planning succeeded before
  shutdown; test cleanup terminated remaining processes. The integration pass
  result covers functional assertions, not clean MoveIt shutdown. System ROS
  packages were not modified.

Remote logs: `build.log`, `model-tests.log`, `colcon-test.log`,
`integration-final.log`, and per-launch logs under `integration-final/`.
