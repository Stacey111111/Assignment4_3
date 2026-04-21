# Assignment 4 - Part C-b: Pick the Bottle with TurtleBot
# Task: Align → Approach → Extend arm → Grab → Lift

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from open_manipulator_msgs.action import ToolControl
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from control_msgs.action import FollowJointTrajectory
import json
import time
from enum import Enum

class State(Enum):
    """State machine states for bottle picking task"""
    SEARCHING = 1      # Looking for bottle
    CENTERING = 2      # Rotating to center bottle
    APPROACHING = 3    # Moving forward toward bottle
    POSITIONING_ARM = 4  # Moving arm to pre-grasp position
    GRASPING = 5       # Closing gripper
    LIFTING = 6        # Lifting bottle
    DONE = 7           # Task complete

class BottlePickNode(Node):
    """
    Complete bottle picking pipeline using state machine.
    """
    
    def __init__(self):
        super().__init__('bottle_pick_node')
        
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
        # Camera and Detection Parameters
        # ====================================================================
        
        self.image_width = 1280
        self.image_height = 720
        self.image_center_x = self.image_width / 2
        self.image_center_y = self.image_height / 2
        
        # ====================================================================
        # Control Parameters
        # ====================================================================
        
        # Centering thresholds
        self.center_tolerance_x = 50  # pixels
        self.angular_speed_max = 0.3  # rad/s
        self.kp_angular = 0.002  # Proportional gain for rotation
        
        # Approaching thresholds
        self.target_bbox_area = 80000  # Target bounding box area (pixels²)
        # When bbox area reaches this, robot is close enough
        self.bbox_area_tolerance = 5000  # Tolerance range
        self.linear_speed = 0.1  # m/s forward speed
        self.kp_linear = 0.000005  # Proportional gain for approach
        
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
        # Arm Joint Names (Open Manipulator X)
        # ====================================================================
        
        self.joint_names = [
            'joint1',  # Base rotation
            'joint2',  # Shoulder
            'joint3',  # Elbow
            'joint4'   # Wrist
        ]
        
        self.get_logger().info("="*60)
        self.get_logger().info("Bottle Picking Node Started")
        self.get_logger().info("="*60)
        self.get_logger().info(f"Initial State: {self.state.name}")
        self.get_logger().info(f"Target bbox area: {self.target_bbox_area}")

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
            self.get_logger().info(f"STATE TRANSITION: {self.prev_state} → {self.state.name}")
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
        elif self.state == State.DONE:
            self.state_done()

    # ========================================================================
    # State: SEARCHING
    # ========================================================================
    
    def state_searching(self):
        """Wait for bottle detection."""
        if not self.bottle_detected:
            # Slowly rotate to search
            twist = Twist()
            twist.angular.z = 0.2  # Slow rotation
            self.cmd_vel_pub.publish(twist)
            
            if int(time.time() - self.state_start_time) % 5 == 0:
                self.get_logger().info("Searching for bottle...")
        else:
            # Bottle detected!
            self.stop_robot()
            self.get_logger().info(f"✓ Bottle detected! Confidence: {self.bottle_confidence:.2f}")
            self.state = State.CENTERING

    # ========================================================================
    # State: CENTERING
    # ========================================================================
    
    def state_centering(self):
        """Center the bottle in camera view."""
        if not self.bottle_detected:
            self.get_logger().warn("Lost bottle during centering!")
            self.state = State.SEARCHING
            return
        
        # Calculate horizontal error
        bottle_x = self.bottle_bbox['cx']
        error_x = bottle_x - self.image_center_x
        
        # Check if centered
        if abs(error_x) < self.center_tolerance_x:
            self.stop_robot()
            self.get_logger().info(f"✓ Bottle CENTERED at x={bottle_x:.1f}")
            self.state = State.APPROACHING
        else:
            # Turn to center
            angular_vel = -self.kp_angular * error_x
            angular_vel = max(min(angular_vel, self.angular_speed_max), -self.angular_speed_max)
            
            twist = Twist()
            twist.angular.z = angular_vel
            self.cmd_vel_pub.publish(twist)
            
            direction = "RIGHT" if error_x > 0 else "LEFT"
            self.get_logger().info(
                f"Centering: {direction} | error={error_x:.1f}px, "
                f"ω={angular_vel:.3f} rad/s"
            )

    # ========================================================================
    # State: APPROACHING
    # ========================================================================
    
    def state_approaching(self):
        """Drive forward until close to bottle."""
        if not self.bottle_detected:
            self.get_logger().warn("Lost bottle during approach!")
            self.state = State.SEARCHING
            return
        
        # Calculate bounding box area
        bbox_area = self.bottle_bbox['w'] * self.bottle_bbox['h']
        
        # Check if close enough
        if bbox_area >= (self.target_bbox_area - self.bbox_area_tolerance):
            self.stop_robot()
            self.get_logger().info(
                f"✓ Reached target distance! "
                f"BBox area: {bbox_area:.0f} >= {self.target_bbox_area}"
            )
            self.state = State.POSITIONING_ARM
        else:
            # Move forward with proportional control
            error_area = self.target_bbox_area - bbox_area
            linear_vel = self.kp_linear * error_area
            linear_vel = min(linear_vel, self.linear_speed)  # Cap speed
            
            twist = Twist()
            twist.linear.x = linear_vel
            
            # Minor angle correction while approaching
            bottle_x = self.bottle_bbox['cx']
            error_x = bottle_x - self.image_center_x
            if abs(error_x) > self.center_tolerance_x * 2:
                twist.angular.z = -self.kp_angular * error_x * 0.5
            
            self.cmd_vel_pub.publish(twist)
            
            self.get_logger().info(
                f"Approaching: area={bbox_area:.0f}/{self.target_bbox_area}, "
                f"v={linear_vel:.3f} m/s"
            )

    # ========================================================================
    # State: POSITIONING_ARM
    # ========================================================================
    
    def state_positioning_arm(self):
        """Move arm to pre-grasp position."""
        elapsed = time.time() - self.state_start_time
        
        if elapsed < 0.5:
            # Just entered state, send arm command
            self.move_arm_to_grasp_position()
            self.get_logger().info("Moving arm to grasp position...")
        elif elapsed > 3.0:
            # Arm should be in position now
            self.get_logger().info("✓ Arm positioned")
            self.state = State.GRASPING

    def move_arm_to_grasp_position(self):
        """
        Send joint trajectory to position arm for grasping.
        
        Joint angles for grasping a bottle on the ground:
        - joint1 (base): 0.0 (facing forward)
        - joint2 (shoulder): -0.5 (lean forward)
        - joint3 (elbow): 0.8 (bend down)
        - joint4 (wrist): 0.3 (point down)
        """
        traj = JointTrajectory()
        traj.joint_names = self.joint_names
        
        point = JointTrajectoryPoint()
        point.positions = [0.0, -0.5, 0.8, 0.3]  # Adjust these values as needed
        point.time_from_start.sec = 2  # Take 2 seconds to move
        
        traj.points = [point]
        self.joint_pub.publish(traj)

    # ========================================================================
    # State: GRASPING
    # ========================================================================
    
    def state_grasping(self):
        """Close gripper to grasp bottle."""
        elapsed = time.time() - self.state_start_time
        
        if elapsed < 0.5:
            # Send gripper close command
            self.close_gripper()
            self.get_logger().info("Closing gripper...")
        elif elapsed > 2.0:
            # Gripper should be closed
            self.get_logger().info("✓ Bottle grasped")
            self.state = State.LIFTING

    def close_gripper(self):
        """Send action to close gripper."""
        goal = ToolControl.Goal()
        goal.planning_group = "gripper"
        goal.value = -0.01  # Close gripper (negative value)
        
        if self.gripper_action_client.wait_for_server(timeout_sec=1.0):
            self.gripper_action_client.send_goal_async(goal)
        else:
            self.get_logger().warn("Gripper action server not available")

    # ========================================================================
    # State: LIFTING
    # ========================================================================
    
    def state_lifting(self):
        """Lift bottle off the ground."""
        elapsed = time.time() - self.state_start_time
        
        if elapsed < 0.5:
            # Send lift command
            self.lift_arm()
            self.get_logger().info("Lifting bottle...")
        elif elapsed > 3.0:
            # Lift complete
            self.get_logger().info("✓ Bottle lifted off ground!")
            self.state = State.DONE

    def lift_arm(self):
        """Move arm up to lift bottle."""
        traj = JointTrajectory()
        traj.joint_names = self.joint_names
        
        point = JointTrajectoryPoint()
        point.positions = [0.0, 0.0, 0.0, 0.0]  # Return to home position
        point.time_from_start.sec = 2
        
        traj.points = [point]
        self.joint_pub.publish(traj)

    # ========================================================================
    # State: DONE
    # ========================================================================
    
    def state_done(self):
        """Task complete."""
        self.get_logger().info("="*60)
        self.get_logger().info("TASK COMPLETE! Bottle picked successfully!")
        self.get_logger().info("="*60)
        time.sleep(1)

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
    node = BottlePickNode()
    
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
