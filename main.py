from machine import Pin, RTC, Timer
from neopixel import NeoPixel
import network
import ntptime
import ujson
import utime
import uos
import gc


class Config:
    def __init__(self):
        self.colors = bytearray(24*24*3)
        for i in range(len(self.colors)):
            self.colors[i] = 255

        self.tz = 1
        self.ap = ("Wortuhr", "froheweihnachten")
        self.wlan_creds = {"WLAN-MAQATG-0": "utah8ohhsai5oow0ienai1eb"} # TODO remove hardcoding after listen() works

    def interpret_command(self, c_list):
        if not isinstance(c_list, list):
            return

        if c_list[0] == "tz":
            if not len(c_list) == 2:
                return
            if not isinstance(c_list[1], int):
                return

            self.tz = c_list[1]

        if c_list[0] == "ap" or c_list[0] == "wlan":
            if not len(c_list) == 3:
                return
            if not isinstance(c_list[1], str):
                return
            if not isinstance(c_list[2], str):
                return

            ssid = c_list[1]
            pw = c_list[2]

        if c_list[0] == "ap":
            self.ap = (ssid, pw)

        if c_list[0] == "wlan":
            self.wlan_creds[ssid] = pw

        if c_list[0] == "color":
            if not len(c_list) == 4:
                return
            if not isinstance(c_list[1], list):
                return
            for i in c_list[1]:
                if not isinstance(i, int):
                    return
                if i > 23:
                    return
            if not isinstance(c_list[2], list):
                return
            for i in c_list[2]:
                if not isinstance(i, int):
                    return
                if i > 23:
                    return
            if not isinstance(c_list[3], list):
                return
            if not len(c_list[3]) == 3:
                return
            for i in c_list[3]:
                if not isinstance(i, int):
                    return
                if i > 255:
                    return

            hours = c_list[1]
            leds = c_list[2]
            color = c_list[3]

            for hour in hours:
                for led in leds:
                    i = hour*72+led*3
                    for x in range(3):
                        self.colors[i+x] = color[x]

            update_lights()

        self.save()

    def load(self):
        with open("config") as f:
            config_dict = ujson.load(f)
            self.tz = config_dict["tz"]
            self.ap = config_dict["ap"]
            self.wlan_creds = config_dict["wlan_creds"]

        with open("colors", mode='rb') as f:
            f.readinto(self.colors)

    def save(self):
        config_dict = {
            "tz": self.tz,
            "ap": self.ap,
            "wlan_creds": self.wlan_creds,
        }

        with open("config", mode='w') as f:
            ujson.dump(config_dict, f)

        with open("colors", mode='wb') as f:
            f.write(self.colors)


def do_connect():
    if not wlan.isconnected():
        wlan.active(True)

        if config.wlan_creds == {}:
            print("keine WLAN-Verbindungsdaten eingegeben")
            return

        ls = sorted(wlan.scan(), key=lambda x: x[3], reverse=True)

        for i in ls:
            ssid = str(i[0], 'utf-8')
            if ssid in config.wlan_creds:
                wlan.connect(ssid, config.wlan_creds[ssid])

                while wlan.status() == 1:
                    utime.sleep_ms(100)
                if wlan.status() == 5:
                    print("Erfolgreich mit WLAN verbunden")
                    ap.active(False)
                    dc_count = 0
                    return
                elif wlan.status() == 2:
                    print("WLAN-Passwort falsch")
                    del config.wlan_creds[ssid]
                else:
                    print("Konnte Verbindung mit WLAN nicht herstellen")

        wlan.active(False)
        dc_count += 1

        if dc_count >= 2:
            ap.active(True)
            utime.sleep_ms(100)
            ap.ifconfig(('192.168.0.1', '255.255.255.0', '192.168.0.1', '192.168.0.1'))
            ap.config(essid=config.ap[0], password=config.ap[1])


def update_time(_):
    do_connect()
    t = utime.localtime(ntptime.time())
    t = t[0:3] + (0,) + (t[3]+config.tz,) + t[4:6] + (0,)
    RTC().datetime(t)
    print("Zeit synchronisiert mit ntp.org")
    print(utime.localtime())


def rand_color():
    color = []
    for _ in range(3):
        color.append(list(uos.urandom(1))[0])
    return (color[0], color[1], color[2])


def clear():
    for i in range(24):
        np[i] = (0,0,0)
    np.write()


def is_minute_later():
    _, _, _, _, minute, _, _, _ = utime.localtime()

    global last_minute
    if minute == last_minute:
        return False
    else:
        return True


def update_lights():
    # get time
    _, _, _, hour, minute, _, _, _ = utime.localtime()

    global last_minute
    last_minute = minute

    quo, rem = divmod(minute, 5)
    five_step = quo * 5 + 5 # add 5 minutes to get next five_step

    if five_step == 60:
        five_step = 0
        hour += 1

    # maps
    minute_word_map = {
        0: (),
        5: ("fuenf", "nach"),
        10: ("zehn", "nach"),
        15: ("viertel", "nach"),
        20: ("zwanzig", "nach"),
        25: ("fuenf", "vor", "halb"),
        30: ("halb",),
        35: ("fuenf", "nach", "halb"),
        40: ("zwanzig", "vor"),
        45: ("viertel", "vor"),
        50: ("zehn", "vor"),
        55: ("fuenf", "vor"),
    }

    word_light_map = {
        "fuenf": 0,
        "zehn": 1,
        "viertel": 3,
        "zwanzig": 2,
        "nach": 4,
        "vor": 5,
        "halb": 6
    }

    hour_light_map = {
        1: 12,
        2: 13,
        3: 14,
        4: 15,
        5: 19,
        6: 18,
        7: 17,
        8: 16,
        9: 20,
        10: 21,
        11: 22,
        12: 23,
        13: 12,
        14: 13,
        15: 14,
        16: 15,
        17: 19,
        18: 18,
        19: 17,
        20: 16,
        21: 20,
        22: 21,
        23: 22,
        0: 23,
    }

    # 5 minute step
    light_ids = [word_light_map[x] for x in minute_word_map[five_step]]

    # minute step
    if rem == 0:
        x = []
    elif rem == 1:
        x = [11]
    elif rem == 2:
        x = [11,10]
    elif rem == 3:
        x = [11,10,8]
    elif rem == 4:
        x = [11,10,8,7]

    light_ids.extend(x)

    # hour
    if five_step < 25:
        x = hour_light_map[hour]
    else:
        x = hour_light_map[hour+1]

    light_ids.append(x)

    for i in range(24):
        if i in light_ids:
            x = hour*72+i*3
            np[i] = (config.colors[x], config.colors[x+1], config.colors[x+2])
        else:
            np[i] = (0,0,0)

    np.write()


def update_lights_check(_):
    if is_minute_later():
        update_lights()


def test_leds():
    clear()

    for i in range(24):
        if i != 0:
            np[i-1] = (0,0,0)
        np[i] = rand_color()
        np.write()
        utime.sleep_ms(500)

    np[23] = (0,0,0)
    np.write()


def listen():
    import socket

    if wlan.active() is True:
        nic = wlan
    elif ap.active() is True:
        nic = ap
    else:
        return

    addr = socket.getaddrinfo(nic.ifconfig()[0], 2)[0][-1]
    s = socket.socket()

    s.bind(addr)
    try:
        s.listen(1)
        print('lausche auf', addr)

        while True:
            c, addr = s.accept()
            try:
                print('Client verbunden von', addr)

                acc = b''
                while True:
                    data = c.recv(100)
                    if data:
                        acc += data
                    else:
                        break

                command = ujson.loads(acc)
                config.interpret_command(command)
            finally:
                c.close()
                utime.sleep_ms(200)
    finally:
        s.close()


def test_listen():
    ap.active(True)
    wlan.active(False)
    utime.sleep_ms(100)
    ap.ifconfig(('192.168.0.1', '255.255.255.0', '192.168.0.1', '192.168.0.1'))
    ap.config(essid=config.ap[0], password=config.ap[1])
    listen()


pin = Pin(0, Pin.OUT)
np = NeoPixel(pin, 24)

config = Config()
if "config" in uos.listdir() and "colors" in uos.listdir():
    config.load()

ap = network.WLAN(network.AP_IF)
wlan = network.WLAN(network.STA_IF)
ap.active(False)
wlan.active(False)


if __name__ == '__main__':
    gc.enable()
    test_leds()

    dc_count = 0
    last_minute = None

    timer1 = Timer(-1)
    timer1.init(period=5000, callback=update_lights_check) # 5000 ms = 5 s
    timer2 = Timer(-1)
    timer2.init(period=90000, callback=update_time) # 90000 ms = 1.5 min

    update_time(1)
    listen()
