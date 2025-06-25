import RPi.GPIO as GPIO
import picamera2
import time
import os
from datetime import datetime
from picamera2 import Picamera2
import pytesseract
import cv2
from libcamera import controls
from RPLCD.i2c import CharLCD
import sys

IMAGE_PATH = "/home/pi/captured_images" 
TRIGGER_PIN = 17
ECHO_PIN = 23
OPTIMAL_LENS_POSITION = 10.0
DISTANTA_DETECTIE_CM = 10
DETECTION_TIMEOUT = 10
SENSOR_POLLING_INTERVAL = 0.1

# Inițializare LCD 
try:
    lcd = CharLCD('PCF8574', 0x27)
except Exception as e:
    sys.stderr.write(f"Eroare la inițializarea LCD în main_pi_script.py: {e}\n")
    lcd = None

def update_lcd_message(message1, message2=""):
    """
    Afișează mesaje temporare pe LCD.
    Mesajul1 pe rândul 0, Mesajul2 pe rândul 1.
    """
    if lcd:
        lcd.clear()
        lcd.write_string(message1.ljust(16))
        lcd.cursor_pos = (1, 0)
        lcd.write_string(message2.ljust(16))
    sys.stderr.write(f"LCD (main_pi_script): {message1} / {message2}\n") # Pentru debugging prin SSH

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIGGER_PIN, GPIO.OUT)
    GPIO.setup(ECHO_PIN, GPIO.IN)
    GPIO.output(TRIGGER_PIN, GPIO.LOW)
    sys.stderr.write("GPIO setat.\n")

def setup_camera():
    picam2 = Picamera2()
    config = picam2.create_still_configuration(
        main={"size": (2304, 1296)},
        lores={"size": (640, 480)},
        display="lores"
    )
    picam2.configure(config)
    
    if "AfMode" in picam2.camera_controls and "LensPosition" in picam2.camera_controls:
        try:
            picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": OPTIMAL_LENS_POSITION})
            sys.stderr.write(f"Focalizare manuală setată la LensPosition: {OPTIMAL_LENS_POSITION}\n")
        except Exception as e:
            sys.stderr.write(f"Eroare la setarea focalizării manuale: {e}\n")
    else:
        sys.stderr.write("Focalizarea manuală nu este suportată sau controlul LensPosition lipsește.\n")
    
    os.makedirs(IMAGE_PATH, exist_ok=True)
    sys.stderr.write(f"Camera setată. Imaginile se vor salva în {IMAGE_PATH}\n")
    return picam2

def get_distance():
    GPIO.output(TRIGGER_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIGGER_PIN, False)

    start_time = time.time()
    stop_time = time.time()

    while GPIO.input(ECHO_PIN) == 0 and time.time() - start_time < 0.1: 
        start_time = time.time()

    while GPIO.input(ECHO_PIN) == 1 and time.time() - stop_time < 0.1: 
        stop_time = time.time()

    time_elapsed = stop_time - start_time
    distance = (time_elapsed * 34300) / 2
    return distance

def capture_image(picam2):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{IMAGE_PATH}/capture_{timestamp}.jpg"
    
    picam2.start()
    time.sleep(0.5)
    picam2.capture_file(filename)
    picam2.stop()
    
    sys.stderr.write(f"Imagine capturată: {filename}\n")
    return filename

def extract_license_plate(image_path):
    try:
        img = cv2.imread(image_path)
        if img is None:
            sys.stderr.write(f"Eroare: Nu s-a putut citi imaginea de la {image_path}\n")
            return None
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY_INV, 51, 20) 

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2)) 
        thresh = cv2.erode(thresh, kernel, iterations=4)
        thresh = cv2.dilate(thresh, kernel, iterations=4)

        kernel_clean = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
        thresh = cv2.erode(thresh, kernel_clean, iterations=1)
        thresh = cv2.dilate(thresh, kernel_clean, iterations=1)
        
        config = ('-c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ --psm 7')
        text = pytesseract.image_to_string(thresh, lang='eng', config=config)
        
        cleaned_text = ''.join(filter(str.isalnum, text)).upper()
        
        cv2.imwrite(f"{IMAGE_PATH}/debug_thresh_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg", thresh)
        
        sys.stderr.write(f"Număr de înmatriculare extras (OCR): {cleaned_text}\n")
        return cleaned_text
    except Exception as e:
        sys.stderr.write(f"Eroare OCR: {e}\n") 
        return None

def main():
    setup_gpio()
    picam2_global = setup_camera()
    
    # Afiseaza mesaj temporar pe LCD
    update_lcd_message("Astept masina...", "in zona") 
    
    start_time = time.time()
    license_plate_result = "PLACA_NEDETECTATA"
    
    try:
        car_detected = False
        while time.time() - start_time < DETECTION_TIMEOUT:
            dist = get_distance()
            if dist < DISTANTA_DETECTIE_CM:
                car_detected = True
                update_lcd_message("Masina detectata!")
                update_lcd_message("Extrag placa...", "...")
                time.sleep(0.5)
                break
            time.sleep(SENSOR_POLLING_INTERVAL)

        if car_detected:
            captured_image_path = capture_image(picam2_global)
            license_plate_result = extract_license_plate(captured_image_path)
            
            if license_plate_result:
                update_lcd_message(f"Placa: {license_plate_result}", "Verificare...")
            else:
                update_lcd_message("Placa NEDEDECTATA", "Eroare OCR")

        else:
            update_lcd_message("Timeout detecție", "Nicio masina")

    except Exception as e:
        sys.stderr.write(f"Eroare majoră în scriptul RPi: {e}\n")
        update_lcd_message("Eroare RPi", "Contactati admin")
    finally:
        if picam2_global:
            picam2_global.close()
        
        print(license_plate_result) # output-ul citit de Django
        
        time.sleep(2) 
        sys.stderr.write("main_pi_script.py ended.\n")

if __name__ == "__main__":
    main()
