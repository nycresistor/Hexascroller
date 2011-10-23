#include "parsing.h"

int parseInt(char*& p) {
  int v = 0;
  while (*p >= '0' && *p <= '9') {
    v *= 10;
    v += *p - '0';
    p++;
  }
  return v;
}

// a  a# b  c  c# d  d# e  f  f# g  g#
// 0  1  2  3  4  5  6  7  8  9  10 11
// -1 for rests (r)
int parseNote(char*& p) {
  int base = 0;
  switch(*p) {
  case 'a': case 'A': base = 0; break;
  case 'b': case 'B': base = 2; break;
  case 'c': case 'C': base = 3; break;
  case 'd': case 'D': base = 5; break;
  case 'e': case 'E': base = 7; break;
  case 'f': case 'F': base = 8; break;
  case 'g': case 'G': base = 10; break;
  case 'r': case 'R': base = -1; break;
  default:
    return 0;  
  }
  p++;
  if (*p == '#') {
    p++; base++;
  }
  if (*p == 'b') {
    p++; base--;
  }
  return base;
}
