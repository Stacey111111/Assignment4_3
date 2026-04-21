# Assignment 4 - Parameter Configuration Guide

## 📋 All Configurable Parameters

This document lists ALL parameters you can adjust in each file, with explanations and recommended ranges.

---

## yolo_publisher_COMPLETED.py

### Model Selection

```python
# Line ~35
self.model = YOLO('yolo11n.pt')  # Nano model (fastest)
self.model.to('cuda:0')
```

**Options:**
- `yolo11n.pt` - Nano (fastest, least accurate)
- `yolo11s.pt` - Small
- `yolo11m.pt` - Medium
- `yolo11l.pt` - Large (slowest, most accurate)

**TensorRT Engine (after first run):**
```python
self.model = YOLO('yolo11n.engine')  # Optimized
```

### Timer Rate

```python
# Line ~48
self.timer = self.create_timer(0.05, self.timer_callback)  # 20 Hz
```

**Options:**
- `0.05` = 20 Hz (recommended)
- `0.033` = 30 Hz (faster, more CPU)
- `0.1` = 10 Hz (slower, less CPU)

---

## task_1a_visual_servoing.py

### Image Parameters

```python
# Line ~23-24
self.image_width = 1280
self.image_center_x = self.image_width / 2  # 640
```

**Must match camera resolution!**

### Centering Tolerance

```python
# Line ~27
self.center_tolerance = 50  # pixels
```

**Range:** 20 - 100
- **Smaller (20-30):** More precise, slower convergence
- **Medium (50):** Balanced (recommended)
- **Larger (70-100):** Faster, less precise

### Maximum Angular Speed

```python
# Line ~28
self.angular_speed_max = 0.5  # rad/s
```

**Range:** 0.2 - 0.8
- **0.2-0.3:** Slow, very stable
- **0.4-0.5:** Moderate (recommended)
- **0.6-0.8:** Fast, may oscillate

### Proportional Gain

```python
# Line ~29
self.kp = 0.002
```

**Range:** 0.0005 - 0.005
- **0.0005-0.001:** Low gain, slow response
- **0.002:** Moderate (recommended)
- **0.003-0.005:** High gain, fast but may oscillate

**Tuning formula:**
```
If oscillating: kp = current_kp * 0.5
If too slow: kp = current_kp * 1.5
```

---

## task_1b_pick_bottle.py

### Image Parameters

```python
# Line ~40-43
self.image_width = 1280
self.image_height = 720
self.image_center_x = self.image_width / 2
self.image_center_y = self.image_height / 2
```

### Centering Parameters

```python
# Line ~51-53
self.center_tolerance_x = 50  # pixels
self.angular_speed_max = 0.3  # rad/s
self.kp_angular = 0.002
```

Same as task_1a, but more conservative defaults.

### ⚠️ CRITICAL: Approaching Parameters

```python
# Line ~56
self.target_bbox_area = 80000  # pixels²
```

**THIS IS THE MOST IMPORTANT PARAMETER TO CALIBRATE!**

**Calibration procedure:**
1. Run `yolo_subscriber_COMPLETED.py`
2. Manually drive robot to good grasping distance
3. Note: `Size: 250.0x320.0` → Area = 250 × 320
4. Set `target_bbox_area = calculated_area`

**Typical ranges:**
- Small bottle, close: 60,000 - 80,000
- Medium bottle, medium: 80,000 - 100,000
- Large bottle, far: 100,000 - 150,000

```python
# Line ~57
self.bbox_area_tolerance = 5000  # pixels²
```

**Range:** 3,000 - 10,000
- Smaller: More precise stopping
- Larger: More forgiving

```python
# Line ~58-59
self.linear_speed = 0.1  # m/s
self.kp_linear = 0.000005
```

**linear_speed range:** 0.05 - 0.2 m/s
**kp_linear range:** 0.000003 - 0.00001

### State Timing

```python
# In state functions:
# POSITIONING_ARM: elapsed > 3.0
# GRASPING: elapsed > 2.0
# LIFTING: elapsed > 3.0
```

**Adjustable ranges:**
- POSITIONING_ARM: 2.0 - 5.0 seconds
- GRASPING: 1.5 - 3.0 seconds
- LIFTING: 2.0 - 4.0 seconds

### Arm Positions

```python
# Line ~201 (move_arm_to_grasp_position)
point.positions = [0.0, -0.5, 0.8, 0.3]
```

**Joint ranges (Open Manipulator X):**
- joint1 (base): -π to +π
- joint2 (shoulder): -π/2 to +π/2
- joint3 (elbow): -π/2 to +π/2
- joint4 (wrist): -π/2 to +π/2

**Common presets:**
```python
# Pre-grasp (low)
[0.0, -0.5, 0.8, 0.3]

# Pre-grasp (medium)
[0.0, -0.4, 0.7, 0.2]

# Pre-grasp (high)
[0.0, -0.3, 0.6, 0.1]

# Home position
[0.0, 0.0, 0.0, 0.0]
```

### Gripper Values

```python
# Line ~223 (close_gripper)
goal.value = -0.01  # Close
```

**Range:** -0.03 to -0.005
- **-0.005 to -0.01:** Light grip
- **-0.01 to -0.015:** Medium grip (recommended)
- **-0.015 to -0.03:** Strong grip

**Finding optimal value:**
1. Test with different values
2. Gripper should close but not strain
3. Should hold bottle securely

---

## task_2_pick_and_place.py

### All parameters from task_1b, PLUS:

### Navigation Parameters

```python
# Line ~65-68
self.position_tolerance = 0.1  # meters
self.angle_tolerance = 0.2  # radians
self.nav_linear_speed = 0.15  # m/s
self.nav_angular_speed = 0.3  # rad/s
```

**position_tolerance:**
- **Range:** 0.05 - 0.3 meters
- **0.05-0.1:** Precise positioning
- **0.15-0.2:** Moderate (recommended)
- **0.2-0.3:** Loose tolerance

**angle_tolerance:**
- **Range:** 0.1 - 0.5 radians
- **0.1-0.15:** Precise alignment
- **0.2-0.3:** Moderate (recommended)
- **0.3-0.5:** Loose tolerance

**nav_linear_speed:**
- **Range:** 0.1 - 0.3 m/s
- **0.1:** Slow, safe
- **0.15:** Moderate (recommended)
- **0.2-0.3:** Fast

**nav_angular_speed:**
- **Range:** 0.2 - 0.5 rad/s
- **0.2:** Slow rotation
- **0.3:** Moderate (recommended)
- **0.4-0.5:** Fast rotation

### Gripper Opening

```python
# Line ~396 (open_gripper)
goal.value = 0.01  # Open
```

**Range:** 0.005 to 0.03
- **0.005-0.01:** Slightly open
- **0.01-0.015:** Medium open (recommended)
- **0.015-0.03:** Fully open

---

## Complete Parameter Summary Table

| Parameter | File | Line | Default | Range | Critical? |
|-----------|------|------|---------|-------|-----------|
| `target_bbox_area` | task_1b, task_2 | ~56 | 80000 | 50k-150k | ⭐⭐⭐⭐⭐ |
| `center_tolerance_x` | task_1a, 1b, 2 | ~27,51 | 50 | 20-100 | ⭐⭐⭐ |
| `kp_angular` | task_1a, 1b, 2 | ~29,53 | 0.002 | 0.0005-0.005 | ⭐⭐⭐ |
| `angular_speed_max` | task_1a, 1b, 2 | ~28,52 | 0.3-0.5 | 0.2-0.8 | ⭐⭐ |
| `linear_speed` | task_1b, 2 | ~58 | 0.1 | 0.05-0.2 | ⭐⭐ |
| `kp_linear` | task_1b, 2 | ~59 | 0.000005 | 0.000003-0.00001 | ⭐⭐ |
| `arm positions` | task_1b, 2 | ~201 | [0,-0.5,0.8,0.3] | varies | ⭐⭐⭐⭐ |
| `gripper close` | task_1b, 2 | ~223 | -0.01 | -0.03 to -0.005 | ⭐⭐⭐ |
| `gripper open` | task_2 | ~396 | 0.01 | 0.005-0.03 | ⭐⭐ |
| `position_tolerance` | task_2 | ~65 | 0.1 | 0.05-0.3 | ⭐⭐⭐ |
| `nav_linear_speed` | task_2 | ~67 | 0.15 | 0.1-0.3 | ⭐⭐ |

**Legend:**
- ⭐⭐⭐⭐⭐: Must calibrate
- ⭐⭐⭐⭐: Should calibrate
- ⭐⭐⭐: Nice to tune
- ⭐⭐: Optional tuning

---

## Step-by-Step Calibration Procedure

### 1. Calibrate target_bbox_area (REQUIRED)

```bash
# Terminal 1
python3 yolo_publisher_COMPLETED.py

# Terminal 2
python3 yolo_subscriber_COMPLETED.py

# Terminal 3
ros2 run turtlebot3_teleop teleop_keyboard
```

1. Drive robot to where you want it to stop for grasping
2. Look at subscriber output: `Size: W x H`
3. Calculate: `Area = W × H`
4. Update in code: `self.target_bbox_area = Area`

### 2. Test centering (if needed)

Run task_1a:
- Too much oscillation? → Reduce `kp_angular`
- Too slow? → Increase `kp_angular`
- Still oscillates? → Reduce `angular_speed_max`

### 3. Test approaching (if needed)

Run task_1b:
- Too much oscillation? → Reduce `kp_linear`
- Too slow? → Increase `linear_speed`

### 4. Test arm positions (if needed)

Run task_1b:
- Gripper too high? → Increase joint2 (more negative)
- Gripper too low? → Decrease joint2 (less negative)
- Can't reach? → Increase joint3

### 5. Test gripper (if needed)

Run task_1b:
- Doesn't close enough? → More negative value
- Too tight? → Less negative value

### 6. Test navigation (if needed)

Run task_2:
- Doesn't reach home? → Increase `position_tolerance`
- Spins too much? → Increase `angle_tolerance`

---

## Common Parameter Combinations

### Conservative (Slow but Stable)

```python
# Centering
center_tolerance_x = 30
angular_speed_max = 0.2
kp_angular = 0.001

# Approaching
linear_speed = 0.05
kp_linear = 0.000003

# Navigation
nav_linear_speed = 0.1
position_tolerance = 0.2
```

### Moderate (Recommended)

```python
# Centering
center_tolerance_x = 50
angular_speed_max = 0.3
kp_angular = 0.002

# Approaching
linear_speed = 0.1
kp_linear = 0.000005

# Navigation
nav_linear_speed = 0.15
position_tolerance = 0.1
```

### Aggressive (Fast but May Oscillate)

```python
# Centering
center_tolerance_x = 70
angular_speed_max = 0.5
kp_angular = 0.003

# Approaching
linear_speed = 0.15
kp_linear = 0.000008

# Navigation
nav_linear_speed = 0.25
position_tolerance = 0.15
```

---

## Debugging: What to Adjust When

| Problem | Adjust This | Direction |
|---------|-------------|-----------|
| Robot overshoots | `target_bbox_area` | Decrease |
| Robot stops too far | `target_bbox_area` | Increase |
| Centering oscillates | `kp_angular` | Decrease |
| Centering too slow | `kp_angular` | Increase |
| Approach oscillates | `kp_linear` | Decrease |
| Approach too slow | `linear_speed` | Increase |
| Gripper misses bottle | `arm positions` | Adjust joints |
| Won't return home | `position_tolerance` | Increase |
| Spins at home | `angle_tolerance` | Increase |

---

**Parameter configuration complete!** 🎯
