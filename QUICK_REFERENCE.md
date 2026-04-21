# Assignment 4 - Quick Reference Guide

## 🚀 Quick Start

### Running the Tasks

```bash
# Terminal 1: YOLO Publisher (always needed)
python3 yolo_publisher_COMPLETED.py

# Terminal 2: Choose your task

# Task 1a - Visual Servoing
python3 task_1a_visual_servoing.py

# Task 1b - Pick Bottle
python3 task_1b_pick_bottle.py

# Task 2 - Pick and Place
python3 task_2_pick_and_place.py
```

---

## 📊 State Machine Overview

### Task 1a: Visual Servoing
```
SEARCHING → CENTERING → (repeat)
```

### Task 1b: Pick Bottle
```
SEARCHING → CENTERING → APPROACHING → 
POSITIONING_ARM → GRASPING → LIFTING → DONE
```

### Task 2: Pick and Place
```
SEARCHING → CENTERING → APPROACHING → POSITIONING_ARM → 
GRASPING → LIFTING → RETURNING_HOME → LOWERING_ARM → 
RELEASING → RETURN_COMPLETE
```

---

## 🎯 Critical Parameters

### Must Calibrate!

```python
# task_1b_pick_bottle.py and task_2_pick_and_place.py
self.target_bbox_area = 80000  # ⚠️ CALIBRATE THIS!
```

**How to calibrate:**
1. Run `python3 yolo_subscriber_COMPLETED.py`
2. Manually drive robot to desired grasping distance
3. Note: `Size: 250.0x320.0` → Area = 250 × 320 = 80,000
4. Update `target_bbox_area` in code

### Optional Tuning

```python
# Centering
self.center_tolerance_x = 50      # Pixels (±)
self.kp_angular = 0.002           # Rotation gain

# Approaching  
self.linear_speed = 0.1           # m/s
self.kp_linear = 0.000005         # Approach gain

# Arm positions
point.positions = [0.0, -0.5, 0.8, 0.3]  # [j1, j2, j3, j4]

# Gripper
goal.value = -0.01  # Close (negative)
goal.value = 0.01   # Open (positive)
```

---

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Bottle not detected | Check YOLO publisher running, check lighting |
| Stops too far | Increase `target_bbox_area` |
| Stops too close | Decrease `target_bbox_area` |
| Arm can't reach | Adjust arm joint angles |
| Gripper doesn't close | Change `goal.value` to -0.015 or -0.02 |
| Robot oscillates | Reduce `kp_angular` or `kp_linear` |
| Won't return home | Check `/odom` topic, increase `position_tolerance` |

---

## 📹 Video Demo Checklist

### Part C-a (20 points)
- [ ] Robot centers on bottle
- [ ] Shows "CENTERED" in log
- [ ] Follows bottle when moved
- [ ] Explain proportional control

### Part C-b (30 points)
- [ ] All 7 states shown
- [ ] Bottle lifted off ground
- [ ] State transitions visible in log
- [ ] Explain bbox area threshold

### Part C-c (20 points)
- [ ] Record home position
- [ ] Pick bottle
- [ ] Return to home
- [ ] Place bottle
- [ ] Explain odometry navigation

---

## 🔧 Common Commands

```bash
# Check YOLO detections
python3 yolo_subscriber_COMPLETED.py

# Test odometry
ros2 topic echo /odom

# Check available topics
ros2 topic list

# Manually control robot
ros2 run turtlebot3_teleop teleop_keyboard

# Test gripper
ros2 action send_goal /tool_control open_manipulator_msgs/action/ToolControl "{planning_group: gripper, value: -0.01}"
```

---

## 📂 File Summary

| File | Lines | Purpose |
|------|-------|---------|
| yolo_publisher_COMPLETED.py | ~100 | YOLO detection |
| yolo_subscriber_COMPLETED.py | ~60 | Test subscriber |
| task_1a_visual_servoing.py | ~150 | Visual servoing |
| task_1b_pick_bottle.py | ~400 | Pick bottle |
| task_2_pick_and_place.py | ~550 | Pick and place |

---

## 💡 Tips

1. **Always run YOLO publisher first**
2. **Calibrate bbox_area for your setup**
3. **Start with slow speeds, increase if stable**
4. **Good lighting helps YOLO accuracy**
5. **Check logs for state transitions**
6. **Test each task separately before demo**

---

## ⚙️ Default Values Reference

```python
# Image
image_width = 1280
image_center_x = 640

# Centering
center_tolerance_x = 50 px
angular_speed_max = 0.3 rad/s
kp_angular = 0.002

# Approaching
target_bbox_area = 80000 px²
bbox_area_tolerance = 5000 px²
linear_speed = 0.1 m/s
kp_linear = 0.000005

# Navigation (Task 2)
position_tolerance = 0.1 m
angle_tolerance = 0.2 rad
nav_linear_speed = 0.15 m/s
nav_angular_speed = 0.3 rad/s

# Timing
state delays:
  - ARM_POSITIONING: 3s
  - GRASPING: 2s
  - LIFTING: 3s
```

---

**Quick Reference Complete!** 🎯
