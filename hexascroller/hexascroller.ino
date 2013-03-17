// New configuration for Teensy 2.0/panel

//
// CLOCK PIN: D0 (5/SCL)
// DATA PIN: D1 (6/SDA)

// ROW 0: B0 (2)
// ROW 1: B1 (3)
// ROW 2: B2 (5)
// ROW 3: B3 (6)
// ROW 4: B4 (7)
// ROW 5: B5 (8)
// ROW 6: B6 (9)

// PIEZO: L3 (46) (T5A)

// Relay: 48

// CONFIGURATION:
// Undefine to use XBee for communications
// #define USE_XBEE
// #define XBEE_PORT Serial2
#define COMM_PORT Serial
#define USE_ECHO
#define RELAY_PIN 48

#define GREETING "!s command to set default message"

// Each display module is a 120x7 grid. (Each module
// consists of two chained 60x7 modules.)
const static int columns = 120;
const static int rows = 7;

static int active_row = -1;

#include <avr/pgmspace.h>
#include "hfont.h"
#include <EEPROM.h>
#include <stdint.h>

// The direction of message scrolling.
// UP and DOWN are currently deprecated
// but may make a comeback someday.
typedef enum {
  LEFT,
  RIGHT,
  UP,
  DOWN,
  NONE
} Direction;

Direction dir = LEFT;

// The scroll delay is in complete display refreshes per frame.
int scroll_delay = 8;

// Resources:
// 256K program space
// 8K RAM
uint8_t b1[columns];
uint8_t b2[columns];
uint8_t rowbuf[columns];

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

  int writeChar(char c, int x, int y, bool wrap = true) {
    int coff = (int)c * 8;
    uint8_t row = pgm_read_byte(charData+coff);
    if (c == ' ') return x+2;
    if (row == 0) {
      return x;
    }
    uint8_t mask = 0xfe >> y;
    while (row != 1) {
      row = row >> y;
      if (wrap) {
        x = x % (columns);
        if (x < 0) { x = x + columns; }
      }
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
    for (int i = 0; i < columns; i++) {
      rowbuf[i] = 0;
      if ( (p[i] & mask) != 0 ) {
        rowbuf[i] |= 1<<1;
      }
    }
    return rowbuf;
  }
  
  uint8_t* getDisplay() { return dpl; }
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
  
  delay(100);
}

static unsigned int curRow = 0;

#define CMD_SIZE 100
#define MESSAGE_TICKS (columns*20)
static int message_timeout = 0;
static char message[CMD_SIZE+1];
static char command[CMD_SIZE+1];
static int cmdIdx = 0;

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

int8_t processCommand() {
  if (command[0] == '!') {
    // command processing
    switch (command[1]) {
    case 's':
      // Set default string
      for (int i = 2; i < CMD_SIZE+1; i++) {
	EEPROM.write(DEFAULT_MSG_OFF-2+i,command[i]);
	if (command[i] == '\0') break;
      }
      return succeed(command+2);
    case 'S':
      // Get current scroller status
      return succeed(message);
    case 'A':
      // Send message to accessory serial port
      return fail("No more accessory port");
    case 'D':
      return fail("No more date commands");
    case 'b':
      return fail("Buzz is no longer supported");
    case 't':
      return fail("Music is no longer supported");
    case 'C':
      return succeed();
    case 'd':
      switch (command[2]) {
      case 'l': dir = LEFT; break;
      case 'r': dir = RIGHT; break;
      // Up and down have been disabled
      case 'n': dir = NONE; break;
      default:
	return fail("Unrecognized direction");
      }
      return succeed();
    default:
      return fail("RTFM, known command letters are SsADbtC and dl|dr");
    }
  } else {
    // message
    message_timeout = MESSAGE_TICKS;
    for (int i = 0; i < CMD_SIZE+1; i++) {
      message[i] = command[i];
      //if (command[i] == '\n' || command[i] == '\r') { message[i] = '\0';
      if (command[i] == '\0') break;
    }
    return succeed();
  }
}

static int xoff = 0;
static int yoff = 0;

static int frames = 0;

void loop() {
  while (frames < scroll_delay) {
    int nextChar = COMM_PORT.read();
    #ifdef USE_ECHO
    if (nextChar > -1) COMM_PORT.write(nextChar);
    #endif
    while (nextChar != -1) {
      if (nextChar == '\n' || nextChar == '\r' || nextChar == '\0') {
        command[cmdIdx] = '\0';
        processCommand();
        cmdIdx = 0;
        nextChar = -1;
      } else {
        command[cmdIdx] = nextChar;
        cmdIdx++;
        if (cmdIdx >= CMD_SIZE) cmdIdx = CMD_SIZE-1;
        nextChar = COMM_PORT.read();
        #ifdef USE_ECHO
        if (nextChar > -1) COMM_PORT.write(nextChar);
        #endif
      }
    }
  }
  frames = 0;
  // No music on teensy version
  //tune();
  b.erase();
  b.writeStr("hello hello hello 10010 hello hello",0,0);
  /*
    switch (dir) {
    case LEFT: xoff--; break;
    case RIGHT: xoff++; break;
    case UP: yoff--; break;
    case DOWN: yoff++; break;
    }

    if (xoff < 0) { xoff += columns; }
    if (xoff >= columns) { xoff -= columns; }
    if (yoff < 0) { yoff += 7; }
    if (yoff >= 7) { yoff -= 7; }
    */
  b.flip();
}

#define CLOCK_BITS 1

ISR(TIMER3_COMPA_vect)
{
  uint8_t row = curRow % 7;
  //  uint8_t mask = 1 << (7-row);
  //uint8_t* p = b.getDisplay();
  uint8_t* p = b.buildRowBuf(row);
  rowOff();
  for (int i = 0; i < columns; i++) {
    __asm__("nop\n\t");
    PORTD = p[i] | CLOCK_BITS;
    //PORTD = 0x01;
    __asm__("nop\n\t");
    //PORTD = 0x0;
    PORTD = p[i] & ~CLOCK_BITS;
    __asm__("nop\n\t");
    //PORTD = 0x01;
    PORTD = p[i] | CLOCK_BITS;
  }
  rowOn(curRow%7);
  curRow++;
  if (curRow >= 7) {
    curRow = 0;
    frames++;
  }
}
