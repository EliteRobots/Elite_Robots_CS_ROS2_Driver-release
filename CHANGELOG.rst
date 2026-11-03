^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Changelog for package elite_robots_driver
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1.2.0 (2026-11-03)
------------------
* Enable automatic memory locking only on real-time kernels with an unlimited soft memlock allowance; preserve explicit ``lock_memory`` overrides to avoid startup failures under finite limits.
* Document memory-locking and scheduling permissions and add runtime regression coverage for memory limits and overrides.
* Add configurable controller-manager targets and optional controller spawning for multi-arm launch composition.
* Accept absolute controller configuration paths and qualify update-rate parameters for namespaced controller managers.
* Add bilingual multi-arm driver and MoveIt setup guides, link them from the usage guides, and install the documentation with the package.

1.1.0 (2026-09-04)
------------------
* Add dashboard services for setting and querying remote control mode.
* Add runtime collision detection, collision sensitivity, and mounting plane configuration.
* Improve trajectory feedback, cancellation handling, and servo command extrapolation.
* Add CS63A and CS630 launch support and bilingual example documentation.
* Contributors: dukang123

1.0.3 (2026-08-31)
------------------
* Link SDK consumers against the exported ``elite-cs-series-sdk::shared`` CMake target.
* Propagate SDK usage requirements through exported driver components.
* Contributors: Yan

1.0.2 (2026-08-28)
------------------
* Use the SDK ROS package metadata without a version constraint.
* Standardize the package maintainer metadata.
* Contributors: Yan

1.0.1 (2026-08-24)
------------------
* Declare the Elite CS Series SDK dependency.
* Declare geometry messages, standard messages, realtime tools, and example runtime dependencies explicitly.
* Contributors: Ivan

1.0.0 (2026-07-29)
------------------
* First public release of the Elite Robots CS ROS 2 driver.
* Added ros2_control hardware, dashboard, primary, and reverse interfaces.
* Added launch files and controller configurations for Elite CS robots.
* Renamed the package to ``elite_robots_driver``.
* Contributors: Yan
