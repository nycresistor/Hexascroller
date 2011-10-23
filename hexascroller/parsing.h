#ifndef PARSING_H
#define PARSING_H

/** Parse an integer from the given pointer and update the
 * pointer to point to the first non-integer character.
 * parseInt does not handle negative numbers.
 */
int parseInt(char*& p);

/**
 * Parse a note entry from the given pointer and update the
 * pointer to point to the first character not recognized
 * as part of the note. The note assignments are as shown:
 *  a  a# b  c  c# d  d# e  f  f# g  g#
 *  0  1  2  3  4  5  6  7  8  9  10 11
 * Returns -1 for rests. (Rests are denoted by "r".)
 */
int parseNote(char*& p);


#endif // PARSING_H
