# Assignment 4 - Part C-c: Pick and Place with TurtleBot
# Task: Align → Approach → Grab → Lift → Return Home → Place

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from open_manipulator_msgs.action import ToolControl
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
import json
import time
import math
from enum import Enum

class State(Enum):
    """State machine states for pick and place task"""
    SEARCHING = 1           # Looking for bottle
    CENTERING = 2           # Rotating to center bottle
    APPROACHING = 3         # Moving forward toward bottle
    POSITIONING_ARM = 4     # Moving arm to pre-grasp position
    GRASPING = 5            # Closing gripper
    LIFTING = 6             # Lifting bottle
    RETURNING_HOME = 7      # Navigate back to starting position
    LOWERING_ARM = 8        # Lower arm to place bottle
    RELEASING = 9           # Open gripper to release
    RETURN_COMPLETE = 10    # Task complete

class PickAndPlaceNode(Node):
    """
    Complete pick and place pipeline with return to home base.
    """
    
    def __init__(self):
        super().__init__('pick_and_place_node')
        
        # ====================================================================
        # ROS2 Setup
        # ====================================================================
        
        # Subscribe to YOLO detections
        self.subscription = self.create_subscription(
            String,
            '/yolo/detections_json',
            self.detection_callback,
            10
        )
        
        # Subscribe to odometry for position tracking
        self.odom_sub = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10
        )
        
        # Publisher for robot movement
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # Publisher for arm joint control
        self.joint_pub = self.create_publisher(
            JointTrajectory,
            '/arm_controller/joint_trajectory',
            10
        )
        
        # Action client for gripper control
        self.gripper_action_client = ActionClient(
            self,
            ToolControl,
            '/tool_control'
        )
        
        # ====================================================================
        # Position Tracking (Odometry)
        # ====================================================================
        
        # Store home position (where robot starts)
        self.home_position = None
        self.home_orientation = None
        self.home_recorded = False
        
        # Current position
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_yaw = 0.0
        
        # ====================================================================
        # Camera and Detection Parameters
        # ====================================================================
        
        self.image_width = 1280
        self.image_height = 720
        self.image_center_x = self.image_width / 2
        
        # ====================================================================
        # Control Parameters
        # ====================================================================
        
        # Centering
        self.center_tolerance_x = 50
        self.angular_speed_max = 0.3
        self.kp_angular = 0.002
        
        # Approaching
        self.target_bbox_area = 80000  # Calibrate this value!
        self.bbox_area_tolerance = 5000
        self.linear_speed = 0.1
        self.kp_linear = 0.000005
        
        # Navigation
        self.position_tolerance = 0.1  # meters
        self.angle_tolerance = 0.2  # radians
        self.nav_linear_speed = 0.15  # m/s
        self.nav_angular_speed = 0.3  # rad/s
        
        # ====================================================================
        # State Machine
        # ====================================================================
        
        self.state = State.SEARCHING
        self.prev_state = None
        
        # Detection state
        self.bottle_detected = False
        self.bottle_bbox = None
        self.bottle_confidence = 0.0
        
        # Timing
        self.state_start_time = time.time()
        
        # ====================================================================
        # Arm Joint Names
        # ====================================================================
        
        self.joint_names = ['joint1', 'joint2', 'joint3', 'joint4']
        
        self.get_logger().info("="*60)
        self.get_logger().info("Pick and Place Node Started")
        self.get_logger().info("="*60)
        self.get_logger().info("⚠️  Move robot to HOME BASE and press Enter...")
        input()  # Wait for user confirmation
        
        self.get_logger().info("✓ Recording home position...")
        time.sleep(1)  # Give odometry time to stabilize

    # ========================================================================
    # Odometry Callback
    # ========================================================================
    
    def odom_callback(self, msg):
        """Update current position from odometry."""
        # Extract position
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
        
        # Extract orientation (convert quaternion to yaw)
        orientation_q = msg.pose.pose.orientation
        siny_cosp = 2 * (orientation_q.w * orientation_q.z + 
                         orientation_q.x * orientation_q.y)
        cosy_cosp = 1 - 2 * (orientation_q.y * orientation_q.y + 
                             orientation_q.z * orientation_q.z)
        self.current_yaw = math.atan2(siny_cosp, cosy_cosp)
        
        # Record home position (first time only)
        if not self.home_recorded:
            self.home_position = (self.current_x, self.current_y)
            self.home_orientation = self.current_yaw
            self.home_recorded = True
            self.get_logger().info(
                f"✓ Home position recorded: "
                f"({self.home_position[0]:.3f}, {self.home_position[1]:.3f}), "
                f"yaw={self.home_orientation:.3f}"
            )

    # ========================================================================
    # Detection Callback
    # ========================================================================
    
    def detection_callback(self, msg):
        """Process YOLO detections and run state machine."""
        try:
            data = json.loads(msg.data)
            detections = data.get("detections", [])
            
            # Look for bottle
            bottle_found = False
            for det in detections:
                if det["class_name"] == "bottle" and det["confidence"] > 0.5:
                    bottle_found = True
                    self.bottle_detected = True
                    self.bottle_bbox = det["bbox"]
                    self.bottle_confidence = det["confidence"]
                    break
            
            if not bottle_found:
                self.bottle_detected = False
                self.bottle_bbox = None
            
            # Run state machine
            self.run_state_machine()
            
        except json.JSONDecodeError as e:
            self.get_logger().error(f"JSON parse error: {e}")

    # ========================================================================
    # State Machine
    # ========================================================================
    
    def run_state_machine(self):
        """Execute current state logic."""
        
        # Log state transitions
        if self.state != self.prev_state:
            self.get_logger().info("")
            self.get_logger().info("="*60)
            self.get_logger().info(f"STATE: {self.state.name}")
            self.get_logger().info("="*60)
            self.prev_state = self.state
            self.state_start_time = time.time()
        
        # Execute state
        if self.state == State.SEARCHING:
            self.state_searching()
        elif self.state == State.CENTERING:
            self.state_centering()
        elif self.state == State.APPROACHING:
            self.state_approaching()
        elif self.state == State.POSITIONING_ARM:
            self.state_positioning_arm()
        elif self.state == State.GRASPING:
            self.state_grasping()
        elif self.state == State.LIFTING:
            self.state_lifting()
        elif self.state == State.RETURNING_HOME:
            self.state_returning_home()
        elif self.state == State.LOWERING_ARM:
            self.state_lowering_arm()
        elif self.state == State.RELEASING:
            self.state_releasing()
        elif self.state == State.RETURN_COMPLETE:
            self.state_return_complete()

    # ========================================================================
    # States: SEARCHING, CENTERING, APPROACHING (same as Task 1b)
    # ========================================================================
    
    def state_searching(self):
        """Wait for bottle detection."""
        if not self.bottle_detected:
            twist = Twist()
            twist.angular.z = 0.2
            self.cmd_vel_pub.publish(twist)
            
            if int(time.time() - self.state_start_time) % 5 == 0:
                self.get_logger().info("Searching for bottle...")
        else:
            self.stop_robot()
            self.get_logger().info(f"✓ Bottle detected! Conf: {self.bottle_confidence:.2f}")
            self.state = State.CENTERING

    def state_centering(self):
        """Center the bottle in camera view."""
        if not self.bottle_detected:
            self.get_logger().warn("Lost bottle during centering!")
            self.state = State.SEARCHING
            return
        
        bottle_x = self.bottle_bbox['cx']
        error_x = bottle_x - self.image_center_x
        
        if abs(error_x) < self.center_tolerance_x:
            self.stop_robot()
            self.get_logger().info(f"✓ Bottle CENTERED at x={bottle_x:.1f}")
            self.state = State.APPROACHING
        else:
            angular_vel = -self.kp_angular * error_x
            angular_vel = max(min(angular_vel, self.angular_speed_max), 
                            -self.angular_speed_max)
            
            twist = Twist()
            twist.angular.z = angular_vel
            self.cmd_vel_pub.publish(twist)
            
            direction = "RIGHT" if error_x > 0 else "LEFT"
            self.get_logger().info(
                f"Centering: {direction} | error={error_x:.1f}px"
            )

    def state_approaching(self):
        """Drive forward until close to bottle."""
        if not self.bottle_detected:
            self.get_logger().warn("Lost bottle during approach!")
            self.state = State.SEARCHING
            return
        
        bbox_area = self.bottle_bbox['w'] * self.bottle_bbox['h']
        
        if bbox_area >= (self.target_bbox_area - self.bbox_area_tolerance):
            self.stop_robot()
            self.get_logger().info(
                f"✓ Reached target distance! Area: {bbox_area:.0f}"
            )
            self.state = State.POSITIONING_ARM
        else:
            error_area = self.target_bbox_area - bbox_area
            linear_vel = self.kp_linear * error_area
            linear_vel = min(linear_vel, self.linear_speed)
            
            twist = Twist()
            twist.linear.x = linear_vel
            
            # Minor angle correction
            bottle_x = self.bottle_bbox['cx']
            error_x = bottle_x - self.image_center_x
            if abs(error_x) > self.center_tolerance_x * 2:
                twist.angular.z = -self.kp_angular * error_x * 0.5
            
            self.cmd_vel_pub.publish(twist)
            
            self.get_logger().info(
                f"Approaching: area={bbox_area:.0f}/{self.target_bbox_area}"
            )

    # ========================================================================
    # States: ARM CONTROL (same as Task 1b)
    # ========================================================================
    
    def state_positioning_arm(self):
        """Move arm to pre-grasp position."""
        elapsed = time.time() - self.state_start_time
        
        if elapsed < 0.5:
            self.move_arm_to_grasp_position()
            self.get_logger().info("Moving arm to grasp position...")
        elif elapsed > 3.0:
            self.get_logger().info("✓ Arm positioned")
            self.state = State.GRASPING

    def move_arm_to_grasp_position(self):
        """Send joint trajectory for grasping."""
        traj = JointTrajectory()
        traj.joint_names = self.joint_names
        
        point = JointTrajectoryPoint()
        point.positions = [0.0, -0.5, 0.8, 0.3]  # Pre-grasp pose
        point.time_from_start.sec = 2
        
        traj.points = [point]
        self.joint_pub.publish(traj)

    def state_grasping(self):
        """Close gripper to grasp bottle."""
        elapsed = time.time() - self.state_start_time
        
        if elapsed < 0.5:
            self.close_gripper()
            self.get_logger().info("Closing gripper...")
        elif elapsed > 2.0:
            self.get_logger().info("✓ Bottle grasped")
            self.state = State.LIFTING

    def close_gripper(self):
        """Send action to close gripper."""
        goal = ToolControl.Goal()
        goal.planning_group = "gripper"
        goal.value = -0.01  # Close
        
        if self.gripper_action_client.wait_for_server(timeout_sec=1.0):
            self.gripper_action_client.send_goal_async(goal)

    def state_lifting(self):
        """Lift bottle off the ground."""
        elapsed = time.time() - self.state_start_time
        
        if elapsed < 0.5:
            self.lift_arm()
            self.get_logger().info("Lifting bottle...")
        elif elapsed > 3.0:
            self.get_logger().info("✓ Bottle lifted!")
            self.state = State.RETURNING_HOME  # NEW: go home instead of DONE

    def lift_arm(self):
        """Move arm up to lift bottle."""
        traj = JointTrajectory()
        traj.joint_names = self.joint_names
        
        point = JointTrajectoryPoint()
        point.positions = [0.0, 0.0, 0.0, 0.0]  # Home position
        point.time_from_start.sec = 2
        
        traj.points = [point]
        self.joint_pub.publish(traj)

    # ========================================================================
    # NEW STATES: RETURN TO HOME BASE
    # ========================================================================
    
    def state_returning_home(self):
        """Navigate back to home position."""
        if not self.home_recorded:
            self.get_logger().error("Home position not recorded!")
            self.state = State.RETURN_COMPLETE
            return
        
        # Calculate distance and angle to home
        dx = self.home_position[0] - self.current_x
        dy = self.home_position[1] - self.current_y
        distance = math.sqrt(dx**2 + dy**2)
        
        # Calculate desired heading to home
        desired_yaw = math.atan2(dy, dx)
        angle_error = desired_yaw - self.current_yaw
        
        # Normalize angle to [-pi, pi]
        while angle_error > math.pi:
            angle_error -= 2 * math.pi
        while angle_error < -math.pi:
            angle_error += 2 * math.pi
        
        # Check if we've arrived
        if distance < self.position_tolerance:
            self.stop_robot()
            self.get_logger().info(f"✓ Arrived at home! Distance: {distance:.3f}m")
            self.state = State.LOWERING_ARM
            return
        
        # Navigate toward home
        twist = Twist()
        
        # First, align to home direction
        if abs(angle_error) > self.angle_tolerance:
            # Need to rotate
            twist.angular.z = self.nav_angular_speed if angle_error > 0 else -self.nav_angular_speed
            self.get_logger().info(
                f"Rotating to home: angle_error={angle_error:.3f} rad"
            )
        else:
            # Move forward
            twist.linear.x = self.nav_linear_speed
            # Minor angle correction while moving
            twist.angular.z = 0.5 * angle_error
            self.get_logger().info(
                f"Moving to home: distance={distance:.3f}m, "
                f"angle_error={angle_error:.3f}"
            )
        
        self.cmd_vel_pub.publish(twist)

    # ========================================================================
    # NEW STATES: PLACE BOTTLE
    # ========================================================================
    
    def state_lowering_arm(self):
        """Lower arm to place bottle."""
        elapsed = time.time() - self.state_start_time
        
        if elapsed < 0.5:
            self.lower_arm_to_place()
            self.get_logger().info("Lowering arm to place bottle...")
        elif elapsed > 3.0:
            self.get_logger().info("✓ Arm lowered")
            self.state = State.RELEASING

    def lower_arm_to_place(self):
        """Move arm down to ground level."""
        traj = JointTrajectory()
        traj.joint_names = self.joint_names
        
        point = JointTrajectoryPoint()
        point.positions = [0.0, -0.5, 0.8, 0.3]  # Place position (similar to grasp)
        point.time_from_start.sec = 2
        
        traj.points = [point]
        self.joint_pub.publish(traj)

    def state_releasing(self):
        """Open gripper to release bottle."""
        elapsed = time.time() - self.state_start_time
        
        if elapsed < 0.5:
            self.open_gripper()
            self.get_logger().info("Opening gripper to release...")
        elif elapsed > 2.0:
            self.get_logger().info("✓ Bottle released")
            # Return arm to home position
            self.lift_arm()
            time.sleep(2)
            self.state = State.RETURN_COMPLETE

    def open_gripper(self):
        """Send action to open gripper."""
        goal = ToolControl.Goal()
        goal.planning_group = "gripper"
        goal.value = 0.01  # Open (positive value)
        
        if self.gripper_action_client.wait_for_server(timeout_sec=1.0):
            self.gripper_action_client.send_goal_async(goal)

    # ========================================================================
    # Final State
    # ========================================================================
    
    def state_return_complete(self):
        """Task complete."""
        self.get_logger().info("")
        self.get_logger().info("="*60)
        self.get_logger().info("✓✓✓ PICK AND PLACE COMPLETE! ✓✓✓")
        self.get_logger().info("="*60)
        self.get_logger().info(f"Home: {self.home_position}")
        self.get_logger().info(f"Current: ({self.current_x:.3f}, {self.current_y:.3f})")
        time.sleep(2)

    # ========================================================================
    # Utility Functions
    # ========================================================================
    
    def stop_robot(self):
        """Stop all robot movement."""
        twist = Twist()
        twist.linear.x = 0.0
        twist.angular.z = 0.0
        self.cmd_vel_pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = PickAndPlaceNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down...")
    finally:
        node.stop_robot()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
