from machine import Pin
import time

def toggle(p):
    p.value(not p.value())

red = Pin(0, Pin.OUT)
blue = Pin(2, Pin.OUT)
toggle(blue)

while True:
    for i in range(1, 25):
        toggle(blue)
        toggle(red)
        time.sleep(1/i)
