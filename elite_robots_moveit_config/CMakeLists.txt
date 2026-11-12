cmake_minimum_required(VERSION 3.5)
project(elite_robots_moveit_config)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)

install(DIRECTORY config launch rviz srdf
  DESTINATION share/${PROJECT_NAME}
)
install(DIRECTORY example/doc/
  DESTINATION share/${PROJECT_NAME}/example/doc
)

install(
  PROGRAMS example/python/example_moveit_pose_goal.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME example_moveit_pose_goal_py
)

add_executable(
  example_moveit_pose_goal
  example/cpp/example_moveit_pose_goal.cpp
)
target_compile_features(example_moveit_pose_goal PRIVATE cxx_std_17)
ament_target_dependencies(
  example_moveit_pose_goal
  rclcpp
  geometry_msgs
  moveit_ros_planning_interface
  tf2
  tf2_geometry_msgs
)
install(
  TARGETS example_moveit_pose_goal
  DESTINATION lib/${PROJECT_NAME}
)

# Install Python modules
ament_python_install_package(${PROJECT_NAME})
ament_python_install_module(${PROJECT_NAME}/launch_common.py)

ament_package()
