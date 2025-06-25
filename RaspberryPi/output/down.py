import RPi.GPIO as GPIO
import time
import sys

BARRIER_PWM_PIN = 12
CLOSE_ANGLE = 180
PWM_FREQUENCY = 50 # Setează la 50Hz pentru consistență cu up.py

def SetAngle(angle):
    pwm = None 
    try:
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(BARRIER_PWM_PIN, GPIO.OUT)
        
        pwm = GPIO.PWM(BARRIER_PWM_PIN, PWM_FREQUENCY)
        pwm.start(0)

        duty = angle / 18 + 2

        GPIO.output(BARRIER_PWM_PIN, True)
        pwm.ChangeDutyCycle(duty)
        time.sleep(1)
        
        sys.stdout.write(f"Bariera închisă la unghiul {angle} (duty: {duty}).\n")

    except Exception as e:
        sys.stderr.write(f"Eroare la închiderea barierei (SetAngle): {e}\n")
    finally:
        if pwm:
            pwm.ChangeDutyCycle(0)
            pwm.stop()
    

if __name__ == "__main__":
    SetAngle(CLOSE_ANGLE)
    sys.exit(0)
