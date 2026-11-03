^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Changelog for package elite_robots_moveit_config
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1.2.0 (2026-11-03)
------------------
* Propagate the joint prefix to the robot description TF prefix for multi-arm setups.
* Add configurable kinematics and RViz files and accept absolute paths for these files and MoveIt controller configurations.
* Add an option to prefer the scaled trajectory controller and tolerate omitted controller entries in custom configurations.

1.1.0 (2026-09-04)
------------------
* Add C++ and Python Cartesian pose goal examples with bilingual documentation.
* Add CS63A and CS630 launch support.
* Increase trajectory execution margins for robot motion and declare the example dependencies.
* Contributors: dukang123

1.0.3 (2026-08-31)
------------------
* Synchronize the package version for the repository-wide SDK CMake target integration fix.
* Contributors: Yan

1.0.2 (2026-08-28)
------------------
* Standardize the package maintainer metadata.
* Contributors: Yan

1.0.1 (2026-08-24)
------------------
* Declare the Python ament index and YAML runtime dependencies.
* Contributors: Ivan

1.0.0 (2026-07-29)
------------------
* First public release of the Elite Robots MoveIt 2 configuration.
* Added planning, kinematics, controller, SRDF, RViz, and launch configurations.
* Renamed the package and MoveIt launch files.
* Contributors: Yan
