class Segment {
  final static byte CC_RELAY = (byte)0xA6;
  final static byte CC_BITMAP = (byte)0xA2;
  int num;
  PVector pos;
  byte[] data;
  LinkedBlockingQueue queue;

  Segment(int num, PVector pos, LinkedBlockingQueue queue) {
    this.num = num;
    this.pos = pos;
    this.queue = queue;
    this.data = new byte[122];
  }

  void draw() {

    byte newData[] = (byte[]) this.queue.poll();
    if (newData != null) this.data = newData;
    byte cmd = this.data[0];
    if (cmd != CC_BITMAP && cmd != CC_RELAY) {
      return;
    }
    pushMatrix();
    translate(this.pos.x, this.pos.y);
    
    for (int col = 0; col < 120; col++) {

      byte currentByte = 0;
      if (cmd == CC_BITMAP) {
        currentByte = this.data[col + 2];
      } else if (cmd == CC_RELAY) {
        currentByte = 0;
      }

      for (int row = 0; row < 8; row++) {

        color fillColor;
        if (((currentByte >>> (7 - row)) & 1) != 0) fillColor = color(255, 0, 0);
        else fillColor = color(50, 0, 0);

        fill(fillColor);
        if (col < 60) ellipse(col * PIXEL_SPACING, row * PIXEL_SPACING, PIXEL_DIAMETER, PIXEL_DIAMETER);
        else ellipse(col * PIXEL_SPACING + SCREEN_SPACING, row * PIXEL_SPACING, PIXEL_DIAMETER, PIXEL_DIAMETER);
      }
    }
    
    fill(150);
    rect((SEGMENT_WIDTH / 2) * PIXEL_SPACING, 0, SCREEN_SPACING, SEGMENT_HEIGHT * PIXEL_SPACING);
    if (this.num < 2) rect(SEGMENT_WIDTH * PIXEL_SPACING, 0, SCREEN_SPACING, SEGMENT_HEIGHT * PIXEL_SPACING);
    
    popMatrix();
  }
}