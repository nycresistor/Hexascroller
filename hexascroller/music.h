#ifndef MUSIC_H
#define MUSIC_H

// Code for playing "music", if that raucous square
// wave nonsense can be called such, on hexascroller.

/**
 * Run the tune loop. This should be called periodically;
 * the actual wave output is controlled by the OC5A pin.
 */
void tune();

void buzz(int frequency, int duration);

void playTune(char* tune);

#endif // MUSIC_H
