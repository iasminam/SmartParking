import RPi.GPIO as GPIO 
import time
import os
import sys
from RPLCD.i2c import CharLCD

TOTAL_LOCURI = 5
PARKING_SPOTS_FILE = "/home/pi/Desktop/SmartParking/parking_spots.txt"
UPDATE_INTERVAL = 5 

# Inițializare LCD
try:
    lcd = CharLCD('PCF8574', 0x27)
except Exception as e:
    sys.stderr.write(f"Eroare la inițializarea LCD în display_spots.py: {e}\n")
    lcd = None

def read_parking_spots():
    try:
        if os.path.exists(PARKING_SPOTS_FILE):
            with open(PARKING_SPOTS_FILE, 'r') as f:
                spots = int(f.read().strip())
                return max(0, min(TOTAL_LOCURI, spots))
        else:
            sys.stderr.write(f"Fișierul {PARKING_SPOTS_FILE} nu există, creând-o cu {TOTAL_LOCURI} locuri.\n")
            with open(PARKING_SPOTS_FILE, 'w') as f:
                f.write(str(TOTAL_LOCURI))
            return TOTAL_LOCURI
    except Exception as e:
        sys.stderr.write(f"Eroare la citirea locurilor libere din fișier: {e}\n")
        return TOTAL_LOCURI

def update_lcd_display(locuri_libere):
    """Actualizează afișajul LCD cu numărul curent de locuri libere."""
    if lcd:
        lcd.clear()
        lcd.write_string(f"Locuri libere:")
        lcd.cursor_pos = (1, 0)
        lcd.write_string(f"{locuri_libere}/{TOTAL_LOCURI}")
    sys.stdout.write(f"LCD Actualizat (background): Locuri libere: {locuri_libere}/{TOTAL_LOCURI}\n")

if __name__ == "__main__":
    sys.stdout.write("Starting display_spots.py in background.\n")

    try:
        locuri_curente = read_parking_spots() 
        update_lcd_display(locuri_curente) 
        while True:
            locuri_curente = read_parking_spots()
            update_lcd_display(locuri_curente)
            time.sleep(UPDATE_INTERVAL)
    except KeyboardInterrupt:
        sys.stdout.write("display_spots.py stopped.\n")
    except Exception as e:
        sys.stderr.write(f"Eroare în bucla principală display_spots.py: {e}\n")
    finally:
        pass 
