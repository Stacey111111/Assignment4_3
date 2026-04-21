#!/usr/bin/env python3
"""
手臂位置交互测试工具
用于找到并记录最佳的预抓取位置

使用方法：
1. python3 test_arm_positions.py
2. 输入关节角度测试
3. 记录满意的位置
"""

import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
import time

class ArmPositionTester(Node):
    def __init__(self):
        super().__init__('arm_position_tester')
        
        # Publisher for arm control
        self.joint_pub = self.create_publisher(
            JointTrajectory,
            '/arm_controller/joint_trajectory',
            10
        )
        
        # Common positions
        self.presets = {
            'home': [0.0, 0.0, 0.0, 0.0],
            'low': [0.0, -0.5, 0.8, 0.3],
            'medium': [0.0, -0.3, 0.6, 0.2],
            'high': [0.0, -0.1, 0.4, 0.1],
            'place': [0.0, -0.6, 0.9, 0.4],
        }
        
        self.get_logger().info("手臂位置测试工具已启动")
        
    def move_to_position(self, j1, j2, j3, j4, duration=3.0):
        """
        Move arm to specified joint positions.
        
        Args:
            j1, j2, j3, j4: Joint angles in radians
            duration: Time to complete movement (seconds)
        """
        traj = JointTrajectory()
        traj.joint_names = ['joint1', 'joint2', 'joint3', 'joint4']
        
        point = JointTrajectoryPoint()
        point.positions = [j1, j2, j3, j4]
        point.time_from_start.sec = int(duration)
        point.time_from_start.nanosec = int((duration - int(duration)) * 1e9)
        
        traj.points = [point]
        self.joint_pub.publish(traj)
        
        self.get_logger().info(
            f'移动到: [j1={j1:.2f}, j2={j2:.2f}, j3={j3:.2f}, j4={j4:.2f}]'
        )
        
        # Wait for movement to complete
        time.sleep(duration + 0.5)
        
    def show_menu(self):
        """Display interactive menu."""
        print("\n" + "="*70)
        print("🤖 手臂位置测试工具 - Open Manipulator X")
        print("="*70)
        print("\n⚠️  安全提示：")
        print("  - 确保机器人周围安全")
        print("  - 第一次使用慢速移动")
        print("  - 准备好紧急停止")
        print("\n" + "="*70)
        
        while rclpy.ok():
            print("\n" + "-"*70)
            print("选择操作：")
            print("  1. 使用预设位置")
            print("  2. 输入自定义位置")
            print("  3. 显示当前关节状态（需要另一个终端运行）")
            print("  4. 测试所有预设位置")
            print("  q. 退出")
            print("-"*70)
            
            choice = input("\n请选择 (1/2/3/4/q): ").strip()
            
            if choice == '1':
                self.use_preset()
            elif choice == '2':
                self.custom_position()
            elif choice == '3':
                self.show_joint_state_help()
            elif choice == '4':
                self.test_all_presets()
            elif choice.lower() == 'q':
                print("\n退出程序...")
                break
            else:
                print("❌ 无效选择")
    
    def use_preset(self):
        """Use predefined positions."""
        print("\n预设位置：")
        print("  home   - Home位置 [0.0, 0.0, 0.0, 0.0]")
        print("  low    - 低位预抓取 [0.0, -0.5, 0.8, 0.3]")
        print("  medium - 中位预抓取 [0.0, -0.3, 0.6, 0.2]")
        print("  high   - 高位预抓取 [0.0, -0.1, 0.4, 0.1]")
        print("  place  - 放置位置 [0.0, -0.6, 0.9, 0.4]")
        
        name = input("\n输入预设名称: ").strip().lower()
        
        if name in self.presets:
            pos = self.presets[name]
            print(f"\n移动到 '{name}': {pos}")
            
            try:
                duration = float(input("移动时长 (秒, 默认3.0): ") or "3.0")
            except ValueError:
                duration = 3.0
            
            self.move_to_position(pos[0], pos[1], pos[2], pos[3], duration)
            
            print("\n✓ 移动完成")
            print(f"当前位置: {pos}")
            
            save = input("\n保存这个位置？(y/n): ")
            if save.lower() == 'y':
                self.save_position(pos)
        else:
            print(f"❌ 预设 '{name}' 不存在")
    
    def custom_position(self):
        """Input custom joint positions."""
        print("\n" + "="*70)
        print("输入自定义关节角度")
        print("="*70)
        print("\n关节范围：")
        print("  joint1 (基座): -3.14 到 3.14 (不转动通常用 0.0)")
        print("  joint2 (肩部): -1.57 到 1.57 (负值向下)")
        print("  joint3 (肘部): -1.57 到 1.57 (正值弯曲)")
        print("  joint4 (手腕): -1.57 到 1.57 (正值向下)")
        print("\n输入格式: j1 j2 j3 j4")
        print("例如: 0 -0.5 0.8 0.3")
        print("-"*70)
        
        user_input = input("\n关节角度: ").strip()
        
        try:
            values = [float(x) for x in user_input.split()]
            
            if len(values) != 4:
                print(f"❌ 错误：需要 4 个数值，您输入了 {len(values)} 个")
                return
            
            # Validate ranges
            if not (-3.14 <= values[0] <= 3.14):
                print("❌ joint1 超出范围")
                return
            if not all(-1.57 <= v <= 1.57 for v in values[1:]):
                print("❌ joint2/3/4 超出范围")
                return
            
            print(f"\n将移动到: {values}")
            confirm = input("确认？(y/n): ")
            
            if confirm.lower() == 'y':
                try:
                    duration = float(input("移动时长 (秒, 默认3.0): ") or "3.0")
                except ValueError:
                    duration = 3.0
                
                self.move_to_position(values[0], values[1], values[2], values[3], duration)
                
                print("\n✓ 移动完成")
                print(f"当前位置: {values}")
                
                save = input("\n保存这个位置？(y/n): ")
                if save.lower() == 'y':
                    self.save_position(values)
            
        except ValueError:
            print("❌ 输入格式错误")
    
    def show_joint_state_help(self):
        """Show instructions for reading joint states."""
        print("\n" + "="*70)
        print("查看当前关节状态")
        print("="*70)
        print("\n在另一个终端运行：")
        print("  ros2 topic echo /joint_states")
        print("\n您会看到：")
        print("""
  name:
  - joint1
  - joint2
  - joint3
  - joint4
  - gripper
  position:
  - 0.001234      # joint1 ≈ 0.00
  - -0.501234     # joint2 ≈ -0.50
  - 0.802345      # joint3 ≈ 0.80
  - 0.300123      # joint4 ≈ 0.30
  - 0.01
        """)
        print("\n记录 position 的前 4 个数值！")
        print("="*70)
        
        input("\n按 Enter 继续...")
    
    def test_all_presets(self):
        """Test all preset positions sequentially."""
        print("\n" + "="*70)
        print("测试所有预设位置")
        print("="*70)
        print("\n⚠️  机器人将依次移动到所有预设位置")
        print("   观察哪个位置最适合您的应用")
        
        confirm = input("\n继续？(y/n): ")
        if confirm.lower() != 'y':
            return
        
        order = ['home', 'low', 'medium', 'high', 'place', 'home']
        
        for name in order:
            pos = self.presets[name]
            print("\n" + "-"*70)
            print(f"📍 位置: {name.upper()}")
            print(f"   关节: {pos}")
            print("-"*70)
            
            self.move_to_position(pos[0], pos[1], pos[2], pos[3], 3.0)
            
            if name != 'home' or order.index(name) == 0:
                response = input("\n这个位置好吗？(y/n/s保存/q退出): ")
                if response.lower() == 'q':
                    break
                elif response.lower() == 's':
                    self.save_position(pos)
        
        print("\n✓ 测试完成")
    
    def save_position(self, position):
        """Save position to a file."""
        name = input("给这个位置命名: ").strip()
        
        if not name:
            print("❌ 未保存：名称不能为空")
            return
        
        try:
            with open('saved_arm_positions.txt', 'a') as f:
                f.write(f"\n{name}: {position}\n")
                f.write(f"# point.positions = {position}\n")
            
            print(f"\n✓ 已保存到 saved_arm_positions.txt")
            print(f"   名称: {name}")
            print(f"   位置: {position}")
            print(f"\n在代码中使用：")
            print(f"   point.positions = {position}")
            
        except Exception as e:
            print(f"❌ 保存失败: {e}")


def main():
    rclpy.init()
    node = ArmPositionTester()
    
    try:
        node.show_menu()
    except KeyboardInterrupt:
        print("\n\n⚠️  程序被中断")
    finally:
        # Return to home position
        print("\n返回 Home 位置...")
        node.move_to_position(0.0, 0.0, 0.0, 0.0, 3.0)
        
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
