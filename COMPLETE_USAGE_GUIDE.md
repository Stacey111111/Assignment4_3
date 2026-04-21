# Assignment 4 - Complete Implementation Guide

## 📚 Table of Contents

1. [Project Overview](#project-overview)
2. [File Structure](#file-structure)
3. [Setup Instructions](#setup-instructions)
4. [Part C-a: Visual Servoing](#part-c-a-visual-servoing)
5. [Part C-b: Pick Bottle](#part-c-b-pick-bottle)
6. [Part C-c: Pick and Place](#part-c-c-pick-and-place)
7. [Parameter Calibration](#parameter-calibration)
8. [Troubleshooting](#troubleshooting)

---

## Project Overview

This assignment implements a complete vision-based pick-and-place pipeline for TurtleBot3 with Open Manipulator X:

```
1. Visual Servoing → Align robot to bottle
2. Pick Bottle → Approach, grasp, and lift
3. Pick and Place → Return home and place bottle
```

### System Architecture

```
┌─────────────────────────────────────────────┐
│           YOLO Publisher (Jetson)           │
│  - Runs on TurtleBot (Jetson Xavier NX)    │
│  - Detects objects with YOLOv11             │
│  - Publishes to /yolo/detections_json      │
└─────────────────┬───────────────────────────┘
                  │
                  ↓ (JSON detections)
┌─────────────────────────────────────────────┐
│        Task Nodes (Jetson or Remote-PC)     │
│  - task_1a_visual_servoing.py              │
│  - task_1b_pick_bottle.py                  │
│  - task_2_pick_and_place.py                │
└─────────────────┬───────────────────────────┘
                  │
                  ↓ (Control commands)
┌─────────────────────────────────────────────┐
│              TurtleBot3 Hardware            │
│  - Wheels (/cmd_vel)                       │
│  - Arm (/arm_controller/joint_trajectory)  │
│  - Gripper (/tool_control)                 │
│  - Odometry (/odom)                        │
└─────────────────────────────────────────────┘
```

---

## File Structure

```
Assignment_4/
├── yolo_publisher_COMPLETED.py       # YOLO detection publisher
├── yolo_subscriber_COMPLETED.py      # YOLO detection subscriber (for testing)
├── task_1a_visual_servoing.py        # Part C-a: Visual servoing
├── task_1b_pick_bottle.py            # Part C-b: Pick bottle
├── task_2_pick_and_place.py          # Part C-c: Pick and place
└── README.md                          # This file
```

---

## Setup Instructions

### 1. Prerequisites

**Hardware:**
- TurtleBot3 Waffle Pi with Jetson Xavier NX
- Raspberry Pi Camera V2
- Open Manipulator X arm
- Bottle (water bottle or similar cylindrical object)

**Software:**
- Ubuntu 22.04 with ROS2 Humble
- Python 3.10+
- YOLO11 model (`yolo11n.pt`)
- OpenCV, Ultralytics

### 2. Installation

```bash
# On Jetson (TurtleBot3):
cd ~/turtlebot3_ws/src
mkdir assignment_4
cd assignment_4

# Copy all Python files to this directory
# Make sure yolo11n.pt is in the same directory

# Make files executable
chmod +x *.py
```

### 3. Model Setup (First Time Only)

```bash
# On Jetson, run once to download and cache the model
python3 yolo_publisher_COMPLETED.py

# Wait for "Loading YOLOv11 model on CUDA..." to complete
# Press Ctrl+C after model is loaded
```

---

## Part C-a: Visual Servoing

### Purpose
Align the robot to face a bottle and keep it centered in the camera view.

### How It Works

```
1. YOLO detects bottle
   ↓
2. Calculate horizontal error
   error = bottle_x - image_center_x
   ↓
3. Proportional controller
   angular_vel = -Kp * error
   ↓
4. Publish /cmd_vel
   ↓
5. Robot turns left/right to center bottle
```

### Running the Task

**Terminal 1 (Jetson - YOLO Publisher):**
```bash
cd ~/turtlebot3_ws/src/assignment_4
python3 yolo_publisher_COMPLETED.py
```

**Terminal 2 (Jetson or Remote-PC - Visual Servoing):**
```bash
cd ~/turtlebot3_ws/src/assignment_4
python3 task_1a_visual_servoing.py
```

### Expected Behavior

1. Robot will search (slowly rotate) until bottle is detected
2. Once detected, robot turns to center the bottle
3. When centered (within ±50 pixels), robot stops
4. Log shows: `✓ CENTERED | Bottle at x=640, error=0px | LOCKED ON TARGET`

### Testing

1. Place bottle in front of robot, but off-center (left or right)
2. Robot should turn to face the bottle
3. Slowly move bottle left and right
4. Robot should follow, keeping bottle centered

### Key Parameters

```python
# In task_1a_visual_servoing.py:

self.center_tolerance = 50      # Pixels - centering threshold
self.angular_speed_max = 0.5    # rad/s - max rotation speed
self.kp = 0.002                 # Proportional gain
```

---

## Part C-b: Pick Bottle

### Purpose
Complete bottle picking: align → approach → grasp → lift.

### State Machine

```
SEARCHING → CENTERING → APPROACHING → POSITIONING_ARM → 
GRASPING → LIFTING → DONE
```

### State Descriptions

| State | Action | Transition Condition |
|-------|--------|---------------------|
| SEARCHING | Rotate slowly | Bottle detected |
| CENTERING | Align to bottle | Centered (±50px) |
| APPROACHING | Drive forward | BBox area ≥ 80,000 |
| POSITIONING_ARM | Move arm to pre-grasp | 3 seconds elapsed |
| GRASPING | Close gripper | 2 seconds elapsed |
| LIFTING | Raise arm | 3 seconds elapsed |
| DONE | Stop | - |

### Running the Task

**Terminal 1 (Jetson - YOLO Publisher):**
```bash
python3 yolo_publisher_COMPLETED.py
```

**Terminal 2 (Jetson or Remote-PC - Pick Bottle):**
```bash
python3 task_1b_pick_bottle.py
```

### Expected Behavior

1. **SEARCHING**: Robot rotates, looking for bottle
2. **CENTERING**: Robot aligns to face bottle
3. **APPROACHING**: Robot drives forward until close
4. **POSITIONING_ARM**: Arm moves to pre-grasp position
5. **GRASPING**: Gripper closes around bottle
6. **LIFTING**: Arm lifts bottle off ground
7. **DONE**: Task complete

### Testing

1. Place bottle on ground, slightly off-center
2. Start the node
3. Robot will automatically:
   - Find the bottle
   - Center on it
   - Drive close
   - Grasp it
   - Lift it

### Critical Parameter: BBOX_AREA_CLOSE

```python
self.target_bbox_area = 80000  # ⚠️ MUST CALIBRATE!
```

**How to Calibrate:**

1. Run `yolo_subscriber_COMPLETED.py` to see detection data:
   ```bash
   python3 yolo_subscriber_COMPLETED.py
   ```

2. Place robot at desired grasping distance from bottle

3. Note the bounding box size:
   ```
   [0] bottle (0.85) | Center: (640.0, 400.0), Size: 250.0x320.0
                                                      ↓      ↓
                                                      w      h
   Area = w × h = 250 × 320 = 80,000
   ```

4. Update `self.target_bbox_area` in code

---

## Part C-c: Pick and Place

### Purpose
Complete pipeline: pick bottle → return to home base → place bottle.

### Extended State Machine

```
SEARCHING → CENTERING → APPROACHING → POSITIONING_ARM → 
GRASPING → LIFTING → RETURNING_HOME → LOWERING_ARM → 
RELEASING → RETURN_COMPLETE
```

### New States

| State | Action | Purpose |
|-------|--------|---------|
| RETURNING_HOME | Navigate to start | Return to base |
| LOWERING_ARM | Lower arm | Prepare to place |
| RELEASING | Open gripper | Release bottle |
| RETURN_COMPLETE | Stop | Task done |

### Running the Task

**Terminal 1 (Jetson - YOLO Publisher):**
```bash
python3 yolo_publisher_COMPLETED.py
```

**Terminal 2 (Jetson or Remote-PC - Pick and Place):**
```bash
python3 task_2_pick_and_place.py
```

### Expected Behavior

**Startup:**
```
⚠️  Move robot to HOME BASE and press Enter...
[You manually position robot at desired home location]
[Press Enter]
✓ Recording home position...
✓ Home position recorded: (0.000, 0.000), yaw=0.000
```

**Execution:**
1. States 1-6: Same as Task 1b (pick bottle)
2. **RETURNING_HOME**: Robot navigates back to starting position
3. **LOWERING_ARM**: Arm lowers to ground
4. **RELEASING**: Gripper opens, releases bottle
5. **RETURN_COMPLETE**: Task complete

### Testing

1. Start node at home base location
2. Press Enter to record home position
3. Place bottle somewhere in robot's vicinity
4. Robot will:
   - Pick up bottle
   - Return to home base
   - Place bottle down
   - Report completion

### Navigation Method

Uses **odometry-based navigation**:
```python
# Home position stored at startup
self.home_position = (x, y)

# Navigate using proportional control
dx = home_x - current_x
dy = home_y - current_y
distance = sqrt(dx² + dy²)
desired_heading = atan2(dy, dx)
```

---

## Parameter Calibration

### Critical Parameters to Adjust

#### 1. Target BBox Area (Most Important!)

```python
self.target_bbox_area = 80000  # Pixels²
```

**Calibration Procedure:**

```bash
# Run subscriber to see live detections
python3 yolo_subscriber_COMPLETED.py

# In another terminal, manually drive robot
ros2 run turtlebot3_teleop teleop_keyboard

# Drive to desired grasping distance
# Note the bbox size from subscriber output
# Area = width × height
# Update target_bbox_area in code
```

**Example Calibration:**
```
Too far (area=30,000):  Bottle too small
Perfect (area=80,000):  ✓ Good grasping distance
Too close (area=150,000): Risk of collision
```

#### 2. Centering Tolerance

```python
self.center_tolerance_x = 50  # Pixels
```

- **Smaller (20-30)**: More precise centering, slower
- **Larger (70-100)**: Faster, less precise

#### 3. Control Gains

```python
# Rotation
self.kp_angular = 0.002  # Proportional gain
self.angular_speed_max = 0.3  # rad/s

# Approach
self.kp_linear = 0.000005  # Proportional gain
self.linear_speed = 0.1  # m/s
```

**Tuning Tips:**
- If robot oscillates: Reduce `kp_angular`
- If robot too slow: Increase gains
- If robot too fast/unstable: Reduce max speeds

#### 4. Arm Positions

```python
# Pre-grasp position (adjust for your robot)
point.positions = [0.0, -0.5, 0.8, 0.3]
#                  │     │     │    │
#                  │     │     │    └─ joint4 (wrist)
#                  │     │     └─ joint3 (elbow)
#                  │     └─ joint2 (shoulder)
#                  └─ joint1 (base rotation)
```

**Finding Good Positions:**
1. Use `rqt_joint_trajectory_controller` to manually move arm
2. Find good pre-grasp position
3. Note joint angles
4. Update in code

---

## Troubleshooting

### Issue: Robot doesn't detect bottle

**Symptoms:**
```
Searching for bottle...
Searching for bottle...
(Never finds it)
```

**Solutions:**
1. Check YOLO publisher is running
2. Check bottle confidence > 0.5
3. Verify lighting conditions
4. Try different bottle (more distinctive)

**Debug:**
```bash
# Check YOLO detections
python3 yolo_subscriber_COMPLETED.py

# You should see:
[0] bottle (0.85) | Center: (...), Size: ...
```

---

### Issue: Robot overshoots/undershoots approach

**Symptoms:**
- Robot stops too far: Can't grasp bottle
- Robot stops too close: Crashes into bottle

**Solution:**
Calibrate `target_bbox_area`:

```python
# If stopping too far:
self.target_bbox_area = 80000  # Increase this
                       ↓
                     100000

# If stopping too close:
self.target_bbox_area = 80000  # Decrease this
                       ↓
                      60000
```

---

### Issue: Arm can't reach bottle

**Symptoms:**
- Gripper misses bottle
- Gripper too high/low

**Solutions:**

1. **Adjust approach distance** (change `target_bbox_area`)

2. **Adjust arm position:**
```python
# Make arm reach lower:
point.positions = [0.0, -0.5, 0.8, 0.3]
                        ↓
                       -0.7  # More down

# Make arm reach higher:
point.positions = [0.0, -0.5, 0.8, 0.3]
                        ↓
                       -0.3  # More up
```

---

### Issue: Gripper doesn't close properly

**Symptoms:**
- Gripper opens instead of closing
- Gripper doesn't move

**Solutions:**

1. **Check gripper action server:**
```bash
ros2 action list
# Should see: /tool_control
```

2. **Test gripper manually:**
```bash
# Close
ros2 action send_goal /tool_control open_manipulator_msgs/action/ToolControl "{planning_group: gripper, value: -0.01}"

# Open
ros2 action send_goal /tool_control open_manipulator_msgs/action/ToolControl "{planning_group: gripper, value: 0.01}"
```

3. **Adjust gripper values:**
```python
# Close gripper
goal.value = -0.01  # Try: -0.015, -0.02

# Open gripper
goal.value = 0.01   # Try: 0.015, 0.02
```

---

### Issue: Robot doesn't return to home (Task 2)

**Symptoms:**
- Robot wanders randomly
- Robot doesn't move during RETURNING_HOME

**Solutions:**

1. **Check odometry:**
```bash
ros2 topic echo /odom
# Should see position updates
```

2. **Check home position was recorded:**
```
✓ Home position recorded: (0.000, 0.000), yaw=0.000
```

3. **Increase position tolerance:**
```python
self.position_tolerance = 0.1  # Try 0.2 or 0.3
```

---

### Issue: Robot oscillates (wobbles)

**Symptoms:**
- Robot shakes left/right while centering
- Robot speeds up/slows down repeatedly

**Solutions:**

**Reduce proportional gains:**
```python
# For rotation oscillation
self.kp_angular = 0.002  # Try 0.001
                 ↓
                0.001

# For approach oscillation
self.kp_linear = 0.000005  # Try 0.000003
                 ↓
                0.000003
```

**Add speed limits:**
```python
self.angular_speed_max = 0.3  # Reduce to 0.2
self.linear_speed = 0.1  # Reduce to 0.05
```

---

## Video Demo Checklist

### Part C-a: Visual Servoing (20 points)

**What to show:**
1. ✓ Robot starts, bottle in view but off-center
2. ✓ Robot turns to center bottle
3. ✓ Log shows "CENTERED" message
4. ✓ Move bottle slowly left/right
5. ✓ Robot follows, maintaining center lock

**Narration points:**
- "The robot uses proportional control"
- "Error is calculated as pixel distance from center"
- "Angular velocity is proportional to error"

---

### Part C-b: Pick Bottle (30 points)

**What to show:**
1. ✓ Place bottle on ground, slightly off-center
2. ✓ Start node, show state transitions in log
3. ✓ Robot searches (rotates)
4. ✓ Robot centers on bottle
5. ✓ Robot approaches bottle
6. ✓ Arm moves to pre-grasp position
7. ✓ Gripper closes
8. ✓ Arm lifts bottle off ground

**Narration points:**
- "State machine has 7 states"
- "Robot uses bounding box area to judge distance"
- "Area threshold was calibrated to [your value]"
- "Gripper uses action client for control"

---

### Part C-c: Pick and Place (20 points)

**What to show:**
1. ✓ Position robot at home base
2. ✓ Press Enter to record home
3. ✓ Place bottle nearby
4. ✓ Robot picks up bottle (states 1-6)
5. ✓ Robot returns to home base
6. ✓ Robot places bottle down
7. ✓ Log shows "PICK AND PLACE COMPLETE"

**Narration points:**
- "Home position is recorded using odometry"
- "Robot uses atan2 to calculate heading to home"
- "Position tolerance is [your value] meters"
- "Gripper opens with positive value"

---

## Summary

### Files Completed

| File | Purpose | Required for |
|------|---------|--------------|
| yolo_publisher_COMPLETED.py | YOLO detection | All tasks |
| yolo_subscriber_COMPLETED.py | Testing | - |
| task_1a_visual_servoing.py | Visual servoing | Part C-a |
| task_1b_pick_bottle.py | Pick bottle | Part C-b |
| task_2_pick_and_place.py | Pick and place | Part C-c |

### Key Concepts

1. **Visual Servoing**: PD control using image coordinates
2. **State Machine**: Sequential task execution
3. **Odometry**: Position tracking for navigation
4. **Action Client**: Asynchronous gripper control
5. **Joint Trajectory**: Arm position control

### Tips for Success

1. ✅ **Calibrate `target_bbox_area`** - Most important!
2. ✅ **Test incrementally** - Run each task separately first
3. ✅ **Check logs** - State transitions show progress
4. ✅ **Adjust speeds** - Start slow, increase if stable
5. ✅ **Good lighting** - YOLO works better with good lighting

---

**Good luck with your demonstration!** 🤖🍾
