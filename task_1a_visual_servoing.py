# Assignment 4 - Part C-a: Visual Servoing to Bottle
# Task: Align TurtleBot3 to face the bottle and keep it centered

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
import json

class BottleVisualServoing(Node):
    """
    Visual servoing node that aligns the robot to face a detected bottle.
    The robot turns left/right to keep the bottle centered in the camera view.
    """
    
    def __init__(self):
        super().__init__('bottle_visual_servoing')
        
        # Subscribe to YOLO detections
        self.subscription = self.create_subscription(
            String,
            '/yolo/detections_json',
            self.detection_callback,
            10
        )
        
        # Publisher for robot velocity commands
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # Visual servoing parameters
        self.image_width = 1280  # Camera resolution width
        self.image_center_x = self.image_width / 2  # Center of image (640)
        
        # Control parameters
        self.center_tolerance = 50  # Pixels - if bottle is within this range, consider it centered
        self.angular_speed_max = 0.5  # rad/s - maximum rotation speed
        self.kp = 0.002  # Proportional gain for PD controller
        
        # State variables
        self.bottle_detected = False
        self.bottle_center_x = 0
        
        self.get_logger().info("Visual Servoing node started. Looking for bottle...")
        self.get_logger().info(f"Image center: {self.image_center_x}, Tolerance: ±{self.center_tolerance} pixels")

    def detection_callback(self, msg):
        """
        Process YOLO detections and perform visual servoing.
        """
        try:
            data = json.loads(msg.data)
            detections = data.get("detections", [])
            
            # Look for bottle in detections
            bottle_found = False
            for det in detections:
                class_name = det["class_name"]
                confidence = det["confidence"]
                bbox = det["bbox"]
                
                # Check if this is a bottle (with good confidence)
                if class_name == "bottle" and confidence > 0.5:
                    bottle_found = True
                    self.bottle_center_x = bbox['cx']
                    self.bottle_detected = True
                    
                    # Perform visual servoing
                    self.servo_to_bottle(bbox)
                    break
            
            # If no bottle detected, stop the robot
            if not bottle_found:
                if self.bottle_detected:
                    self.get_logger().info("Bottle lost - stopping robot")
                self.bottle_detected = False
                self.stop_robot()
                
        except json.JSONDecodeError as e:
            self.get_logger().error(f"Failed to parse JSON: {e}")

    def servo_to_bottle(self, bbox):
        """
        Calculate and publish velocity commands to center the bottle.
        
        Args:
            bbox: Bounding box dictionary with 'cx', 'cy', 'w', 'h'
        """
        # Calculate error (how far from center)
        error_x = self.bottle_center_x - self.image_center_x
        
        # Create velocity command
        twist = Twist()
        twist.linear.x = 0.0  # No forward movement, only rotation
        
        # Check if bottle is centered
        if abs(error_x) < self.center_tolerance:
            # Bottle is centered - stop rotation
            twist.angular.z = 0.0
            self.get_logger().info(
                f"✓ CENTERED | Bottle at x={self.bottle_center_x:.1f}, "
                f"error={error_x:.1f}px | LOCKED ON TARGET"
            )
        else:
            # Calculate angular velocity using proportional control
            # Negative because: error > 0 means bottle is to the right, need to turn right (negative angular)
            angular_velocity = -self.kp * error_x
            
            # Limit maximum angular velocity
            angular_velocity = max(min(angular_velocity, self.angular_speed_max), -self.angular_speed_max)
            twist.angular.z = angular_velocity
            
            # Determine direction
            direction = "RIGHT" if error_x > 0 else "LEFT"
            self.get_logger().info(
                f"→ TURNING {direction} | Bottle at x={self.bottle_center_x:.1f}, "
                f"error={error_x:.1f}px, angular_vel={angular_velocity:.3f} rad/s"
            )
        
        # Publish the command
        self.cmd_vel_pub.publish(twist)

    def stop_robot(self):
        """
        Stop the robot by publishing zero velocities.
        """
        twist = Twist()
        twist.linear.x = 0.0
        twist.angular.z = 0.0
        self.cmd_vel_pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = BottleVisualServoing()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutting down visual servoing node...")
    finally:
        # Stop robot before shutting down
        node.stop_robot()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
