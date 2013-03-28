import led_panels
from led_panels import panels
import time

class ServiceThread:
    pass

if __name__=="__main__":
    led_panels.init()

    panels[0].setRelay(true)

    for i in range(100):
        for j in range(3):
            panels[j].setMessage("Test:"+str(i),i,0)
        time.delay(0.333)

    panels[0].setRelay(false)

    led_panels.shutdown()
