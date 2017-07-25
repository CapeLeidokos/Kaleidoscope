#include "Kaleidoscope.h"


static bool handleSyntheticKeyswitchEvent(Key mappedKey, uint8_t keyState) {
  if (mappedKey.flags & RESERVED)
    return false;

  if (!(mappedKey.flags & SYNTHETIC))
    return false;

  if (mappedKey.flags & IS_INTERNAL) {
    return false;
  } else if (mappedKey.flags & IS_CONSUMER) {
    if (keyIsPressed(keyState)) {
      pressConsumer(mappedKey);
    } else if (keyWasPressed(keyState)) {
      releaseConsumer(mappedKey);
    }
  } else if (mappedKey.flags & IS_SYSCTL) {
    if (keyIsPressed(keyState)) {
      pressSystem(mappedKey);
    } else if (keyWasPressed(keyState)) {
      releaseSystem(mappedKey);
    }
  } else if (mappedKey.flags & SWITCH_TO_KEYMAP) {
    // Should not happen, handled elsewhere.
  }

  return true;
}

static bool handleKeyswitchEventDefault(Key mappedKey, byte row, byte col, uint8_t keyState) {
  //for every newly pressed button, figure out what logical key it is and send a key down event
  // for every newly released button, figure out what logical key it is and send a key up event

  if (mappedKey.flags & SYNTHETIC) {
    handleSyntheticKeyswitchEvent(mappedKey, keyState);
  } else if (keyIsPressed(keyState)) {
    pressKey(mappedKey);
  } else if (keyToggledOff(keyState) && (keyState & INJECTED)) {
    releaseKey(mappedKey);
  }
  return true;
}

void handleKeyswitchEvent(Key mappedKey, byte row, byte col, uint8_t keyState) {
  if (!(keyState & INJECTED)) {
    mappedKey = Layer.lookup(row, col);
  }
  for (byte i = 0; Kaleidoscope.eventHandlers[i] != NULL && i < HOOK_MAX; i++) {
    Kaleidoscope_::eventHandlerHook handler = Kaleidoscope.eventHandlers[i];
    mappedKey = (*handler)(mappedKey, row, col, keyState);
    if (mappedKey.raw == Key_NoKey.raw)
      return;
  }
  mappedKey = Layer.eventHandler(mappedKey, row, col, keyState);
  if (mappedKey.raw == Key_NoKey.raw)
    return;
  handleKeyswitchEventDefault(mappedKey, row, col, keyState);
}


void initializeKeyboard() {
  Keyboard.begin();
}

void pressKeyRaw(Key mappedKey) {
  Keyboard.press(mappedKey.keyCode);

}

void pressKey(Key mappedKey) {
  if (mappedKey.flags & SHIFT_HELD) {
    pressKeyRaw(Key_LeftShift);
  }
  if (mappedKey.flags & CTRL_HELD) {
    pressKeyRaw(Key_LeftControl);
  }
  if (mappedKey.flags & LALT_HELD) {
    pressKeyRaw(Key_LeftAlt);
  }
  if (mappedKey.flags & RALT_HELD) {
    pressKeyRaw(Key_RightAlt);
  }
  if (mappedKey.flags & GUI_HELD) {
    pressKeyRaw(Key_LeftGui);
  }

  pressKeyRaw(mappedKey);
}

void releaseKeyRaw(Key mappedKey) {
  Keyboard.release(mappedKey.keyCode);

}

void releaseAllKeys() {
  Keyboard.releaseAll();
}

void releaseKey(Key mappedKey) {
  if (mappedKey.flags & SHIFT_HELD) {
    releaseKeyRaw(Key_LeftShift);
  }
  if (mappedKey.flags & CTRL_HELD) {
    releaseKeyRaw(Key_LeftControl);
  }
  if (mappedKey.flags & LALT_HELD) {
    releaseKeyRaw(Key_LeftAlt);
  }
  if (mappedKey.flags & RALT_HELD) {
    releaseKeyRaw(Key_RightAlt);
  }
  if (mappedKey.flags & GUI_HELD) {
    releaseKeyRaw(Key_LeftGui);
  }
  releaseKeyRaw(mappedKey);
}



void sendKeyboardReport() {
  Keyboard.sendReport();
}

void initializeConsumerControl() {
  ConsumerControl.begin();
}

void pressConsumer(Key mappedKey) {
  ConsumerControl.press(mappedKey.keyCode);
}

void releaseConsumer(Key mappedKey) {
  ConsumerControl.release(mappedKey.keyCode);
}


void initializeSystemControl() {
  SystemControl.begin();
}

void pressSystem(Key mappedKey) {
  SystemControl.press(mappedKey.keyCode);
}

void releaseSystem(Key mappedKey) {
  SystemControl.release();
}


/** Mouse events
 * See above for commentary on connectionMask. */


void initializeMouse() {
  Mouse.begin();
}

void moveMouse(signed char x, signed char y, signed char wheel) {
  Mouse.move(x, y, wheel);
}

void clickMouseButtons(uint8_t buttons) {
  Mouse.click(buttons);
}

void pressMouseButtons(uint8_t buttons) {
  Mouse.press(buttons);
}

void releaseMouseButtons(uint8_t buttons) {
  Mouse.release(buttons);
}

/** Absolute mouse (grapahics tablet) events
 * See above for commentary on connectionMask. */

void initializeAbsoluteMouse() {
  AbsoluteMouse.begin();
}

void moveAbsoluteMouse(signed char x, signed char y, signed char wheel) {
  AbsoluteMouse.move(x, y, wheel);
}
void moveAbsoluteMouseTo(uint16_t x, uint16_t y, signed char wheel) {
  AbsoluteMouse.moveTo(x, y, wheel);
}

void clickAbsoluteMouseButtons(uint8_t buttons) {
  AbsoluteMouse.click(buttons);
}

void pressAbsoluteMouseButtons(uint8_t buttons) {
  AbsoluteMouse.press(buttons);
}

void releaseAbsoluteMouseButtons(uint8_t buttons) {
  AbsoluteMouse.release(buttons);
}
