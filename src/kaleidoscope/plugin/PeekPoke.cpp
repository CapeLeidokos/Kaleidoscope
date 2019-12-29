/* Kaleidoscope - Firmware for computer input devices
 * Copyright (C) 2013-2019  Keyboard.io, Inc.
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
 */

#include "kaleidoscope/plugin/PeekPoke.h"
#include "kaleidoscope/plugin/FocusSerial.h"

namespace kaleidoscope {
namespace plugin {
namespace peek_poke {
struct TransferInfo {
   uintptr_t addr_int_;
   uint16_t size_bytes_;
   TransferInfo() {
      ::Focus.read(addr_int_);
      ::Focus.read(size_bytes_);
   }
   
   template<typename _T>
   void sendData() {
      ::Focus.send(*((_T*)addr_int_));
   }
   
   template<typename _T>
   void receiveData() {
      _T data;
      ::Focus.read(data);
      *(_T*)addr_int_ = data;
   }
};
} // namespace peek_poke
   
EventHandlerResult PeekPoke_::onFocusEvent(const char *command)
{
   using namespace peek_poke;
   
   if(::Focus.handleHelp(command, PSTR("read\nwrite\npeek\npoke\nupdate")))
    return EventHandlerResult::OK;
   
   if(strcmp_P(command, PSTR("read")) == 0) {
      
      TransferInfo ti;
         
      for(uint16_t n = 0; n < ti.size_bytes_; ++n) {
         auto addr = (uint8_t*)ti.addr_int_ + n;
         ::Focus.send(*addr);
      }
   }
   else if(strcmp_P(command, PSTR("write")) == 0) {
      
      TransferInfo ti;
      
      for(uint16_t n = 0; n < ti.size_bytes_; ++n) {
         uint8_t data;
         ::Focus.read(data);
         auto addr = (uint8_t*)ti.addr_int_ + n;
         *addr = data;
      }
   }
   else if(strcmp_P(command, PSTR("peek")) == 0) {
      TransferInfo ti;
      
      switch(ti.size_bytes_) {
         case 1:
            ti.sendData<uint8_t>();
            break;
         case 2:
            ti.sendData<uint16_t>();
            break;
         case 4:
            ti.sendData<uint32_t>();
            break;
         default:
            // Error
            break;
      }
   }
   else if(strcmp_P(command, PSTR("poke")) == 0) {
      TransferInfo ti;
      
      switch(ti.size_bytes_) {
         case 1:
            ti.receiveData<uint8_t>();
            break;
         case 2:
            ti.receiveData<uint16_t>();
            break;
//          case 4:
//             ti.receiveData<uint32_t>();
//             break;
         default:
            // Error
            break;
      }
   }
   else if (strcmp_P(command, PSTR("update")) == 0) {
      uintptr_t addr_int;
      ::Focus.read(addr_int);
      
      typedef void (*Func)();
      
      auto f = (Func)addr_int;
      
      f();
   }
   else {
    return EventHandlerResult::OK;
   }
   
    return EventHandlerResult::EVENT_CONSUMED;
}
   
} // namespace plugin
} // namespace kaleidoscope

kaleidoscope::plugin::PeekPoke_ PeekPoke;
