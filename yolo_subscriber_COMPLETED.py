# Sample Code for Robotics_Assignment_4 - COMPLETED
# YOLO Subscriber code for Jetson NX or Remote PC

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json

class YoloJsonSubscriber(Node):
    def __init__(self):
        ###############################################################
        # TODO 1: Initialize the Node
        super().__init__('yolo_json_subscriber')
        ###############################################################

        ###############################################################
        # TODO 2: Create a subscriber
        self.subscription = self.create_subscription(
            String,
            '/yolo/detections_json',
            self.detection_callback,
            10
        )
        ###############################################################
      
        self.get_logger().info("Listening for YOLO JSON detections...")

    def detection_callback(self, msg):
        try:
            ###############################################################
            # TODO 3: Parse JSON string to Python dictionary
            data = json.loads(msg.data)
            ###############################################################
            
            # Extract the metadata
            timestamp = data.get("timestamp", 0.0)
            frame_id = data.get("frame_id", "unknown")
            detections = data.get("detections", [])
            
            self.get_logger().info(f"Received {len(detections)} detections:")
            
            # Iterate through the detection list
            for i, det in enumerate(detections):
                ###############################################################
                # TODO 4: Extract values from det dictionary
                class_name = det["class_name"]
                score = det["confidence"]
                bbox = det["bbox"]
                ###############################################################
                
                self.get_logger().info(
                    f"  [{i}] {class_name} ({score:.2f}) | "
                    f"Center: ({bbox['cx']:.1f}, {bbox['cy']:.1f}), "
                    f"Size: {bbox['w']:.1f}x{bbox['h']:.1f}"
                )
                
        except json.JSONDecodeError as e:
            self.get_logger().error(f"Failed to parse JSON string: {e}")

def main(args=None):
    ###############################################################
    # TODO 5: Initialize ROS 2
    rclpy.init(args=args)
    ###############################################################
    
    node = YoloJsonSubscriber()
    
    try:
        ###############################################################
        # TODO 6: Spin the node
        rclpy.spin(node)
        ###############################################################
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
