#!/usr/bin/python
import led_panel
from led_panel import panels
import time

class ServiceThread:
    pass

if __name__=="__main__":
    led_panel.init()

    panels[0].setRelay(True)

    for i in range(100):
        for j in range(3):
            panels[j].setMessage("Test:"+str(i),i,0)
        time.sleep(0.333)

    panels[0].setRelay(False)

    led_panel.shutdown()
