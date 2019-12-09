/* -*- mode: c++ -*-
 * Kaleidoscope-EEPROM-Settings -- Basic EEPROM settings plugin for Kaleidoscope.
 * Copyright (C) 2017  Keyboard.io, Inc
 *
 * This program is free software: you can redistribute it and/or modify it under
 * the terms of the GNU General Public License as published by the Free Software
 * Foundation, version 3.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
 * details.
 *
 * You should have received a copy of the GNU General Public License along with
 * this program. If not, see <http://www.gnu.org/licenses/>.
 *
 * Originally generated by pycrc v0.9, https://pycrc.org
 *
 * using the configuration:
 *    Width         = 16
 *    Poly          = 0x8005
 *    Xor_In        = 0x0000
 *    ReflectIn     = True
 *    Xor_Out       = 0x0000
 *    ReflectOut    = True
 *    Algorithm     = bit-by-bit-fast
 */

#pragma once

class CRC_ {
 public:
  uint16_t crc = 0;

  CRC_(void) {};

  void update(const void *data, uint8_t len);
  void finalize(void) {
    reflect(16);
  }
  void reflect(uint8_t len);
};

extern CRC_ CRC;
