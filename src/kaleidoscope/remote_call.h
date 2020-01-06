#pragma once 
   
namespace kaleidoscope {
namespace remote_call {
   void exportSymbols();
   extern void *_______function_io_______;
} /* namespace remote_call */
} /* namespace kaleidoscope */

#define KRC_EXPORT_SYMBOLS \
   kaleidoscope::remote_call::exportSymbols();

#ifdef KALEIDOSCOPE_SKETCH
#ifndef KALEIDOSCOPE_REMOTE_CALL_DISABLED
   
// Make all members of all classes available for export.
// Note: This is a very dirty hack but avoids a lot of boilerplate friend 
//       declaractions. Also this is only happening in the sketch object
//       but not in any other objects where the classes are used.
//
#define private public
#define protected public

#include "kaleidoscope/macro_map.h"

namespace kaleidoscope {
namespace remote_call {

typedef void (*Callable)();
extern const uint8_t pointer_size;
const uint8_t pointer_size = sizeof(void*);

void _______noUpdate_______() {}

template<typename _T>
struct TypeNameTrait
{};

#define KRC_MEMBER_TYPE_TRAIT(TYPE, TYPE_ID) \
   template<> \
   struct TypeNameTrait<TYPE> \
   { \
      constexpr static uint8_t typeName() { \
         return TYPE_ID; \
      } \
   };
   
KRC_MEMBER_TYPE_TRAIT(uint8_t,     0)
KRC_MEMBER_TYPE_TRAIT(uint16_t,    1)
KRC_MEMBER_TYPE_TRAIT(uint32_t,    2)
KRC_MEMBER_TYPE_TRAIT(int8_t,      3)
KRC_MEMBER_TYPE_TRAIT(int16_t,     4)
KRC_MEMBER_TYPE_TRAIT(int32_t,     5)
KRC_MEMBER_TYPE_TRAIT(float,       6)

} // namespace remote_call
} // namespace kaleidoscope

namespace kaleidoscope {
namespace remote_call {
   
template<int _T>
union CallableArgsUnion
{
   CallableArgsUnion<_T - 1> rest_;
};

template<>
union CallableArgsUnion<-1>
{
   uint8_t dummy_; // Union must have at least one member
};

} // namespace remote_call
} // namespace kaleidoscope

#define _KM_DECLARE_PROCEDURE_IO_STRUCT_AUX(IO_STRUCT, CNTR) \
   namespace kaleidoscope { \
   namespace remote_call { \
      template<> \
      union CallableArgsUnion<CNTR> \
      { \
         IO_STRUCT data_; \
         CallableArgsUnion<CNTR - 1> rest_; \
      }; \
   } /* namespace remote_call */ \
   } /* namespace kaleidoscope */
   
#define _KRC_EXPORT_IO_STRUCT(IO_STRUCT) \
   _KM_DECLARE_PROCEDURE_IO_STRUCT_AUX(IO_STRUCT, __COUNTER__)
   
#define KRC_EXPORT_PROCEDURE(PROC, ...) \
   \
   namespace kaleidoscope { \
   namespace remote_call { \
      _KM_EXPORT_FUNCTION_AUX(PROC, __COUNTER__) \
   } /* namespace remote_call */ \
   } /* namespace kaleidoscope */ \
   \
   /* Export arguments and results */ \
   MAP(_KRC_EXPORT_IO_STRUCT, __VA_ARGS__)
   
#define KRC_INSTANCIATE_PROCEDURE_ARGUMENTS \
   namespace kaleidoscope { \
   namespace remote_call { \
      CallableArgsUnion<__COUNTER__> _______function_io_union_______; \
      KRC_EXPORT_VARIABLE(::kaleidoscope::remote_call::_______function_io_union_______) \
      void *_______function_io_______ = &_______function_io_union_______; \
   } /* namespace remote_call */ \
   } /* namespace kaleidoscope */
   
#define KRC_ACCESS_ARGS(STRUCT) \
   static_cast<const STRUCT *>(::kaleidoscope::remote_call::_______function_io_______)
#define KRC_ACCESS_RESULTS(STRUCT) \
   static_cast<STRUCT *>(::kaleidoscope::remote_call::_______function_io_______)
   
//******************************************************************************
// Enforced symbol export
//******************************************************************************
// During the linker stage, ld the linker will strip out any symbols (functions
// and global variables that are not referenced by any other function that is
// directly or indirectly called from main.
//
// To prevent symbols that we want to use for remote calls from being stripped
// we add dummy access instructions that are indirectly called from main.
// This is achieved by defining SymbolExporter template class specializations
// that do the assembler symbol access. The SymbolExporter classes are defined
// in a way that each specialization calls the apply() method of the specialization
// with the next lower integer template parameter. SymbolExporter<-1> ends
// the recursion. 
// 
// Every invokation of EXPORT_FUNCTION or EXPORT_VARIABLE defines a SymbolExporter
// class specialization whose integer value is defined by the continuously 
// growing intrinsic __COUNTER__ macro. That way we can be sure that each
// counter value is only used once. 3rd party use of the __COUNTER__ macro
// leads to gaps in the range of integer template parameters of the SymbolExporter
// specializations. This can be safely ignored as those gaps cause the standard
// implementation of SymbolExporter being used that just calls the next lower
// specialization. 
// 
// A final use of the __COUNTER__ macro in KRC_FINISH_EXPORTS
// ensures that all the eval() static methods of all template specializations
// are called from a function kaleidoscope::remote_call::exportSymbols() that
// is invoked by void Runtime_::setup() which is in turn called indirectly
// by main().

namespace kaleidoscope {
namespace remote_call {
   
template<int _T>
struct SymbolExporter
{
   __attribute__((always_inline))
   static void eval() {
      SymbolExporter<_T - 1>::eval();
   }
};

// End recursion
//
template<>
struct SymbolExporter<-1>
{
   __attribute__((always_inline))
   static void eval() {}
};

} // namespace remote_call
} // namespace kaleidoscope

#define _KM_EXPORT_FUNCTION_AUX(FUNC, CNTR) \
   template<> \
   struct SymbolExporter<CNTR> \
   { \
      __attribute__((always_inline)) \
      static void eval() { \
         asm volatile( \
            "ldi r26, lo8(%0)" :: "p" (FUNC)); \
         \
         SymbolExporter<CNTR - 1>::eval(); \
      } \
   };
   
#define KRC_EXPORT_FUNCTION(FUNC) _KM_EXPORT_FUNCTION_AUX(FUNC, __COUNTER__)

#define _KM_EXPORT_VARIABLE_AUX(VAR, CNTR) \
   template<> \
   struct SymbolExporter<CNTR> \
   { \
      __attribute__((always_inline)) \
      static void eval() { \
         asm volatile("" : "+r" (VAR)); \
         \
         SymbolExporter<CNTR - 1>::eval(); \
      } \
   };
   
#define KRC_EXPORT_VARIABLE(VAR) _KM_EXPORT_VARIABLE_AUX(VAR, __COUNTER__)
   
#define KRC_FINISH_EXPORTS \
   namespace kaleidoscope { \
   namespace remote_call { \
      void exportSymbols() { \
         SymbolExporter<__COUNTER__>::eval(); \
      } \
   } /* namespace remote_call */ \
   } /* namespace kaleidoscope */
   
//******************************************************************************

#define KALEIDOSCOPE_REMOTE_CALL(...) \
   namespace kaleidoscope { \
   namespace remote_call { \
      __VA_ARGS__ \
   } /* namespace remote_call */ \
   } /* namespace kaleidoscope */

#define KRC_DESCRIPTION(S) \
   namespace _______info_______ { \
      extern const char description[]; \
      const char description[] = S; \
   } /* namespace _______info_______ */
   
#define KRC_UPDATE(PROC) \
   namespace _______info_______ { \
      extern const kaleidoscope::remote_call::Callable callable; \
      const kaleidoscope::remote_call::Callable callable \
         = PROC; \
   } /* namespace _______info_______ */

#define KRC_INPUT(ENTRY_NAME, VARIABLE_NAME, ...)  \
      namespace _______inputs_______ { \
      namespace ENTRY_NAME { \
         \
         namespace _______info_______ { \
            extern const void* address; \
            const void* address = &object->VARIABLE_NAME; \
            \
            extern const uint16_t size; \
            const uint16_t size = sizeof(object->VARIABLE_NAME); \
            \
            extern const uint8_t type; \
            const uint8_t type \
               = TypeNameTrait<decltype(object->VARIABLE_NAME)>::typeName(); \
         } /* namespace _______info_______ */ \
         \
         __VA_ARGS__ \
      } /* namespace ENTRY_NAME */ \
      } /* namespace _______inputs_______ */
   
#define KRC_OBJECT(PACKAGE_NAME, OBJECT, ...) \
   namespace PACKAGE_NAME {\
      \
      /* The tag variable is only required to simplify regex \
       * parsing of packages \
       */ \
      extern const uint8_t _______package_______; \
      const uint8_t _______package_______ = 0; \
      \
      typedef decltype(OBJECT) ClassType; \
      \
      constexpr auto* object = &OBJECT; \
      \
      __VA_ARGS__ \
   } /* namespace PACKAGE_NAME */
   
#define KRC_PLUGIN(...) \
   KRC_OBJECT(__VA_ARGS__)
   
#define KRC_GLOBAL(MEMBER_NAME, VARIABLE, ...)  \
      namespace _______inputs_______ { \
      namespace MEMBER_NAME { \
         \
         namespace _______info_______ { \
            extern const void* address; \
            const void* address = &VARIABLE; \
            \
            extern const uint16_t size; \
            const uint16_t size = sizeof(VARIABLE); \
            \
            extern const uint8_t type; \
            const uint8_t type \
               = TypeNameTrait<decltype(VARIABLE)>::typeName(); \
         } /* namespace _______info_______ */ \
         \
         __VA_ARGS__ \
      } /* namespace MEMBER_NAME */ \
      } /* namespace _______inputs_______ */

#define KRC_PACKAGE(PACKAGE_NAME, ...) \
   namespace PACKAGE_NAME { \
      \
      /* The tag variable is only required to simplify regex \
       * parsing of packages \
       */ \
      extern const uint8_t _______package_______; \
      const uint8_t _______package_______ = 0; \
      \
      __VA_ARGS__ \
   } /* namespace PACKAGE_NAME */
   
#define _KRC_PROCESS_DATUM_AUX(NAME, ARGS_MEMBER_NAME, ...)  \
   namespace NAME { \
      namespace _______info_______ { \
         extern const uint16_t offset; \
         const uint16_t offset = (uint16_t)offsetof(StructType, ARGS_MEMBER_NAME); \
         \
         extern const uint16_t size; \
         const uint16_t size = sizeof(decltype(StructType{}.ARGS_MEMBER_NAME)); \
         \
         extern const uint8_t type; \
         const uint8_t type \
            = TypeNameTrait<decltype(StructType{}.ARGS_MEMBER_NAME)>::typeName(); \
      } /* namespace _______info_______ */ \
         \
      __VA_ARGS__ \
   } /* namespace NAME */
   
#define _KRC_PROCESS_DATUM(...) _KRC_PROCESS_DATUM_AUX __VA_ARGS__
   
#define KRC_ARGUMENTS(ARGS_TYPE, ...) \
   \
   namespace _______arguments_______ { \
      typedef ARGS_TYPE StructType; \
      MAP(_KRC_PROCESS_DATUM, __VA_ARGS__) \
   } /* namespace _______arguments_______ */ \
   
#define KRC_RESULTS(RESULT_TYPE, ...) \
   \
   namespace _______results_______ { \
      typedef RESULT_TYPE StructType; \
      MAP(_KRC_PROCESS_DATUM, __VA_ARGS__) \
   } /* namespace _______results_______ */ \
   
#define KRC_PROCEDURE(NAME, PROC, ARGS_TYPE, ...) \
   namespace _______function_______ { \
   namespace NAME { \
      namespace _______info_______ { \
         extern const kaleidoscope::remote_call::Callable callable; \
         const kaleidoscope::remote_call::Callable callable \
            = PROC; \
      } /* namespace _______info_______ */ \
      \
      __VA_ARGS__ \
   } /* namepspace NAME */ \
   } /* namespace _______function_______ */
   
#define KALEIDOSCOPE_REMOTE_CALL_END \
   KRC_FINISH_EXPORTS \
   KRC_INSTANCIATE_PROCEDURE_ARGUMENTS
   
#define KRC_STATIC_MEMBER_FUNCTION(NAME) &ClassType::NAME
#define KRC_GLOBAL_FUNCTION(FUNCTION_NAME) &FUNCTION_NAME
#define KRC_NO_UPDATE KRC_UPDATE(&kaleidoscope::remote_call::_______noUpdate_______)

// A soon as we find a way to incorporate remote call package scan during
// the build process, we can store a firmware checksum in the firmware elf file.
//
// #define KALEIDOSCOPE_REMOTE_CALL_HAVE_FIRMWARE_CHECKSUM
//
#ifdef KALEIDOSCOPE_REMOTE_CALL_HAVE_FIRMWARE_CHECKSUM
namespace kaleidoscope {
namespace remote_call {
   extern const PROGMEM int8_t firmware_checksum[8];
   const PROGMEM int8_t firmware_checksum[8] = { 0 };
} // namespace remote_call
} // namespace kaleidoscope
#endif
   
#else // #ifndef KALEIDOSCOPE_REMOTE_CALL_DISABLED

// If the remote call module is disabled, we need at least an empty
// symbol export function.
//
#define KRC_FINISH_EXPORTS \
   namespace kaleidoscope { \
   namespace remote_call { \
      void exportSymbols() {} \
   } /* namespace remote_call */ \
   } /* namespace kaleidoscope */

#endif // #ifndef KALEIDOSCOPE_REMOTE_CALL_DISABLED
#else

// An empty version of the KALEIDOSCOPE_REMOTE_CALL macro
// is required to be used in all non-sketch compilation units.
//
#define KALEIDOSCOPE_REMOTE_CALL(...)

#endif // #ifdef KALEIDOSCOPE_SKETCH
