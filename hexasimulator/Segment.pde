class Segment {

  int num;
  PVector pos;
  byte[] data;
  LinkedBlockingQueue queue;

  Segment(int num, PVector pos, LinkedBlockingQueue queue) {
    this.num = num;
    this.pos = pos;
    this.queue = queue;
    this.data = new byte[121];
  }

  void draw() {

    byte newData[] = (byte[]) this.queue.poll();
    if (newData != null) this.data = newData;

    pushMatrix();
    translate(this.pos.x, this.pos.y);


    for (int col = 0; col < 120; col++) {

      byte currentByte = this.data[col + 1];

      for (int row = 0; row < 8; row++) {

        color fillColor;
        if (((currentByte >>> (7 - row)) & 1) != 0) fillColor = color(255, 0, 0);
        else fillColor = color(50, 0, 0);

        fill(fillColor);
        if (col < 60) ellipse(col * PIXEL_SPACING, row * PIXEL_SPACING, PIXEL_DIAMETER, PIXEL_DIAMETER);
        else ellipse(col * PIXEL_SPACING + SCREEN_SPACING, row * PIXEL_SPACING, PIXEL_DIAMETER, PIXEL_DIAMETER);
      }
    }
    popMatrix();
  }
}

