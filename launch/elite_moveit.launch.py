# Author: Chen Shichao

import os

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from elite_robots_moveit_config.launch_common import load_yaml

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution


def launch_setup(context, *args, **kwargs):

    # Initialize Arguments
    cs_type = LaunchConfiguration("cs_type")
    use_fake_hardware = LaunchConfiguration("use_fake_hardware")
    safety_limits = LaunchConfiguration("safety_limits")
    safety_pos_margin = LaunchConfiguration("safety_pos_margin")
    safety_k_position = LaunchConfiguration("safety_k_position")
    # General arguments
    description_package = LaunchConfiguration("description_package")
    description_file = LaunchConfiguration("description_file")
    moveit_config_package = LaunchConfiguration("moveit_config_package")
    moveit_joint_limits_file = LaunchConfiguration("moveit_joint_limits_file")
    moveit_controllers_file = LaunchConfiguration("moveit_controllers_file")
    moveit_config_file = LaunchConfiguration("moveit_config_file")
    warehouse_sqlite_path = LaunchConfiguration("warehouse_sqlite_path")
    prefix = LaunchConfiguration("prefix")
    use_sim_time = LaunchConfiguration("use_sim_time")
    launch_rviz = LaunchConfiguration("launch_rviz")
    launch_servo = LaunchConfiguration("launch_servo")
    publish_robot_description = LaunchConfiguration("publish_robot_description")
    publish_robot_description_semantic = LaunchConfiguration("publish_robot_description_semantic")
    prefer_scaled_controller = LaunchConfiguration("prefer_scaled_controller")

    cs_type_value = cs_type.perform(context)
    is_5_axis = cs_type_value.endswith("h")
    description_file_value = description_file.perform(context)
    moveit_config_file_value = moveit_config_file.perform(context)
    moveit_joint_limits_file_value = moveit_joint_limits_file.perform(context)
    moveit_controllers_file_value = moveit_controllers_file.perform(context)
    description_subdir = "urdf"
    if is_5_axis and description_file_value == "cs.urdf.xacro":
        description_subdir = "urdf_5f"
    if is_5_axis and moveit_config_file_value == "cs.srdf.xacro":
        moveit_config_file_value = "cs_5f.srdf.xacro"
    if is_5_axis and moveit_joint_limits_file_value == "joint_limits.yaml":
        moveit_joint_limits_file_value = "joint_limits_5f.yaml"
    if is_5_axis and moveit_controllers_file_value == "controllers.yaml":
        moveit_controllers_file_value = "controllers_5f.yaml"

    joint_limit_params = PathJoinSubstitution(
        [FindPackageShare(description_package), "config", cs_type, "joint_limits.yaml"]
    )
    kinematics_params = PathJoinSubstitution(
        [FindPackageShare(description_package), "config", cs_type, "default_kinematics.yaml"]
    )
    physical_params = PathJoinSubstitution(
        [FindPackageShare(description_package), "config", cs_type, "physical_parameters.yaml"]
    )
    visual_params = PathJoinSubstitution(
        [FindPackageShare(description_package), "config", cs_type, "visual_parameters.yaml"]
    )

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [FindPackageShare(description_package), description_subdir, description_file_value]
            ),
            " ",
            "robot_ip:=xxx.yyy.zzz.www",
            " ",
            "joint_limit_params:=",
            joint_limit_params,
            " ",
            "kinematics_params:=",
            kinematics_params,
            " ",
            "physical_params:=",
            physical_params,
            " ",
            "visual_params:=",
            visual_params,
            " ",
            "safety_limits:=",
            safety_limits,
            " ",
            "safety_pos_margin:=",
            safety_pos_margin,
            " ",
            "safety_k_position:=",
            safety_k_position,
            " ",
            "name:=",
            "cs",
            " ",
            "cs_type:=",
            cs_type,
            " ",
            "script_filename:=external_control.script",
            " ",
            "input_recipe_filename:=input_recipe.txt",
            " ",
            "output_recipe_filename:=output_recipe.txt",
            " ",
            "prefix:=",
            prefix,
            " ",
            "tf_prefix:=",
            prefix,
            " ",
        ]
    )
    robot_description = {"robot_description": robot_description_content}

    # MoveIt Configuration
    robot_description_semantic_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [FindPackageShare(moveit_config_package), "srdf", moveit_config_file_value]
            ),
            " ",
            "name:=",
            # Also cs_type parameter could be used but then the planning group names in yaml
            # configs has to be updated!
            "cs",
            " ",
            "prefix:=",
            prefix,
            " ",
        ]
    )
    robot_description_semantic = {"robot_description_semantic": robot_description_semantic_content}

    kinematics_file_value = LaunchConfiguration("kinematics_file").perform(context)
    robot_description_kinematics = kinematics_file_value if os.path.isabs(kinematics_file_value) else PathJoinSubstitution(
        [FindPackageShare(moveit_config_package), "config", kinematics_file_value]
    )

    robot_description_planning = {
        "robot_description_planning": load_yaml(
            str(moveit_config_package.perform(context)),
            os.path.join("config", moveit_joint_limits_file_value),
        )
    }

    # Planning Configuration
    ompl_planning_pipeline_config = {
        "move_group": {
            "planning_plugin": "ompl_interface/OMPLPlanner",
            "request_adapters": """default_planner_request_adapters/AddTimeOptimalParameterization default_planner_request_adapters/FixWorkspaceBounds default_planner_request_adapters/FixStartStateBounds default_planner_request_adapters/FixStartStateCollision default_planner_request_adapters/FixStartStatePathConstraints""",
            "start_state_max_bounds_error": 0.1,
        }
    }
    ompl_planning_yaml = load_yaml("elite_robots_moveit_config", "config/ompl_planning.yaml")
    ompl_planning_pipeline_config["move_group"].update(ompl_planning_yaml)

    # Trajectory Execution Configuration
    if os.path.isabs(moveit_controllers_file_value):
        import yaml
        with open(moveit_controllers_file_value, "r") as controller_file:
            controllers_yaml = yaml.safe_load(controller_file)
    else:
        controllers_yaml = load_yaml(
            str(moveit_config_package.perform(context)),
            os.path.join("config", moveit_controllers_file_value),
        )
    # Preserve the historical single-arm fake behavior unless a composed
    # multi-arm launch explicitly requests the scaled controller.  Also avoid
    # indexing optional controller entries in user-provided YAML files.
    scaled_controller = controllers_yaml.get("scaled_joint_trajectory_controller")
    joint_controller = controllers_yaml.get("joint_trajectory_controller")
    if prefer_scaled_controller.perform(context).lower() == "true":
        if scaled_controller is not None:
            scaled_controller["default"] = True
        if joint_controller is not None:
            joint_controller["default"] = False
    elif use_fake_hardware.perform(context).lower() == "true":
        if scaled_controller is not None:
            scaled_controller["default"] = False
        if joint_controller is not None:
            joint_controller["default"] = True

    moveit_controllers = {
        "moveit_simple_controller_manager": controllers_yaml,
        "moveit_controller_manager": "moveit_simple_controller_manager/MoveItSimpleControllerManager",
    }

    trajectory_execution = {
        "moveit_manage_controllers": False,
        "trajectory_execution.allowed_execution_duration_scaling": 10.0,
        "trajectory_execution.allowed_goal_duration_margin": 20.0,
        "trajectory_execution.allowed_start_tolerance": 0.01,
    }

    planning_scene_monitor_parameters = {
        "publish_planning_scene": True,
        "publish_geometry_updates": True,
        "publish_state_updates": True,
        "publish_transforms_updates": True,
        "publish_robot_description" : publish_robot_description,
        "publish_robot_description_semantic" : publish_robot_description_semantic
    }

    warehouse_ros_config = {
        "warehouse_plugin": "warehouse_ros_sqlite::DatabaseConnection",
        "warehouse_host": warehouse_sqlite_path,
    }

    # Start the actual move_group node/action server
    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            robot_description,
            robot_description_semantic,
            robot_description_kinematics,
            robot_description_planning,
            ompl_planning_pipeline_config,
            trajectory_execution,
            moveit_controllers,
            planning_scene_monitor_parameters,
            {"use_sim_time": use_sim_time},
            warehouse_ros_config,
        ],
    )

    # rviz with moveit configuration
    rviz_config_file_value = LaunchConfiguration("rviz_config_file").perform(context)
    rviz_config_file = rviz_config_file_value if os.path.isabs(rviz_config_file_value) else PathJoinSubstitution(
        [FindPackageShare(moveit_config_package), "rviz", rviz_config_file_value]
    )
    rviz_node = Node(
        package="rviz2",
        condition=IfCondition(launch_rviz),
        executable="rviz2",
        name="rviz2_moveit",
        output="log",
        arguments=["-d", rviz_config_file],
        parameters=[
            robot_description,
            robot_description_semantic,
            ompl_planning_pipeline_config,
            robot_description_kinematics,
            robot_description_planning,
            warehouse_ros_config,
        ],
    )

    # Servo node for realtime control
    servo_yaml = load_yaml("elite_robots_moveit_config", "config/cs_servo.yaml")
    servo_params = {"moveit_servo": servo_yaml}
    servo_node = Node(
        package="moveit_servo",
        condition=IfCondition(launch_servo),
        executable="servo_node_main",
        parameters=[
            servo_params,
            robot_description,
            robot_description_semantic,
            robot_description_kinematics,
        ],
        output="screen",
    )

    nodes_to_start = [move_group_node, rviz_node, servo_node]

    return nodes_to_start


def generate_launch_description():

    declared_arguments = []
    # cs specific arguments
    declared_arguments.append(
        DeclareLaunchArgument(
            "cs_type",
            description="Type/series of used ELITE CS robot.",
            choices=["cs63", "cs63a", "cs66", "cs68", "cs612", "cs616", "cs618f", "cs620", "cs625", "cs630", "cs66a", "cs520h", "ls65"],
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "use_fake_hardware",
            default_value="false",
            description="Indicate whether robot is running with fake hardware mirroring command to its states.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "safety_limits",
            default_value="true",
            description="Enables the safety limits controller if true.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "safety_pos_margin",
            default_value="0.15",
            description="The margin to lower and upper limits in the safety controller.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "safety_k_position",
            default_value="20",
            description="k-position factor in the safety controller.",
        )
    )
    # General arguments
    declared_arguments.append(
        DeclareLaunchArgument(
            "description_package",
            default_value="elite_robots_description",
            description="Description package with robot URDF/XACRO files. Usually the argument "
            "is not set, it enables use of a custom description.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "description_file",
            default_value="cs.urdf.xacro",
            description="URDF/XACRO description file with the robot. The default switches to urdf_5f for cs_type values ending with 'h'.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "moveit_config_package",
            default_value="elite_robots_moveit_config",
            description="MoveIt config package with robot SRDF/XACRO files. Usually the argument "
            "is not set, it enables use of a custom moveit config.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "moveit_config_file",
            default_value="cs.srdf.xacro",
            description="MoveIt SRDF/XACRO description file with the robot. The default switches to the 5-axis SRDF for cs_type values ending with 'h'.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "moveit_joint_limits_file",
            default_value="joint_limits.yaml",
            description="MoveIt joint limits that augment or override the values from the URDF robot_description. "
            "The default switches to the 5-axis file for cs_type values ending with 'h'.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "moveit_controllers_file",
            default_value="controllers.yaml",
            description="MoveIt controller list configuration file. The default switches to the 5-axis file for cs_type values ending with 'h'.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "warehouse_sqlite_path",
            default_value=os.path.expanduser("~/.ros/warehouse_ros.sqlite"),
            description="Path where the warehouse database should be stored",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="false",
            description="Make MoveIt to use simulation time. This is needed for the trajectory planing in simulation.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "prefix",
            default_value='""',
            description="Prefix of the joint names, useful for "
            "multi-robot setup. If changed than also joint names in the controllers' configuration "
            "have to be updated.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument("launch_rviz", default_value="true", description="Launch RViz?")
    )
    declared_arguments.append(DeclareLaunchArgument("rviz_config_file", default_value="view_robot.rviz"))
    declared_arguments.append(DeclareLaunchArgument("kinematics_file", default_value="kinematics.yaml"))
    declared_arguments.append(
        DeclareLaunchArgument("launch_servo", default_value="true", description="Launch Servo?")
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "prefer_scaled_controller",
            default_value="false",
            description="Prefer scaled_joint_trajectory_controller when available.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "publish_robot_description",
            default_value="true",
            description="MoveGroup publishes robot description"
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "publish_robot_description_semantic",
            default_value="true",
            description="MoveGroup publishes robot description semantic"
        )
    )

    return LaunchDescription(declared_arguments + [OpaqueFunction(function=launch_setup)])
