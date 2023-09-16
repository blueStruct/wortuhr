from machine import Pin, RTC
from neopixel import NeoPixel
import network
import ntptime
import utime
import uos

ap = network.WLAN(network.AP_IF)
ap.active(False)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

COLOR = (255, 255, 255)
TZ_OFFSET = 1

def do_connect():
    if not wlan.isconnected():
        wlan.active(True)

        if "wlan_credentials" not in uos.listdir():
            print("keine WLAN-Verbindungsdaten eingegeben")
            return

        with open("wlan_credentials") as f:
            ssid = f.readline().rstrip("\n")
            pw = f.readline().rstrip("\n")

        wlan.connect(ssid, pw)

        while wlan.status() == 1:
            utime.sleep_ms(100)
        if wlan.status() == 5:
            print("Erfolgreich mit WLAN verbunden")
        elif wlan.status() == 2:
            print("WLAN-Passwort falsch")
        elif wlan.status() == 3:
            print("WLAN nicht gefunden")
        else:
            print("Konnte Verbindung mit WLAN nicht herstellen")


def update_time():
    do_connect()
    t = utime.localtime(ntptime.time())
    t = t[0:3] + (0,) + (t[3]+TZ_OFFSET,) + t[4:6] + (0,)
    RTC().datetime(t)
    print("Zeit synchronisiert mit ntp.org")
    print(utime.localtime())


def update_lights():
    _, _, _, hour, minute, _, _, _ = utime.localtime()
    quo, rem = divmod(minute, 5)
    five_step = quo * 5

    minute_word_map = {
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
        "fuenf": (),
        "zehn": (),
        "viertel": (),
        "zwanzig": (),
        "nach": (),
        "vor": (),
        "halb": ()
    }

    light_ids = [i for x in minute_word_map[five_step] for i in word_light_map[x]]
    hour_id = 13+2*hour # TODO correct equation


    if five_step < 30:
        light_ids.extend((hour_id, hour_id+1)) # TODO correct offsets
    else:
        light_ids.extend((hour_id+2, hour_id+3)) # TODO correct offsets

    light_ids.append(15+rem) # minute steps

    pin = Pin(14, Pin.OUT)
    np = NeoPixel(pin, 20)

    for i in light_ids:
        np[i] = COLOR

    np.write()


# TODO get and use config data
def serve_config_page():
    ap.active(True)
    utime.sleep_ms(100)
    ap.ifconfig(('192.168.0.1', '255.255.255.0', '192.168.0.1', '192.168.0.1'))
    ap.config(essid='Wortuhr', password='froheweihnachten')

    html = """
	<!DOCTYPE html>
	<html>
	    <head>
		<meta charset="utf-8">
		<title>Wortuhr</title>
		<style>
		    html, body {
			width: 100%;
			height: 100%;
			margin: 0;
			padding: 0;
		    }
		</style>
	    </head>
	    <body>
		<h2>Konfiguration</h2>
		<table border="0">
		    <tr>
			<td><strong>WLAN-SSID</strong></td>
			<td><input type="text" id="ssid" name="ssid"></td>
		    </tr>
		    <tr>
			<td><strong>WLAN-Passwort</strong></td>
			<td><input type="password" id="password" name="password"></td>
		    </tr>
		    <tr>
			<td><strong>Textfarbe</strong></td>
			<td><input type="color" id="color" name="color"></td>
		    </tr>
		    <tr>
			<td>Rotanteil (0-255)</td>
			<td><input type="text" id="red" name="red"></td>
		    </tr>
		    <tr>
			<td>Grünanteil (0-255)</td>
			<td><input type="text" id="green" name="green"></td>
		    </tr>
		    <tr>
			<td>Blauanteil (0-255)</td>
			<td><input type="text" id="blue" name="blue"></td>
		    </tr>
		    <tr>
			<td><strong>Zeitzone (UTC + x)</strong></td>
			<td><input type="text" id="tz" name="tz"></td>
		    </tr>
		</table>
		<h2>Meldungen</h2>
	    </body>
	</html>
    """

    import socket
    addr = socket.getaddrinfo(ap.ifconfig()[0], 80)[0][-1]
    s = socket.socket()

    try:
        s.bind(addr)
        s.listen(1)
        print('lausche auf', addr)

        while True:
            cl, addr = s.accept()
            print('Client verbunden von', addr)
            cl_file = cl.makefile('rwb', 0)
            while True:
                line = cl_file.readline()
                if not line or line == b'\r\n':
                    break
            cl.send(html)

            # while True:
            #     data = s.recv(100)
            #     if data:
            #         print(str(data, 'utf8'), end='')
            #     else:
            #         break

            cl.close()
    finally:
        cl.close()


if __name__ == '__main__':
    pass # TODO setup timers
