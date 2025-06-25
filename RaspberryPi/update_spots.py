import RPi.GPIO as GPIO 
import time
import os
import sys
from RPLCD.i2c import CharLCD

TOTAL_LOCURI = 5
PARKING_SPOTS_FILE = "/home/pi/Desktop/SmartParking/parking_spots.txt"

# Inițializare LCD
try:
    lcd = CharLCD('PCF8574', 0x27)
except Exception as e:
    sys.stderr.write(f"Eroare la inițializarea LCD în update_spots.py: {e}\n")
    lcd = None

def read_parking_spots():
    try:
        if os.path.exists(PARKING_SPOTS_FILE):
            with open(PARKING_SPOTS_FILE, 'r') as f:
                spots = int(f.read().strip())
                return max(0, min(TOTAL_LOCURI, spots)) 
        else:
            sys.stderr.write(f"Fișierul {PARKING_SPOTS_FILE} nu există, creând-o cu {TOTAL_LOCURI} locuri.\n")
            write_parking_spots(TOTAL_LOCURI)
            return TOTAL_LOCURI 
    except Exception as e:
        sys.stderr.write(f"Eroare la citirea locurilor libere din fișier: {e}\n")
        return TOTAL_LOCURI

def write_parking_spots(spots):
    try:
        with open(PARKING_SPOTS_FILE, 'w') as f:
            f.write(str(spots))
    except Exception as e:
        sys.stderr.write(f"Eroare la scrierea locurilor libere în fișier: {e}\n")

def update_lcd_display(locuri_libere):
    """Actualizează afișajul LCD cu numărul curent de locuri libere."""
    if lcd:
        lcd.clear()
        lcd.write_string(f"Locuri libere:")
        lcd.cursor_pos = (1, 0)
        lcd.write_string(f"{locuri_libere}/{TOTAL_LOCURI}")
    sys.stdout.write(f"LCD Actualizat: Locuri libere: {locuri_libere}/{TOTAL_LOCURI}\n")

if __name__ == "__main__":
    action = "initial"
    if len(sys.argv) > 1:
        action = sys.argv[1]

    locuri_curente = read_parking_spots()

    if action == "enter":
        if locuri_curente > 0:
            locuri_curente -= 1
            write_parking_spots(locuri_curente)
            sys.stdout.write("Locuri scăzute cu 1.\n")
        else:
            sys.stdout.write("Parcare plină, nu se pot scădea locuri.\n")
    elif action == "exit":
        if locuri_curente < TOTAL_LOCURI:
            locuri_curente += 1
            write_parking_spots(locuri_curente)
            sys.stdout.write("Locuri crescute cu 1.\n")
        else:
            sys.stdout.write("Parcare goală, nu se pot crește locuri.\n")
    else:
        sys.stdout.write(f"Acțiune necunoscută: {action}. Nu s-au modificat locurile.\n")
    
    update_lcd_display(locuri_curente)
    sys.exit(0)
