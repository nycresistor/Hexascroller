import hypermedia.net.*;
import java.util.concurrent.*;

final static int SEGMENT_WIDTH = 120;
final static int SEGMENT_HEIGHT = 7;
final static int PIXEL_SPACING = 4;
final static int PIXEL_DIAMETER = 3;
final static int SCREEN_SPACING = 3;

UDP udp0;
UDP udp1;
UDP udp2;

LinkedBlockingQueue imageQueue0;
LinkedBlockingQueue imageQueue1;
LinkedBlockingQueue imageQueue2;

Segment segment0;
Segment segment1;
Segment segment2;

ArrayList<LinkedBlockingQueue> queues;
ArrayList<Segment> segments;

boolean stopped;
long lastRecieved;
long timeout = 5000; // Turn off draw loop when no data recieved

void settings() {
  size((SEGMENT_WIDTH * PIXEL_SPACING) * 3 + SCREEN_SPACING * 6, PIXEL_SPACING * SEGMENT_HEIGHT + (SCREEN_SPACING * 2));
}

// does processing not do closures? not even interested in finding out
void wrap0(byte[] data, String ip, int port) { receive(0, data, ip, port); }
void wrap1(byte[] data, String ip, int port) { receive(1, data, ip, port); }
void wrap2(byte[] data, String ip, int port) { receive(2, data, ip, port); }

void setup() {
  frameRate(60);

  imageQueue0 = new LinkedBlockingQueue();
  imageQueue1 = new LinkedBlockingQueue();
  imageQueue2 = new LinkedBlockingQueue();

  queues = new ArrayList<LinkedBlockingQueue>();
  queues.add(imageQueue0);
  queues.add(imageQueue1);
  queues.add(imageQueue2);

  segment0 = new Segment(0, new PVector(SCREEN_SPACING, SCREEN_SPACING), imageQueue0);
  segment1 = new Segment(1, new PVector((SCREEN_SPACING * 3) + (SEGMENT_WIDTH * PIXEL_SPACING) * 1, SCREEN_SPACING), imageQueue1);
  segment2 = new Segment(2, new PVector((SCREEN_SPACING * 5) + (SEGMENT_WIDTH * PIXEL_SPACING) * 2, SCREEN_SPACING), imageQueue2);

  segments = new ArrayList<Segment>();
  segments.add(segment0);
  segments.add(segment1);
  segments.add(segment2);

  udp0 = new UDP(this, 9990);
  udp1 = new UDP(this, 9991);
  udp2 = new UDP(this, 9992);
  // Well, this is clumsy as fuck
  udp0.setReceiveHandler("wrap0");
  udp1.setReceiveHandler("wrap1");
  udp2.setReceiveHandler("wrap2");
  udp0.listen(true);
  udp1.listen(true);
  udp2.listen(true);
}

void receive(int num, byte[] data, String ip, int port) { 
  // Restart draw loop
  lastRecieved = millis();
  loop(); 

  if (queues.get(num).size() > 0) {
    //println("Buffer full, dropping frame!");
    return;
  }

  try { 
    queues.get(num).put(data);
  } 
  catch( InterruptedException e ) {
    println("Interrupted Exception caught");
  }
}

int convertByte(byte b) {
  return (b<0) ? 256+b : b;
}

void draw() {
  background(0); 

  for (Segment segment : segments) {
    segment.draw();
  }
  
  // Turn off draw loop when no data is being recieved
  if (millis() - lastRecieved > timeout) {
    stopped = true;
    noLoop();
    println("Paused.");
  }
}