def beep(buzzer, freq, t):
    for _ in range(int(freq*t)):
        toggle(buzzer)
        utime.sleep_us(int(1e6/freq))
    buzzer.off()
