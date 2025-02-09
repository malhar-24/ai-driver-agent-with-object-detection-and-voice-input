import serial
import sys
import requests
import numpy as np
from ultralytics import YOLO
import cv2
import time
# Load YOLOv8 model
model = YOLO("yolov8n.pt")
# IP camera snapshot URL
url = "http://192.168.1.101:8080/shot.jpg"
# Accept target_x and target_y from command-line arguments
if len(sys.argv) < 3:
    print("Usage: python nwithobject.py <target_x> <target_y>")
    sys.exit(1)

target_x = int(sys.argv[1])
target_y = int(sys.argv[2])


def detect_object_position():
    response = requests.get(url)

    if response.status_code == 200:
        img_array = np.asarray(bytearray(response.content), dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)  # Decode image

        if frame is None:
            print("Failed to decode image")
            return

        results = model(frame)  # Run YOLOv8 inference

        if len(results[0].boxes) > 0:
            frame_width = frame.shape[1]  # Get frame width
            frame_height = frame.shape[0]  # Get frame height

            section_width = frame_width / 4  # Divide width into 4 parts
            section_height = frame_height / 2  # Divide height into 2 parts

            for box in results[0].boxes.xyxy:  # Get bounding box coordinates
                x_min, y_min, x_max, y_max = box[:4]  # Extract x and y values
                
                # Find center of the detected object
                center_x = (x_min + x_max) / 2  
                center_y = (y_min + y_max) / 2  

                # Determine horizontal position (Left-most, Left, Right, Right-most)
                if center_x < section_width:
                    horizontal_position = "left"
                elif center_x < 2 * section_width:
                    horizontal_position = "left"
                elif center_x < 3 * section_width:
                    horizontal_position = "right"
                else:
                    horizontal_position = "right"

                # Determine vertical position (Upper, Lower)
                vertical_position = "upper" if center_y < section_height else "lower"

                # Combine both positions
                position = f"{vertical_position} {horizontal_position}"

                return position

        else:
            return 'None'

    else:
        print("Failed to retrieve image. Status code:", response.status_code)



def generate_gcode(current_x, current_y, target_x, target_y, maxstep, object_status,feed):
    # If object status is not 'none', handle object detection
    if object_status != 'None':
        if object_status == 'upper left':  # Move diagonally up-right
            gcode = f"G1 X{current_x} Y{current_y + maxstep} F{feed}\nG1 X{current_x + maxstep} Y{current_y + maxstep * 2} F{feed}"
            return gcode, current_x + maxstep, current_y + maxstep * 2

        elif object_status == 'lower right':  # Move diagonally down-right
            gcode = f"G1 X{current_x - maxstep} Y{current_y - maxstep} F{feed}\nG1 X{current_x} Y{current_y - maxstep} F{feed}\nG1 X{current_x + maxstep} Y{current_y} F{feed}"
            return gcode, current_x + maxstep, current_y

        elif object_status == 'upper right':  # Move up (y increment) and keep x same
            gcode = f"G1 X{current_x + maxstep} Y{current_y} F{feed}\nG1 X{current_x + maxstep*2} Y{current_y + maxstep} F{feed}"
            return gcode, current_x + maxstep*2, current_y + maxstep

        elif object_status == 'lower left':  # Move down (y decrement) and keep x same
            gcode = f"G1 X{current_x - maxstep} Y{current_y - maxstep} F{feed}\nG1 X{current_x- maxstep} Y{current_y} F{feed}\nG1 X{current_x } Y{current_y + maxstep} F{feed}"
            return gcode, current_x, current_y + maxstep

     # If object status is 'none', increment the current position towards the target
    else:
        # Calculate the delta between current and target coordinates
        delta_x = target_x - current_x
        delta_y = target_y - current_y
        rx=1
        ry=1
        if abs(delta_x)>abs(delta_y):
            ry=abs(delta_y/delta_x)
        if abs(delta_x)<abs(delta_y):
            rx=abs(delta_x/delta_y)

        if rx == 0:
            rx=1
        if ry == 0:
            ry=1
        
        # Create conditions to increment coordinates step by step towards the target
        if abs(delta_x) <= maxstep and abs(delta_y) <= maxstep:
            # If both x and y are within one step, move directly to the target
            new_x = target_x
            new_y = target_y
        else:
            # Separate x and y movements to avoid overshooting
            # Move x towards the target
            if abs(delta_x) > maxstep:
                new_x = current_x + (maxstep if delta_x > 0 else -maxstep)*rx
            else:
                new_x = target_x*rx

            # Move y towards the target
            if abs(delta_y) > maxstep:
                new_y = current_y + (maxstep if delta_y > 0 else -maxstep)*ry
            else:
                new_y = target_y*ry

            # Ensure we don't overshoot the target for X and Y separately
            if (delta_x > 0 and new_x > target_x) or (delta_x < 0 and new_x < target_x):
                new_x = target_x
            if (delta_y > 0 and new_y > target_y) or (delta_y < 0 and new_y < target_y):
                new_y = target_y

        # Generate the G-code command for movement
        gcode = f"G1 X{new_x} Y{new_y} F{feed}"
        return gcode, new_x, new_y



def main():
    ser = serial.Serial(port='COM5', baudrate=115200, timeout=1)
    
    current_x=0
    current_y=0
    max_step=3
    feed=100

    
    try:
        while True:
            response = ser.readline().decode().strip()
            if response:
                print("Received:", response)

            while current_x != target_x or current_y != target_y:
                for i in range(0, 5):
                    object_status = detect_object_position()
                    if object_status!= 'None':
                        break
                
                gcode, current_x, current_y = generate_gcode(current_x, current_y, target_x, target_y, max_step, object_status,feed)
                print(gcode, ',', current_x, ',', current_y)
                for line in gcode.split("\n"):

                    ser.write(line.strip().encode() + b'\n')  # Send G-code over serial
                    print(line.strip().encode() + b'\n')
                
                
                time.sleep(10)  # Add delay

            exit(0)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        ser.close()

if __name__ == "__main__":
    main()



    





