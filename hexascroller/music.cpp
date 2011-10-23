#include "music.h"
#include "parsing.h"
#include <avr/io.h>

#define OCTAVES 6
#define NOTES_PER_OCTAVE 12
// A A# B C C# D D# E F F# G G#
// octaves: 6
// notes per octave: 12
int pitches[OCTAVES * NOTES_PER_OCTAVE] = {
    // octave 0
    55, 58, 62, 65, 69, 73, 78, 82, 87, 92, 98, 104,
    110, 117, 123, 131, 139, 147, 156, 165, 175, 185, 196, 208,
    220, 233, 246, 261, 277, 293, 311, 330, 349, 370, 392, 415,
    440, 466, 493, 523, 554, 587, 622, 659, 698, 740, 784, 830,
    880, 932, 988, 1047, 1109, 1175, 1245, 1319, 1397, 1480, 1568, 1661,
    1760, 1865, 1976, 2093, 2217, 2349, 2489, 2637, 2794, 2960, 3136, 3322
};

#define MAX_TUNE_LEN 400

struct Note {
  int frequency; // -1 for silent/rest
  unsigned int length; // in 32nd notes
};
Note tuneNotes[MAX_TUNE_LEN];
int tuneLength = 0;
int tuneIdx = 0;
int noteTicks = 0;

void startBuzz(int frequency) {
  if (frequency <= 0) {
    TCCR5A = 0;
    TCCR5B = 0;
  } else {
    DDRL |= 1 << 3;
    // mode 4, CTC, clock src = 1/8
    TCCR5A = 0b01000000;
    TCCR5B = 0b00001010;
    // period = 1/freq 
    int period = 2000000 / frequency;
    OCR5A = period; // 3000; // ~500hz
  }
}

void tune() {
  if (tuneLength <= tuneIdx) {
    TCCR5A = 0;
    TCCR5B = 0;
    return;
  } else {
    if (noteTicks == 0) {
	if (tuneNotes[tuneIdx].frequency == -1) {
          // rest or end of tune
          TCCR5A = 0;
          TCCR5B = 0;
        } else {
          startBuzz(tuneNotes[tuneIdx].frequency);
        }
    }
    noteTicks++;
    if (noteTicks >= tuneNotes[tuneIdx].length) {
      noteTicks = 0;
      tuneIdx++;
    }
  }
}

void buzz(int frequency, int duration) {
  tuneNotes[0].frequency = frequency;
  tuneNotes[1].length = duration;
  tuneLength = 1;
  tuneIdx = 0;
}

void playTune(char* p) {
  int tl = 0;
  while (*p != '\0') {
    int octave = *(p++) - '0'; //parseInt(p);
    if (*p == '\0') break;
    int note = parseNote(p);
    //if (note == -1) octave = 0;
    int len = parseInt(p);
    int ni = (octave * NOTES_PER_OCTAVE) + note;
    if (ni <= 0) {
      tuneNotes[tl].frequency = -1;
    } else {
      tuneNotes[tl].frequency = pitches[ni];
    }
    tuneNotes[tl].length = len;
    tl++;
    if (*p == ',') p++;
  }
  tuneLength = tl;
  tuneIdx = 0;
}
