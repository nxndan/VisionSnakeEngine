import cv2
import math
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import pyautogui
import pymongo
import datetime
import random   
import time    
 
pyautogui.FAILSAFE = False
 

GRID_COLS  = 5
GRID_ROWS  = 5
TOTAL_SQ   = GRID_COLS * GRID_ROWS       
 
SLIDES = {10: 3, 17: 6, 22: 14, 24: 11}
 
CELL_SIZE    = 80        
GRID_OX      = 120        
GRID_OY      = 20         
 
DICE_X       = 20        
DICE_Y       = 10
DICE_SIZE    = 58
 
OVERLAY_ALPHA = 0.50      
PINCH_COOL    = 1.2        
FLASH_DUR     = 0.35     
 

C_BG       = ( 15,  15,  15)  
C_GOAL     = ( 10, 200, 255)  
C_SL_TOP   = ( 25,  25, 210)  
C_SL_BOT   = (  5, 110, 255) 
C_GRID_LN  = (160, 160, 160)  
C_TXT      = (240, 240, 240)  
C_HEAD     = (  0, 235,  85)  
C_BODY     = (  0, 155,  40)  
C_FLASH    = (  0, 255, 210)  
C_DICE_BG  = ( 40,  40,  40)
C_DICE_DOT = (255, 255, 255)
C_HUD      = (200, 200, 200)
 
 
def sq_to_cell(sq):
    """
    Convert 1-based square number to (col, row) grid coords.
    Square 1  = bottom-left; snake-pattern upward.
    row 0 = top of grid display.
    """
    idx        = sq - 1
    r_from_bot = idx // GRID_COLS
    c_in_row   = idx % GRID_COLS
    col = c_in_row if r_from_bot % 2 == 0 else GRID_COLS - 1 - c_in_row
    row = GRID_ROWS - 1 - r_from_bot
    return col, row
 
 
def cell_rect(sq):
    """Return pixel (x1, y1, x2, y2) for square sq."""
    col, row = sq_to_cell(sq)
    x1 = GRID_OX + col * CELL_SIZE
    y1 = GRID_OY + row * CELL_SIZE
    return x1, y1, x1 + CELL_SIZE, y1 + CELL_SIZE
 
 
def draw_game_overlay(frame, player_pos, last_dice, flash, game_won):
    """
    Draw the semi-transparent grid + snake icon over `frame` in-place.
    Camera feed and hand-landmark dots remain visible underneath.
    """
    overlay = frame.copy()
 
   
    for sq in range(1, TOTAL_SQ + 1):
        x1, y1, x2, y2 = cell_rect(sq)
 
        if sq == TOTAL_SQ:
            bg = C_GOAL
        elif sq in SLIDES:
            bg = C_SL_TOP
        elif sq in SLIDES.values():
            bg = C_SL_BOT
        else:
            bg = C_BG
 
        cv2.rectangle(overlay, (x1, y1), (x2, y2), bg, -1)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), C_GRID_LN, 1)
 
       
        fs = 0.36
        label = str(sq)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, fs, 1)
        cv2.putText(overlay, label, (x1 + 4, y1 + th + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, fs, C_TXT, 1, cv2.LINE_AA)
 
        
        if sq in SLIDES:
            note = f"slide>{SLIDES[sq]}"
            cv2.putText(overlay, note, (x1 + 2, y2 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.27, (0, 225, 255), 1, cv2.LINE_AA)
 
        
        if sq == TOTAL_SQ:
            cv2.putText(overlay, "GOAL",
                        (x1 + 8, y1 + CELL_SIZE // 2 + 7),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 0), 2, cv2.LINE_AA)
 

    if 1 <= player_pos <= TOTAL_SQ:
        x1, y1, x2, y2 = cell_rect(player_pos)
        pad  = 5
        ix1, iy1 = x1 + pad, y1 + pad
        ix2, iy2 = x2 - pad, y2 - pad
        mid_y = (iy1 + iy2) // 2
 

        cv2.rectangle(overlay, (ix1, mid_y), (ix2, iy2), C_BODY, -1)
        cv2.rectangle(overlay, (ix1, iy1), (ix2, mid_y), C_HEAD, -1)
 

        eye_r  = max(2, CELL_SIZE // 14)
        eye_y  = iy1 + (mid_y - iy1) // 2
        eye_lx = ix1 + (ix2 - ix1) // 3
        eye_rx = ix1 + 2 * (ix2 - ix1) // 3
        cv2.circle(overlay, (eye_lx, eye_y), eye_r, (0, 0, 0), -1)
        cv2.circle(overlay, (eye_rx, eye_y), eye_r, (0, 0, 0), -1)
 

        tx = (ix1 + ix2) // 2
        cv2.line(overlay, (tx, iy1),     (tx, iy1 - 6),     (0, 0, 190), 2)
        cv2.line(overlay, (tx, iy1 - 6), (tx - 4, iy1 - 10), (0, 0, 190), 2)
        cv2.line(overlay, (tx, iy1 - 6), (tx + 4, iy1 - 10), (0, 0, 190), 2)
 
        # outline — flashes on roll
        cv2.rectangle(overlay, (ix1, iy1), (ix2, iy2),
                      C_FLASH if flash else C_HEAD, 2)
 

    cv2.addWeighted(overlay, OVERLAY_ALPHA, frame, 1 - OVERLAY_ALPHA, 0, frame)
 

    if game_won:
        gw  = GRID_COLS * CELL_SIZE
        bx1 = GRID_OX
        bx2 = GRID_OX + gw
        bmy = GRID_OY + (GRID_ROWS * CELL_SIZE) // 2
        cv2.rectangle(frame, (bx1, bmy - 34), (bx2, bmy + 34), (0, 130, 0), -1)
        cv2.rectangle(frame, (bx1, bmy - 34), (bx2, bmy + 34), (0, 255, 80), 2)
        cv2.putText(frame, "YOU WIN!",
                    (bx1 + 55, bmy + 7),
                    cv2.FONT_HERSHEY_DUPLEX, 1.05, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, "Pinch to restart",
                    (bx1 + 38, bmy + 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180, 255, 180), 1, cv2.LINE_AA)
 
    hud_y = GRID_OY + GRID_ROWS * CELL_SIZE + 22
    cv2.putText(frame,
                f"Square: {player_pos} / {TOTAL_SQ}    Roll: {last_dice if last_dice else '-'}",
                (GRID_OX, hud_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, C_HUD, 1, cv2.LINE_AA)
    cv2.putText(frame, "Pinch index+thumb to roll",
                (GRID_OX, hud_y + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, (120, 120, 120), 1, cv2.LINE_AA)
 
 
def draw_dice_widget(frame, value):
    """Render a pip-style dice face in the top-left corner of the frame."""
    x, y, s = DICE_X, DICE_Y, DICE_SIZE
 
    cv2.rectangle(frame, (x, y), (x + s, y + s), C_DICE_BG, -1)
    cv2.rectangle(frame, (x, y), (x + s, y + s), C_TXT,     2)
 
    cr = 4
    for cx, cy in [(x+cr, y+cr), (x+s-cr, y+cr),
                   (x+cr, y+s-cr), (x+s-cr, y+s-cr)]:
        cv2.circle(frame, (cx, cy), cr, C_DICE_BG, -1)
 
    pips = {
        1: [(0.50, 0.50)],
        2: [(0.28, 0.28), (0.72, 0.72)],
        3: [(0.28, 0.28), (0.50, 0.50), (0.72, 0.72)],
        4: [(0.28, 0.28), (0.72, 0.28), (0.28, 0.72), (0.72, 0.72)],
        5: [(0.28, 0.28), (0.72, 0.28), (0.50, 0.50), (0.28, 0.72), (0.72, 0.72)],
        6: [(0.28, 0.22), (0.72, 0.22), (0.28, 0.50), (0.72, 0.50), (0.28, 0.78), (0.72, 0.78)],
    }
    r = max(3, s // 9)
    for fx, fy in pips.get(value, []):
        cv2.circle(frame, (x + int(fx * s), y + int(fy * s)), r, C_DICE_DOT, -1)
 
    cv2.putText(frame, "DICE", (x + 11, y + s + 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, (140, 140, 140), 1, cv2.LINE_AA)
 

def main():
    base_options = python.BaseOptions(model_asset_path="hand_landmarker.task")
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=1,
        
    )
    detector = vision.HandLandmarker.create_from_options(options)
    frame1 = cv2.imread("full_screenshot.png")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return
 
    
    player_pos    = 1
    last_dice     = 0
    last_pinch_t  = 0.0
    pinch_flash_t = 0.0
    game_won      = False
    was_pinching  = False
 
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
 
        
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )
 
        
        result = detector.detect(mp_image)
 
        
        pinching = False
 
        
        if result.hand_landmarks:
            hand = result.hand_landmarks[0]
            index_finger_tip = hand[8]
            thumb_finger_tip = hand[4]
            h, w, _ = frame.shape
            
            for lm in [index_finger_tip,thumb_finger_tip]:
                x = int(lm.x * w)
                y = int(lm.y * h)
                cv2.circle(frame, (x, y), 4, (0, 255, 0), -1)
                    #cv2.circle()
        
           
            dist = math.hypot(index_finger_tip.x - thumb_finger_tip.x, index_finger_tip.y - thumb_finger_tip.y)
            if dist < 0.06:
                print("pinch")
                pinching = True  
 
        
        now = time.time()
        if pinching and not was_pinching and (now - last_pinch_t) >= PINCH_COOL:
            if game_won:
                # restart
                player_pos    = 1
                last_dice     = 0
                game_won      = False
            else:
                roll      = random.randint(1, 6)
                last_dice = roll
                new_pos   = player_pos + roll
 
                
                if new_pos >= TOTAL_SQ:
                    new_pos  = TOTAL_SQ
                    game_won = True
 
                
                if not game_won and new_pos in SLIDES:
                    new_pos = SLIDES[new_pos]
 
                player_pos = new_pos
 
            last_pinch_t  = now
            pinch_flash_t = now + FLASH_DUR   
 
        was_pinching = pinching
 
        flash = time.time() < pinch_flash_t
        draw_game_overlay(frame, player_pos, last_dice, flash, game_won)
        if last_dice:
            draw_dice_widget(frame, last_dice)
 
        cv2.imshow("Hand Landmarks", frame)
 
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
 
    cap.release()
    cv2.destroyAllWindows()
 
if __name__ == "__main__":
    main()
 