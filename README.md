VisionSnakeEngine is a real‑time gesture‑controlled game engine built with Python, OpenCV, and Mediapipe. The system tracks hand landmarks, detects pinch gestures, rolls a virtual dice, updates board state, and renders a dynamic Snake‑and‑Ladders grid with animations and HUD overlays.

The engine tracks 21 hand landmarks, computes pinch distance between index and thumb, and triggers a dice roll when the gesture is detected. The board is rendered using layered OpenCV rectangles, transparency overlays, and animated player movement. Snakes and ladders are implemented as a mapping table.

