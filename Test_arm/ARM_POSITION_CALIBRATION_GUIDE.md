# 手臂位置校准指南 - 如何找到并记录预抓取位置

## 📚 目录

1. [方法概览](#方法概览)
2. [方法 1：使用 RQT GUI 工具（最简单）](#方法-1使用-rqt-gui-工具最简单)
3. [方法 2：使用命令行发送位置](#方法-2使用命令行发送位置)
4. [方法 3：手动移动并读取（推荐）](#方法-3手动移动并读取推荐)
5. [常用预设位置](#常用预设位置)
6. [测试和验证](#测试和验证)

---

## 方法概览

| 方法 | 难度 | 推荐度 | 工具 |
|------|------|--------|------|
| **RQT GUI** | ⭐ 简单 | ⭐⭐⭐⭐⭐ | rqt_joint_trajectory_controller |
| **命令行** | ⭐⭐ 中等 | ⭐⭐⭐ | ros2 topic pub |
| **手动移动** | ⭐⭐⭐ 复杂 | ⭐⭐⭐⭐ | ros2 topic echo |

---

## 方法 1：使用 RQT GUI 工具（最简单）

### 步骤 1：启动 RQT Joint Trajectory Controller

```bash
# 在 Remote-PC 或 Jetson 上运行
rqt
```

或者直接启动插件：
```bash
rqt_joint_trajectory_controller
```

### 步骤 2：在 RQT 中加载插件

如果直接运行 `rqt`：
1. 点击菜单：`Plugins` → `Robot Tools` → `Joint trajectory controller`
2. 在 `Controller Manager` 下拉菜单中选择：`/arm_controller`
3. 点击 `Load`

### 步骤 3：使用滑块移动手臂

您会看到 4 个滑块：

```
joint1 (base)     [----●--------]  -3.14 to 3.14
joint2 (shoulder) [----●--------]  -1.57 to 1.57
joint3 (elbow)    [----●--------]  -1.57 to 1.57
joint4 (wrist)    [----●--------]  -1.57 to 1.57
```

**操作：**
1. **慢慢拖动滑块**移动每个关节
2. **观察实际机器人**的手臂位置
3. **找到合适的预抓取位置**（夹爪刚好在瓶子上方/前方）
4. **记录每个滑块的数值**

### 步骤 4：记录关节角度

在 RQT 界面上，每个滑块旁边会显示**当前数值**：

```
joint1: 0.00 rad
joint2: -0.50 rad
joint3: 0.80 rad
joint4: 0.30 rad
```

**把这些数值记录下来！**

### 步骤 5：更新代码

```python
# 在 task_1b_pick_bottle.py 或 task_2_pick_and_place.py
# 找到 move_arm_to_grasp_position() 函数

point.positions = [0.0, -0.5, 0.8, 0.3]  # 旧的值
                   ↓
point.positions = [0.0, -0.50, 0.80, 0.30]  # 你记录的值
```

---

## 方法 2：使用命令行发送位置

### 步骤 1：准备测试脚本

创建一个测试文件 `test_arm_position.py`：

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

class ArmPositionTester(Node):
    def __init__(self):
        super().__init__('arm_position_tester')
        self.joint_pub = self.create_publisher(
            JointTrajectory,
            '/arm_controller/joint_trajectory',
            10
        )
        
    def move_to_position(self, j1, j2, j3, j4, duration=2.0):
        """移动手臂到指定位置"""
        traj = JointTrajectory()
        traj.joint_names = ['joint1', 'joint2', 'joint3', 'joint4']
        
        point = JointTrajectoryPoint()
        point.positions = [j1, j2, j3, j4]
        point.time_from_start.sec = int(duration)
        point.time_from_start.nanosec = int((duration - int(duration)) * 1e9)
        
        traj.points = [point]
        self.joint_pub.publish(traj)
        
        self.get_logger().info(f'Moving to: [{j1:.2f}, {j2:.2f}, {j3:.2f}, {j4:.2f}]')

def main():
    rclpy.init()
    node = ArmPositionTester()
    
    print("\n" + "="*60)
    print("手臂位置测试工具")
    print("="*60)
    
    while True:
        print("\n输入关节角度 (用空格分隔) 或 'q' 退出")
        print("格式: joint1 joint2 joint3 joint4")
        print("例如: 0 -0.5 0.8 0.3")
        
        user_input = input("\n> ")
        
        if user_input.lower() == 'q':
            break
            
        try:
            values = [float(x) for x in user_input.split()]
            if len(values) != 4:
                print("错误：需要 4 个数值")
                continue
                
            node.move_to_position(values[0], values[1], values[2], values[3])
            
        except ValueError:
            print("错误：输入无效")
    
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

### 步骤 2：运行测试脚本

```bash
chmod +x test_arm_position.py
python3 test_arm_position.py
```

### 步骤 3：尝试不同位置

```
> 0 0 0 0          # 首先回到 home 位置
> 0 -0.3 0.5 0.2   # 尝试一个位置
> 0 -0.5 0.8 0.3   # 尝试另一个位置
> 0 -0.7 1.0 0.4   # 再尝试一个
```

**观察哪个位置最适合抓取瓶子！**

### 步骤 4：记录最佳位置

找到最佳位置后，记录数值并更新代码。

---

## 方法 3：手动移动并读取（推荐）

### 步骤 1：启动关节状态监听

```bash
# Terminal 1：监听关节状态
ros2 topic echo /joint_states
```

您会看到：
```yaml
header:
  stamp:
    sec: 1234567890
    nanosec: 123456789
  frame_id: ''
name:
- joint1
- joint2
- joint3
- joint4
- gripper
position:
- 0.0
- -0.5012345
- 0.8023456
- 0.3001234
- 0.01
velocity: [...]
effort: [...]
```

### 步骤 2：手动移动手臂（物理方式）

**⚠️ 注意安全！**

有两种方法：

#### 方法 A：使用示教模式（如果可用）

```bash
# 进入示教模式（torque off）
ros2 service call /set_actuator_state open_manipulator_msgs/srv/SetActuatorState "{set_actuator_state: false}"
```

现在可以手动移动手臂了！

#### 方法 B：使用 GUI 控制器

```bash
# 启动 Open Manipulator 控制器
ros2 run open_manipulator_x_teleop open_manipulator_x_teleop_keyboard
```

使用键盘控制手臂到合适位置。

### 步骤 3：读取并记录关节角度

当手臂在好位置时，查看 Terminal 1 的输出：

```yaml
position:
- 0.001234      # joint1 ≈ 0.00
- -0.501234     # joint2 ≈ -0.50
- 0.802345      # joint3 ≈ 0.80
- 0.300123      # joint4 ≈ 0.30
```

**记录这些数值（四舍五入到小数点后2位）：**
```
joint1: 0.00
joint2: -0.50
joint3: 0.80
joint4: 0.30
```

### 步骤 4：退出示教模式

```bash
# 重新启用力矩（torque on）
ros2 service call /set_actuator_state open_manipulator_msgs/srv/SetActuatorState "{set_actuator_state: true}"
```

### 步骤 5：更新代码

```python
point.positions = [0.00, -0.50, 0.80, 0.30]
```

---

## 常用预设位置

### 预抓取位置（低位 - 抓地面上的瓶子）

```python
# 低位预抓取
point.positions = [0.0, -0.5, 0.8, 0.3]
#                  │     │     │    │
#                  │     │     │    └─ 手腕向下倾斜
#                  │     │     └─ 肘部弯曲向下
#                  │     └─ 肩部向下
#                  └─ 基座不转

# 描述：
# - 夹爪指向地面
# - 适合抓取地面上的物体
# - 高度约 5-10 cm
```

### 预抓取位置（中位）

```python
# 中位预抓取
point.positions = [0.0, -0.3, 0.6, 0.2]

# 描述：
# - 夹爪在中等高度
# - 适合抓取桌面上的物体
# - 高度约 15-20 cm
```

### 预抓取位置（高位）

```python
# 高位预抓取
point.positions = [0.0, -0.1, 0.4, 0.1]

# 描述：
# - 夹爪在较高位置
# - 适合抓取架子上的物体
# - 高度约 25-30 cm
```

### Home 位置（收起）

```python
# Home 位置
point.positions = [0.0, 0.0, 0.0, 0.0]

# 描述：
# - 所有关节归零
# - 手臂垂直向上
# - 安全的初始/结束位置
```

### 放置位置

```python
# 放置位置（与预抓取类似，但稍微降低）
point.positions = [0.0, -0.6, 0.9, 0.4]

# 描述：
# - 比预抓取稍低一点
# - 确保瓶子接触地面
```

---

## 测试和验证

### 创建完整测试脚本

创建 `test_all_positions.py`：

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
import time

class PositionTester(Node):
    def __init__(self):
        super().__init__('position_tester')
        self.joint_pub = self.create_publisher(
            JointTrajectory,
            '/arm_controller/joint_trajectory',
            10
        )
        
    def move_to(self, name, positions, duration=3.0):
        """移动到指定位置"""
        print(f"\n移动到: {name}")
        print(f"位置: {positions}")
        
        traj = JointTrajectory()
        traj.joint_names = ['joint1', 'joint2', 'joint3', 'joint4']
        
        point = JointTrajectoryPoint()
        point.positions = positions
        point.time_from_start.sec = int(duration)
        
        traj.points = [point]
        self.joint_pub.publish(traj)
        
        time.sleep(duration + 0.5)

def main():
    rclpy.init()
    node = PositionTester()
    
    # 定义测试位置
    positions = {
        'Home': [0.0, 0.0, 0.0, 0.0],
        'Pre-grasp (Low)': [0.0, -0.5, 0.8, 0.3],
        'Pre-grasp (Medium)': [0.0, -0.3, 0.6, 0.2],
        'Pre-grasp (High)': [0.0, -0.1, 0.4, 0.1],
    }
    
    print("\n" + "="*60)
    print("测试预设手臂位置")
    print("="*60)
    print("\n⚠️  确保机器人周围安全！")
    input("按 Enter 继续...")
    
    try:
        for name, pos in positions.items():
            node.move_to(name, pos)
            
            print(f"\n当前位置: {name}")
            print(f"关节角度: {pos}")
            
            response = input("这个位置好吗？(y/n/q退出): ")
            if response.lower() == 'q':
                break
            elif response.lower() == 'y':
                print(f"✓ 记录这个位置：{pos}")
        
        # 返回 Home
        print("\n返回 Home 位置...")
        node.move_to('Home', [0.0, 0.0, 0.0, 0.0])
        
    except KeyboardInterrupt:
        print("\n中断")
    
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

### 运行测试

```bash
python3 test_all_positions.py
```

程序会依次移动到每个预设位置，您可以评估哪个最好。

---

## 实战示例：找到最佳预抓取位置

### 完整流程

```bash
# Step 1：启动机器人
# [确保 TurtleBot 和手臂已启动]

# Step 2：放置瓶子
# [在机器人前方地面上放一个瓶子]

# Step 3：运行测试脚本
python3 test_all_positions.py

# Step 4：观察每个位置
# 当手臂移动到各个位置时：
# - 夹爪是否在瓶子正上方？
# - 夹爪高度是否合适？
# - 夹爪方向是否正确？

# Step 5：记录最佳位置
# 例如：Pre-grasp (Low) = [0.0, -0.5, 0.8, 0.3] ✓

# Step 6：微调（可选）
# 使用 RQT 或测试工具微调：
# - joint2 太高？改为 -0.6
# - joint3 太直？改为 0.9

# Step 7：更新代码
# 在 task_1b_pick_bottle.py:
point.positions = [0.0, -0.5, 0.8, 0.3]  # 你找到的最佳值
```

---

## 关节角度理解

### 各关节的作用

```
joint1 (Base Rotation - 基座旋转)
  -π ← [●] → +π
  左转     右转
  
joint2 (Shoulder - 肩部)
  -π/2 ← [●] → +π/2
  向下      向上
  
joint3 (Elbow - 肘部)
  -π/2 ← [●] → +π/2
  伸直      弯曲
  
joint4 (Wrist - 手腕)
  -π/2 ← [●] → +π/2
  向上      向下
```

### 典型抓取位置的关节配置

```
低位抓取（地面）：
  joint1 = 0.0    (不转)
  joint2 = -0.5   (肩部向下)
  joint3 = 0.8    (肘部弯曲)
  joint4 = 0.3    (手腕向下)
  
中位抓取（桌面）：
  joint1 = 0.0    (不转)
  joint2 = -0.3   (肩部稍微向下)
  joint3 = 0.6    (肘部中等弯曲)
  joint4 = 0.2    (手腕稍微向下)
  
高位抓取（架子）：
  joint1 = 0.0    (不转)
  joint2 = -0.1   (肩部几乎水平)
  joint3 = 0.4    (肘部稍微弯曲)
  joint4 = 0.1    (手腕几乎水平)
```

---

## 安全提示

### ⚠️ 注意事项

1. **缓慢移动**
   - 首次测试时使用较长的 duration（3-5 秒）
   - 观察手臂运动轨迹

2. **检查碰撞**
   - 确保手臂不会撞到机器人本体
   - 确保手臂不会撞到地面
   - 确保夹爪有足够空间

3. **紧急停止**
   - 准备好紧急停止按钮
   - 或随时准备 Ctrl+C

4. **工作空间**
   - 了解手臂的工作范围
   - 不要超出关节限位

---

## 总结

### 推荐工作流程

```
1. 使用 RQT GUI 工具
   ↓ 找到大致位置
   
2. 使用测试脚本微调
   ↓ 测试不同数值
   
3. 记录最佳位置
   ↓ 写下关节角度
   
4. 更新代码
   ↓ 在实际任务中使用
   
5. 实际测试
   ↓ 运行完整任务验证
```

### 快速记录表

```
测试位置记录表：

位置1: [_____, _____, _____, _____] 评价: □好 □中 □差
位置2: [_____, _____, _____, _____] 评价: □好 □中 □差
位置3: [_____, _____, _____, _____] 评价: □好 □中 □差

最终选择: [_____, _____, _____, _____]

备注：
_______________________________________________________
_______________________________________________________
```

---

**现在您知道如何找到并记录最佳手臂位置了！** 🎯

**记得多尝试、多测试，找到最适合您机器人的配置！** 🤖
