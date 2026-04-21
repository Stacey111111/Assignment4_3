# Sample Code for Robotics_Assignment_4 - COMPLETED
# YOLO Publisher code for Jetson NX

import rclpy
from rclpy.node import Node
from std_msgs.msg import String  
import cv2
import json  
from ultralytics import YOLO

class YoloJsonPublisher(Node):
    def __init__(self):
        ###############################################################
        # TODO 1: Initialize the Node with the name 'yolo_json_publisher'
        super().__init__('yolo_json_publisher')
        ###############################################################

        ###############################################################
        # TODO 2: Create a publisher that sends standard String messages
        self.publisher_ = self.create_publisher(String, '/yolo/detections_json', 10)
        ###############################################################
        
        # Load YOLOv11 base model onto the Jetson's GPU
        self.get_logger().info("Loading YOLOv11 model on CUDA...")
        
        ###############################################################
        # TODO 3: Select a model and optimization level
        # Using CUDA (without TensorRT for first run)
        self.model = YOLO('yolo11n.pt')
        self.model.to('cuda:0')
        
        # For TensorRT optimization (after first run):
        # self.model = YOLO('yolo11n.engine')
        ###############################################################
        
        # GStreamer pipeline for Raspberry Pi V2 Camera on Jetson CSI port
        gstreamer_pipeline = (
            "nvarguscamerasrc ! "
            "video/x-raw(memory:NVMM), width=(int)1280, height=(int)720, format=(string)NV12, framerate=(fraction)30/1 ! "
            "nvvidconv ! "
            "video/x-raw, format=(string)BGRx ! "
            "videoconvert ! "
            "video/x-raw, format=(string)BGR ! appsink"
        )
        
        self.cap = cv2.VideoCapture(gstreamer_pipeline, cv2.CAP_GSTREAMER)
        if not self.cap.isOpened():
            self.get_logger().error("Failed to open camera.")
            return
            
        ###############################################################
        # TODO 4: Create a timer that triggers callback every 0.05 seconds (20 Hz)
        self.timer = self.create_timer(0.05, self.timer_callback)
        ###############################################################

    def timer_callback(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        # Run YOLO inference
        results = self.model(frame, verbose=False)[0]

        # Initialize the dictionary to hold our data
        detection_data = {
            "timestamp": self.get_clock().now().nanoseconds / 1e9,
            "frame_id": "camera_link",
            "detections": []
        }

        # Populate the dictionary with YOLO results
        for box in results.boxes:
            x_center, y_center, width, height = box.xywh[0].tolist()
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())

            detection_data["detections"].append({
                "class_name": self.model.names[class_id],
                "confidence": confidence,
                "bbox": {"cx": x_center, "cy": y_center, "w": width, "h": height}
            })
            
        ###############################################################
        # TODO 5: Convert detection_data to JSON string
        json_str = json.dumps(detection_data)
        ###############################################################
      
        ###############################################################
        # TODO 6: Create and publish ROS 2 String message
        msg = String()
        msg.data = json_str
        self.publisher_.publish(msg)
        ###############################################################

    def destroy_node(self):
        self.cap.release()
        super().destroy_node()

def main(args=None):
    ###############################################################
    # TODO 7: Initialize ROS 2
    rclpy.init(args=args)
    ###############################################################
    
    node = YoloJsonPublisher()
    
    try:
        ###############################################################
        # TODO 8: Spin the node
        rclpy.spin(node)
        ###############################################################
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
