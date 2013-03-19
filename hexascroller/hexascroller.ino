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

// Accessory port is on UART1
// Relay: C7 (10)

#define RELAY_PIN 10

// Commands:
// A command is a command code followed by a command-specific
// amount of raw data. The maximum command length is 122 bytes.
// If a command is not completed with 500ms, it is abandoned.
// Command codes are in the range 0xA0-0xAF.
// When a command is received, a response message is sent which
// consists of a status code, a length field N, and N bytes of data.
//
// Every command should recieve a response, consisting of an error
// code, a length field N, and N bytes of data.
//
// Reponse codes:
// 0x00 - OK
// 0x01 - Unspecified failure
//
// Command Codes:
// 0xA0 - status (not yet implemented)
// 0xA1 - display text
//        Payload:
//        X - 1 byte signed x offset
//        Y - 1 byte signed y offset
//        s... - string to display
//        Response payload: None
// 0xA2 - display bitmap
//        Payload:
//        b... - 120 bytes of 1-bit bitmap data
//        Response payload: None
// 0xA3 - set ID
//        Payload:
//        I - 1 byte unsigned ID
//        Response payload: None
// 0xA4 - query ID
//        Payload: none
//        Response payload:
//        I - 1 byte unsigned ID
// 0xA5 - write to accessory UART
//        Payload:
//        b... - up to 120 bytes of data to write to
//        the accessory UART. It is recommended that
//        the messages be short.
//        Response payload: None
// 0xA6 - Turn on/off relay
//        Payload:
//        V - 1 byte indicating on (non-zero) or off (zero)
//        Response payload: None
//

#define COMM_PORT Serial
#define ACC_PORT Serial1

// Each display module is a 120x7 grid. (Each module
// consists of two chained 60x7 modules.)
const static int columns = 120;
const static int rows = 7;

static int active_row = -1;

#include <avr/pgmspace.h>
#include "hfont.h"
#include <stdint.h>
#include <EEPROM.h>

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

void setRelay(boolean on) {
  digitalWrite(RELAY_PIN,on?HIGH:LOW);
}

void setup() {
  // Make sure relay is off initially
  PORTC &= ~_BV(7);
  DDRC |= _BV(7);
  
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

  ACC_PORT.begin(9600);
  
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
  RSP_OK = 0,
  RSP_ERROR = 1
};

void response(uint8_t code, const uint8_t* payload, uint8_t psize) {
  COMM_PORT.write(code);
  COMM_PORT.write(psize);
  for (int i = 0; i < psize; i++) {
    COMM_PORT.write(payload[i]);
  }
}

void fail(const uint8_t* payload = NULL, uint8_t psize = 0) {
  response(RSP_ERROR, payload, psize);
}

void succeed(const uint8_t* payload = NULL, uint8_t psize = 0) {
  response(RSP_OK, payload, psize);
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
            case 0xA1: // text
              b.erase();
              b.writeNStr(command+2,cmdLen-2,command[0],command[1]);
              b.flip();
              succeed();
              break;
            case 0xA2: // bitmap
              {
                uint8_t* buffer = b.getBuffer();
                b.erase();
                for (uint8_t i = 0; i < columns; i++) {
                  buffer[i] = command[i];
                }
                b.flip();
                succeed();
              }
              break;
            case 0xA3: // set ID
              EEPROM.write(0,command[0]);
              succeed();
              break;
            case 0xA4: // get ID
              {
                uint8_t v = EEPROM.read(0);
                succeed(&v,1);
              }
              break;
            case 0xA5: // write to accessort uart
              {
                for (int i = 0; i < cmdLen; i++) {
                  ACC_PORT.write(command[i]);
                }
              }
              succeed();
              break;
            case 0xA6: // turn on/off relay
              setRelay(command[0] != 0);
              succeed();
              break;
            default:
              fail((const uint8_t*)&curCmd,1);
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
