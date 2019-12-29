// Any code that appears here is added to the top of the preprocessed sketch file.

#define KALEIDOSCOPE_SKETCH

// Only while we are scanning modules, we want all class inventory to be public
// to make member variables publicly available.
//
#define KALEIDOSCOPE_MODULE_SCAN

#ifdef KALEIDOSCOPE_MODULE_SCAN
#define private public
#define protected public
#endif
