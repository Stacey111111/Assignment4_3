#!/usr/bin/env python3
"""
快速手臂位置测试脚本
快速测试几个预设位置，找到最佳抓取姿态

使用方法：
python3 quick_position_test.py
"""

import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
import time

class QuickTester(Node):
    def __init__(self):
        super().__init__('quick_position_tester')
        self.joint_pub = self.create_publisher(
            JointTrajectory,
            '/arm_controller/joint_trajectory',
            10
        )
        
    def move(self, name, j1, j2, j3, j4, duration=3.0):
        """Move arm to position and wait."""
        traj = JointTrajectory()
        traj.joint_names = ['joint1', 'joint2', 'joint3', 'joint4']
        
        point = JointTrajectoryPoint()
        point.positions = [j1, j2, j3, j4]
        point.time_from_start.sec = int(duration)
        point.time_from_start.nanosec = int((duration - int(duration)) * 1e9)
        
        traj.points = [point]
        self.joint_pub.publish(traj)
        
        print(f"\n{'='*60}")
        print(f"📍 {name}")
        print(f"{'='*60}")
        print(f"关节角度: [{j1:.2f}, {j2:.2f}, {j3:.2f}, {j4:.2f}]")
        print(f"移动中... ({duration}秒)")
        
        time.sleep(duration + 0.5)
        print("✓ 到达位置")


def main():
    rclpy.init()
    node = QuickTester()
    
    print("\n" + "="*60)
    print("🤖 快速手臂位置测试")
    print("="*60)
    print("\n这个脚本会测试几个常用的预抓取位置")
    print("观察哪个位置最适合抓取您的瓶子")
    print("\n⚠️  确保：")
    print("  1. 机器人周围安全")
    print("  2. 瓶子放在机器人前方地面")
    print("  3. 准备好记录最佳位置")
    
    input("\n按 Enter 开始测试...")
    
    # Define test positions
    positions = [
        ("Home (起始位置)", 0.0, 0.0, 0.0, 0.0),
        ("Low Grasp 1 (低位1)", 0.0, -0.5, 0.8, 0.3),
        ("Low Grasp 2 (低位2)", 0.0, -0.6, 0.9, 0.4),
        ("Low Grasp 3 (低位3)", 0.0, -0.4, 0.7, 0.2),
        ("Medium Grasp (中位)", 0.0, -0.3, 0.6, 0.2),
        ("High Grasp (高位)", 0.0, -0.1, 0.4, 0.1),
    ]
    
    saved_positions = []
    
    try:
        for name, j1, j2, j3, j4 in positions:
            node.move(name, j1, j2, j3, j4)
            
            # Ask user
            print("\n" + "-"*60)
            response = input("这个位置好吗？(y=好/n=不好/s=保存/q=退出): ").strip().lower()
            
            if response == 'q':
                print("\n提前退出测试")
                break
            elif response == 'y' or response == 's':
                print(f"✓ 标记为好位置: {name}")
                saved_positions.append((name, [j1, j2, j3, j4]))
                if response == 's':
                    print("  (已保存)")
            elif response == 'n':
                print(f"✗ 跳过: {name}")
            
            time.sleep(0.5)
        
        # Return to home
        print("\n" + "="*60)
        print("测试完成，返回 Home 位置")
        print("="*60)
        node.move("Home (返回)", 0.0, 0.0, 0.0, 0.0)
        
        # Show summary
        print("\n" + "="*60)
        print("📊 测试总结")
        print("="*60)
        
        if saved_positions:
            print("\n您标记的好位置：")
            for i, (name, pos) in enumerate(saved_positions, 1):
                print(f"\n{i}. {name}")
                print(f"   关节角度: {pos}")
                print(f"   代码: point.positions = {pos}")
        else:
            print("\n没有保存任何位置")
        
        # Save to file
        if saved_positions:
            save = input("\n保存到文件？(y/n): ").strip().lower()
            if save == 'y':
                with open('quick_test_results.txt', 'w') as f:
                    f.write("手臂位置测试结果\n")
                    f.write("="*60 + "\n\n")
                    for name, pos in saved_positions:
                        f.write(f"{name}:\n")
                        f.write(f"  关节角度: {pos}\n")
                        f.write(f"  代码: point.positions = {pos}\n\n")
                print("✓ 已保存到 quick_test_results.txt")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被中断")
        print("返回 Home 位置...")
        node.move("Home (安全)", 0.0, 0.0, 0.0, 0.0)
    
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
