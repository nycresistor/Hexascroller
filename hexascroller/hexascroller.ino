// The new hexascroller code only handles a single 7x120
// panel.

// Pin assignments:

// CLOCK PIN: D0 (5/SCL)
// DATA PIN: D1 (6/SDA)

// ROW 0: B0 (0)
// ROW 1: B1 (1)
// ROW 2: B2 (2)
// ROW 3: B3 (3)
// ROW 4: B4 (13)
// ROW 5: B5 (14)
// ROW 6: B6 (15)

// Commands:
// A command is a command code followed by a command-specific
// amount of raw data. The maximum command length is 122 bytes.
// If a command is not completed with 500ms, it is abandoned.
// Command codes are in the range 0xA0-0xAF.
// When a command is received, a response message is sent which
// consists of a status code, a length field N, and N bytes of data.
// Codes:
// 0xA0 - status (not yet implemented)
// 0xA1 - display text
//        Payload:
//        X - 1 byte signed x offset
//        Y - 1 byte signed y offset
//        s... - string to display
// 0xA2 - display bitmap
//        Payload:
//        b... - 120 bytes of 1-bit bitmap data
//

#define COMM_PORT Serial

// Each display module is a 120x7 grid. (Each module
// consists of two chained 60x7 modules.)
const static int columns = 120;
const static int rows = 7;

static int active_row = -1;

#include <avr/pgmspace.h>
#include "hfont.h"
#include <stdint.h>

// Resources:
// 2.5K RAM

uint8_t b1[columns];
uint8_t b2[columns];
uint8_t rowbuf[columns/8];

/**
 * The Bitmap class describes the display as a
 * columns x rows grid of 1-bit pixels.
 * It also contains a backing buffer and methods
 * for packing a row for faster bit-banging to 
 * the display modules.
 */
class Bitmap {
  uint8_t* data;
  uint8_t* dpl;
public:
  Bitmap() {
    data = b1;
    dpl = b2;
  }
  void erase() {
    for (int i = 0; i < columns; i++) data[i] = 0;
  }
  void writeStr(char* p, int x, int y) {
    while (*p != '\0') {
      x = writeChar(*p,x,y);
      p++;
      x++;
    }
  }
  void writeNStr(char* p, int n, int x, int y) {
    while (n-- > 0) {
      x = writeChar(*p,x,y);
      p++;
      x++;
    }
  }

  int charWidth(char c) {
    if (c == ' ') return 2;
    int coff = (int)c * 8;
    uint8_t row = pgm_read_byte(charData+coff);
    int width = 0;
    if (row == 0) {
      return 0;
    }
    while (row != 1) {
      coff++;
      width++;
      row = pgm_read_byte(charData+coff);
    }
    return width;
  }

  int stringWidth(const char* s) {
    int textLen = 0;
    while (*s != '\0') {
      textLen += charWidth(*s);
      s++;
    }
    return textLen;
  }

  int writeChar(char c, int x, int y) {
    int coff = (int)c * 8;
    uint8_t row = pgm_read_byte(charData+coff);
    if (c == ' ') return x+2;
    if (row == 0) {
      return x;
    }
    uint8_t mask = 0xfe >> y;
    while (row != 1) {
      row = row >> y;
      if (x >= 0 && x < columns) {
        data[x] = row | (data[x] & mask);
      }
      coff++;
      x++;
      row = pgm_read_byte(charData+coff);
    }
    return x;
  }
  void flip() {
    cli();
    uint8_t* tmp = data;
    data = dpl;
    dpl = tmp;
    sei();
  }
  
  uint8_t* buildRowBuf(int row) {
    uint8_t* p = getDisplay();
    uint8_t mask = 1 << (7-row);
    for (int i = 0; i < columns/8; i++) {
      rowbuf[i] = 0;
      for (int j = 0; j < 8; j++) {
        if ( (p[(i*8)+j] & mask) != 0 ) {
          rowbuf[i] |= 1<<j;
        }
      } 
    }
    return rowbuf;
  }
  
  uint8_t* getDisplay() { return dpl; }
  uint8_t* getBuffer() { return data; }
};

static Bitmap b;

inline void rowOff() {
  PORTB &= 0x80;
}

inline void rowOn(int row) {
  PORTB |= 1 << row;
}

void setup() {
  b.erase();
  b.flip();
  b.erase();
  DDRD |= 0x03;
  PORTD |= 0x03;
  DDRB |= 0x7f;
  PORTB &= 0x80;
  // 2ms per row/interrupt
  // clock: 16MHz
  // target: 500Hz
  // 32000 cycles per interrupt
  // Prescaler: 1/64 OC: 500
  // CS[2:0] = 0b011
  // WGM[3:0] = 0b0100 CTC mode (top is OCR3A)
  
  TCCR3A = 0b00000000;
  TCCR3B = 0b00001011;
  TIMSK3 = _BV(OCIE3A);
  OCR3A = 200;

  COMM_PORT.begin(9600);

  //pinMode(46,OUTPUT);
  //digitalWrite(46,LOW);

  //pinMode(48,OUTPUT);
  //digitalWrite(48,HIGH);
  
  b.erase();
  b.writeStr("Panel ready",0,0);
  b.flip();

  delay(100);
}

static unsigned int curRow = 0;

// Tomorrow: define message types

// String message
// Bitmap message


#define CMD_SIZE 122
#define MESSAGE_TICKS (columns*20)
static int message_timeout = 0;

const static uint16_t DEFAULT_MSG_OFF = 0x10;


enum {
  CODE_OK = 0,
  CODE_ERROR = -1
};

int8_t response(const char* message, int8_t code) {
  const static char* errMsg = "ERROR";
  const static char* okMsg = "OK";
  const char* prefix = (code == CODE_OK)?okMsg:errMsg;
  COMM_PORT.print(prefix);
  if (message != NULL) {
    COMM_PORT.print(": ");
    COMM_PORT.print(message);
  }
  COMM_PORT.print("\n");
  return code;
}

int8_t fail(const char* message = NULL) {
  return response(message, CODE_ERROR);
}

int8_t succeed(const char* message = NULL) {
  return response(message, CODE_OK);
}


static int xoff = 0;
static int yoff = 0;

static int frames = 0;
const int scroll_delay = 200;

static int curCmd = 0;
static int cmdLen = -1;
static char command[CMD_SIZE+1];
static int cmdIdx = 0;

void loop() {
    int nextChar = COMM_PORT.read();
    if (nextChar != -1) {
      // if not in current command...
      if (curCmd == 0) {
        if ((nextChar & 0xA0) == 0xA0) {
          curCmd = nextChar;
          cmdLen = -1;
        }
        return;
      } else if (cmdLen == -1) {
        cmdLen = nextChar;
        cmdIdx = 0;
        return;
      } else {
        command[cmdIdx++] = nextChar;
        if (cmdIdx == cmdLen) {
          switch(curCmd) {
            case 0xA1:
              b.erase();
              b.writeNStr(command+2,cmdLen-2,command[0],command[1]);
              b.flip();
              break;
            case 0xA2:
              uint8_t* buffer = b.getBuffer();
              b.erase();
              for (uint8_t i = 0; i < columns; i++) {
                buffer[i] = command[i];
              }
              b.flip();
              break;
          }
          curCmd = 0;
        }
      }
    }
}

#define CLOCK_BITS 1

ISR(TIMER3_COMPA_vect)
{
  uint8_t row = curRow % 7;
  //  uint8_t mask = 1 << (7-row);
  //uint8_t* p = b.getDisplay();
  uint8_t* p = b.buildRowBuf(row);
  rowOff();
  for (int i = 0; i < columns/8; i++) {
    for (int j = 0; j < 8; j++) {
      uint8_t v = ((p[i] & (1<<j)) == 0)?0:2;
      PORTD = CLOCK_BITS | v;
      //__asm__("nop\n\t");
      PORTD =  ~CLOCK_BITS & v;
      //__asm__("nop\n\t");
      PORTD = CLOCK_BITS | v;
    }
  }
  rowOn(curRow%7);
  curRow++;
  if (curRow >= 7) {
    curRow = 0;
    frames++;
  }
}
