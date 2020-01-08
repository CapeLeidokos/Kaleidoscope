#pragma once

#include "kaleidoscope/macro_helpers.h"
   
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

#define KRC_MEMBER_TYPE_TRAIT(TYPE, TYPE_ID)                                   \
   template<>                                                           __NL__ \
   struct TypeNameTrait<TYPE>                                           __NL__ \
   {                                                                    __NL__ \
      constexpr static uint8_t typeName() {                             __NL__ \
         return TYPE_ID;                                                __NL__ \
      }                                                                 __NL__ \
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

//******************************************************************************
// IO struct export
//******************************************************************************
// All remote call functions arguments and result values are stored in RAM.
// As Kaleidoscope is a single tasking system, we can allow all functions
// to store their arguments and result values in the same memory area.
//
// The following macros serve to define a global union that stores 
// arguments and result values of all functions.
//
// This is achieved by using recursively defined template unions on 
// every namespace level of packages and functions.

// Initializes IODataUnion collection on the level of every namespace.
//
#define _KRC_INIT_IO_DATA_EXPORT                                               \
   template<int _T>                                                     __NL__ \
   union IODataUnion                                                    __NL__ \
   {                                                                    __NL__ \
      IODataUnion<_T - 1> rest_;                                        __NL__ \
   };                                                                   __NL__ \
                                                                        __NL__ \
   template<>                                                           __NL__ \
   union IODataUnion<-1>                                                __NL__ \
   {                                                                    __NL__ \
      uint8_t dummy_; /* Union must have at least one member */         __NL__ \
   };

#define _KRC_IO_DATA_ADD_DATA_TYPE_AUX(DATA_TYPE, CNTR)                        \
   template<>                                                           __NL__ \
   union IODataUnion<CNTR>                                              __NL__ \
   {                                                                    __NL__ \
      DATA_TYPE data_;                                                  __NL__ \
      IODataUnion<CNTR - 1> rest_;                                      __NL__ \
   };
   
// Adds a data type to the global function arguments/results (IO data)
// union.
//
#define _KRC_IO_DATA_ADD_DATA_TYPE(DATA_TYPE) \
   _KRC_IO_DATA_ADD_DATA_TYPE_AUX(DATA_TYPE, __COUNTER__)
   
#define _KRC_IO_DATA_ADD_FROM_NAMESPACE_AUX(NAMESPACE, CNTR)                   \
   template<>                                                           __NL__ \
   union IODataUnion<CNTR>                                              __NL__ \
   {                                                                    __NL__ \
      NAMESPACE::IODataUnion<CNTR> nested_data_;                        __NL__ \
      IODataUnion<CNTR - 1> rest_;                                      __NL__ \
   };
   
// Adds the IO data union of a namespace to the IO data union of 
// the surrounding namespace.
//
#define _KRC_IO_DATA_ADD_FROM_NAMESPACE(NAMESPACE) \
   _KRC_IO_DATA_ADD_FROM_NAMESPACE_AUX(NAMESPACE, __COUNTER__)
   
// Inititializes the global IO data union
// (in namespace kaleidoscope::remote_call).
//
#define _KRC_GLOBAL_INIT_IO_DATA                                               \
   namespace kaleidoscope {                                             __NL__ \
   namespace remote_call {                                              __NL__ \
      _KRC_INIT_IO_DATA_EXPORT                                          __NL__ \
   } /* namespace remote_call */                                        __NL__ \
   } /* namespace kaleidoscope */
   
// Exports the global IO data union.
//
#define _KRC_GLOBAL_FINISH_IO_DATA                                             \
   namespace kaleidoscope {                                             __NL__ \
   namespace remote_call {                                              __NL__ \
      IODataUnion<__COUNTER__> _______function_io_union_______;         __NL__ \
      KRC_EXPORT_VARIABLE(::kaleidoscope::remote_call                   __NL__ \
         ::_______function_io_union_______)                             __NL__ \
      void *_______function_io_______                                   __NL__ \
            = &_______function_io_union_______;                         __NL__ \
   } /* namespace remote_call */                                        __NL__ \
   } /* namespace kaleidoscope */
   
// Accesses function arguments (casts the global IO union to a pointer to 
// the actual arguments struct).
//
#define KRC_ACCESS_ARGS()                                                      \
   static_cast<const _______arguments_______::StructType*>(             __NL__ \
      ::kaleidoscope::remote_call::_______function_io_______)
   
// Accesses function results (casts the global IO union to a pointer to 
// the actual results struct).
//
#define KRC_ACCESS_RESULTS()                                                   \
   static_cast<_______results_______::StructType*>(                     __NL__ \
      ::kaleidoscope::remote_call::_______function_io_______)
   
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
// with the next lower integer template parameter. SymbolExporter<CNTR> ends
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

// Initializes symbol export for a namespace level (package or function).
//
#define _KRC_INIT_SYMBOL_EXPORT                                                \
   template<int _T>                                                     __NL__ \
   struct SymbolExporter                                                __NL__ \
   {                                                                    __NL__ \
      __attribute__((always_inline))                                    __NL__ \
      static void eval() {                                              __NL__ \
         SymbolExporter<_T - 1>::eval();                                __NL__ \
      }                                                                 __NL__ \
   };                                                                   __NL__ \
                                                                        __NL__ \
   /* End recursion */                                                  __NL__ \
   /**/                                                                 __NL__ \
   template<>                                                           __NL__ \
   struct SymbolExporter<-1>                                            __NL__ \
   {                                                                    __NL__ \
      __attribute__((always_inline))                                    __NL__ \
      static void eval() {}                                             __NL__ \
   };
   
#define _KRC_EXPORT_SYMBOLS_OF_NAMESPACE_AUX(NAMESPACE, CNTR)                  \
   template<>                                                           __NL__ \
   struct SymbolExporter<CNTR>                                          __NL__ \
   {                                                                    __NL__ \
      __attribute__((always_inline))                                    __NL__ \
      static void eval() {                                              __NL__ \
         SymbolExporter<CNTR - 1>::eval();                              __NL__ \
         NAMESPACE::SymbolExporter<CNTR>::eval();                       __NL__ \
      }                                                                 __NL__ \
   };

// Collects symbol export of a namespace and ensures that it will
// be considered by the surrounding namespace.
//
#define _KRC_EXPORT_SYMBOLS_OF_NAMESPACE(NAMESPACE) \
   _KRC_EXPORT_SYMBOLS_OF_NAMESPACE_AUX(NAMESPACE, __COUNTER__)

#define _KRC_EXPORT_FUNCTION_AUX(FUNC, CNTR)                                   \
   template<>                                                           __NL__ \
   struct SymbolExporter<CNTR>                                          __NL__ \
   {                                                                    __NL__ \
      __attribute__((always_inline))                                    __NL__ \
      static void eval() {                                              __NL__ \
         asm volatile(                                                  __NL__ \
            "ldi r26, lo8(%0)" :: "p" (FUNC));                          __NL__ \
                                                                        __NL__ \
         SymbolExporter<CNTR - 1>::eval();                              __NL__ \
      }                                                                 __NL__ \
   };
   
// Exports a function. By issuing an assembler load command of the 
// function address, we prevent the function to be garbage collected.
//
#define KRC_EXPORT_FUNCTION(FUNC)                                              \
   _KRC_EXPORT_FUNCTION_AUX(FUNC, __COUNTER__)

#define _KRC_EXPORT_VARIABLE_AUX(VAR, CNTR)                                    \
   template<>                                                           __NL__ \
   struct SymbolExporter<CNTR>                                          __NL__ \
   {                                                                    __NL__ \
      __attribute__((always_inline))                                    __NL__ \
      static void eval() {                                              __NL__ \
         asm volatile("" : "+r" (VAR));                                 __NL__ \
                                                                        __NL__ \
         SymbolExporter<CNTR - 1>::eval();                              __NL__ \
      }                                                                 __NL__ \
   };
  
// Exports a global variable. By issuing an assembler load command of the 
// variable address, we prevent the variable to be garbage collected.
//
#define KRC_EXPORT_VARIABLE(VAR)                                               \
   _KRC_EXPORT_VARIABLE_AUX(VAR, __COUNTER__)
   
// Initialize symbol export in the outermost 
// namespace kaleidoscope::remote_call.
//
#define _KRC_GLOBAL_INIT_SYMBOL_EXPORT                                         \
   namespace kaleidoscope {                                             __NL__ \
   namespace remote_call {                                              __NL__ \
      _KRC_INIT_SYMBOL_EXPORT                                           __NL__ \
   } /* namespace remote_call */                                        __NL__ \
   } /* namespace kaleidoscope */
   
// Provide a function exportSymbols() that is called by the runtimes 
// intitialization method in order to prevent symbol garbage collection.
//
#define _KRC_GLOBAL_FINISH_SYMBOL_EXPORTS                                      \
   namespace kaleidoscope {                                             __NL__ \
   namespace remote_call {                                              __NL__ \
      void exportSymbols() {                                            __NL__ \
         SymbolExporter<__COUNTER__>::eval();                           __NL__ \
      }                                                                 __NL__ \
   } /* namespace remote_call */                                        __NL__ \
   } /* namespace kaleidoscope */
   
//******************************************************************************

// At the begin of a namespace (package or function) we initialize symbol export
// and IO data union collection.
//
#define _KRC_START_NAMESPACE(NAMESPACE)                                        \
   namespace NAMESPACE {                                                __NL__ \
      _KRC_INIT_SYMBOL_EXPORT                                           __NL__ \
      _KRC_INIT_IO_DATA_EXPORT
   
// At the end of every namespace we make the surrounding namespace collect
// the symbol export and IO data union information of the nested namespace.
//
#define _KRC_END_NAMESPACE(NAMESPACE)                                          \
   } /* namespace NAMESPACE */                                          __NL__ \
   _KRC_EXPORT_SYMBOLS_OF_NAMESPACE(NAMESPACE)                          __NL__ \
   _KRC_IO_DATA_ADD_FROM_NAMESPACE(NAMESPACE)
   
// For all namespaces that are opened and closes several times, such
// as e.g. _______inputs_______, we need to initialize the 
// export stuff only once.
//
#define _KRC_INIT_EXPORT_STUFF_FOR_NAMESPACE(NAMESPACE)                        \
   namespace NAMESPACE {                                                __NL__ \
      _KRC_INIT_SYMBOL_EXPORT                                           __NL__ \
      _KRC_INIT_IO_DATA_EXPORT                                          __NL__ \
   }
   
#define _KRC_FINALIZE_EXPORT_STUFF_FOR_NAMESPACE(NAMESPACE)                    \
   _KRC_EXPORT_SYMBOLS_OF_NAMESPACE(NAMESPACE)                                 \
   _KRC_IO_DATA_ADD_FROM_NAMESPACE(NAMESPACE)
   
// Adds a description to a package, function, argument, result or input.
//
#define KRC_DESCRIPTION(S)                                                     \
   namespace _______info_______ {                                       __NL__ \
      extern const char description[];                                  __NL__ \
      const char description[] = S;                                     __NL__ \
   } /* namespace _______info_______ */

// Associates an update function with an input.
//
#define KRC_UPDATE(FUNC)                                                       \
   namespace _______info_______ {                                       __NL__ \
      extern const kaleidoscope::remote_call::Callable callable;        __NL__ \
      const kaleidoscope::remote_call::Callable callable                __NL__ \
         = FUNC;                                                        __NL__ \
   } /* namespace _______info_______ */
   
// Use a global function as update for an input.
//
#define KRC_UPDATE_THROUGH_GLOBAL_FUNCTION(FUNC)                               \
   KRC_EXPORT_FUNCTION(FUNC)                                                   \
   KRC_UPDATE(&FUNC)
  
// Use a static class member function as update for an input.
//
#define KRC_UPDATE_THROUGH_STATIC_MEMBER_FUNCTION(NAME)                        \
   KRC_EXPORT_FUNCTION(ClassType::NAME)                                        \
   KRC_UPDATE(&ClassType::NAME)

// Defines an input.
//
#define KRC_MEMBER(NAME, VARIABLE_NAME, ...)                                    \
   /* Export stuff for namepspace _______inputs_______ has already been */     \
   /* initialized in KRC_PACKAGE(...)                                   */     \
   /**/                                                                        \
   namespace _______inputs_______ {                                     __NL__ \
   _KRC_START_NAMESPACE(NAME)                                           __NL__ \
                                                                        __NL__ \
      namespace _______info_______ {                                    __NL__ \
         extern const void* address;                                    __NL__ \
         const void* address = &object->VARIABLE_NAME;                  __NL__ \
                                                                        __NL__ \
         extern const uint16_t size;                                    __NL__ \
         const uint16_t size = sizeof(object->VARIABLE_NAME);           __NL__ \
                                                                        __NL__ \
         extern const uint8_t type;                                     __NL__ \
         const uint8_t type                                             __NL__ \
            = TypeNameTrait<decltype(object->VARIABLE_NAME)>            __NL__ \
                  ::typeName();                                         __NL__ \
      } /* namespace _______info_______ */                              __NL__ \
                                                                        __NL__ \
      __VA_ARGS__                                                       __NL__ \
   _KRC_END_NAMESPACE(NAME)                                             __NL__ \
   } /* namespace _______inputs_______ */
   
#define _KRC_PACKAGE_NAMESPACE_NAME(NAME, CNTR)                                \
   GLUE4(_______package, CNTR, _______, NAME)
   
// Defines a package level (packages may be hierarchically structured).
//
#define _KRC_PACKAGE_AUX(NAME, CNTR, ...)                                      \
   _KRC_START_NAMESPACE(_KRC_PACKAGE_NAMESPACE_NAME(NAME, CNTR))        __NL__ \
                                                                        __NL__ \
      _KRC_INIT_EXPORT_STUFF_FOR_NAMESPACE(_______inputs_______)        __NL__ \
      _KRC_INIT_EXPORT_STUFF_FOR_NAMESPACE(_______function_______)      __NL__ \
                                                                        __NL__ \
      /* The tag variable is only required to simplify regex */         __NL__ \
      /* parsing of packages                                 */         __NL__ \
      /**/                                                              __NL__ \
      extern const uint8_t _______package_______;                       __NL__ \
      const uint8_t _______package_______ = 0;                          __NL__ \
                                                                        __NL__ \
      __VA_ARGS__                                                       __NL__ \
                                                                        __NL__ \
      _KRC_FINALIZE_EXPORT_STUFF_FOR_NAMESPACE(_______inputs_______)    __NL__ \
      _KRC_FINALIZE_EXPORT_STUFF_FOR_NAMESPACE(_______function_______)  __NL__ \
                                                                        __NL__ \
   _KRC_END_NAMESPACE(_KRC_PACKAGE_NAMESPACE_NAME(NAME, CNTR))
   
#define KRC_PACKAGE(NAME, ...)                                                 \
   _KRC_PACKAGE_AUX(NAME, __COUNTER__, __VA_ARGS__)
   
// The outermost package level must be defined in namespace 
// kaleidoscope::remote_call. Therefore, we supply a dedicated macro to
// define the outermost package level.
//
#define KRC_PACKAGE_ROOT(PACKAGE_NAME, ...)                                    \
   namespace kaleidoscope {                                             __NL__ \
   namespace remote_call {                                              __NL__ \
      KRC_PACKAGE(PACKAGE_NAME, __VA_ARGS__)                            __NL__ \
   } /* namespace remote_call */                                        __NL__ \
   } /* namespace kaleidoscope */

// Defines a package that is associatd with a global class object.
//
#define KRC_OBJECT(NAME, OBJECT, ...)                                          \
   _KRC_PACKAGE_AUX(NAME, __COUNTER__,                                  __NL__ \
      typedef decltype(OBJECT) ClassType;                               __NL__ \
      constexpr auto* object = &OBJECT;                                 __NL__ \
                                                                        __NL__ \
      __VA_ARGS__                                                       __NL__ \
   )
   
// Defines a package that is associatd with a global class object that is
// a Kaleidoscope plugin.
//
#define KRC_PLUGIN(...) \
   KRC_OBJECT(__VA_ARGS__)
   
// Associates a global variable with an input.
//
#define KRC_GLOBAL(MEMBER_NAME, VARIABLE, ...)                                 \
   namespace _______inputs_______ {                                     __NL__ \
   _KRC_START_NAMESPACE(MEMBER_NAME)                                    __NL__ \
                                                                        __NL__ \
      KRC_EXPORT_VARIABLE(VARIABLE)                                     __NL__ \
                                                                        __NL__ \
      namespace _______info_______ {                                    __NL__ \
         extern const void* address;                                    __NL__ \
         const void* address = &VARIABLE;                               __NL__ \
                                                                        __NL__ \
         extern const uint16_t size;                                    __NL__ \
         const uint16_t size = sizeof(VARIABLE);                        __NL__ \
                                                                        __NL__ \
         extern const uint8_t type;                                     __NL__ \
         const uint8_t type                                             __NL__ \
            = TypeNameTrait<decltype(VARIABLE)>::typeName();            __NL__ \
      } /* namespace _______info_______ */                              __NL__ \
                                                                        __NL__ \
      __VA_ARGS__                                                       __NL__ \
   _KRC_END_NAMESPACE(MEMBER_NAME)                                      __NL__ \
   } /* namespace _______inputs_______ */
      
// An auxiliary macro that is used both to define function arguments and
// results.
//
#define _KRC_IO_DATUM_AUX(TYPE, NAME, ...)                                     \
   namespace NAME {                                                     __NL__ \
      namespace _______info_______ {                                    __NL__ \
         extern const uint16_t offset;                                  __NL__ \
         const uint16_t offset                                          __NL__ \
            = (uint16_t)offsetof(StructType, NAME);                     __NL__ \
                                                                        __NL__ \
         extern const uint16_t size;                                    __NL__ \
         const uint16_t size                                            __NL__ \
            = sizeof(decltype(StructType{}.NAME));                      __NL__ \
                                                                        __NL__ \
         extern const uint8_t type;                                     __NL__ \
         const uint8_t type                                             __NL__ \
            = TypeNameTrait<decltype(StructType{}.NAME)>                __NL__ \
                  ::typeName();                                         __NL__ \
      } /* namespace _______info_______ */                              __NL__ \
                                                                        __NL__ \
      __VA_ARGS__                                                       __NL__ \
   } /* namespace NAME */
   
#define _KRC_IO_DATUM(...) _KRC_IO_DATUM_AUX __VA_ARGS__

#define _KRC_IO_DATA_STRUCT_MEMBER_AUX(TYPE, NAME, ...)                        \
   TYPE NAME;
   
// Defines the member of an IO data struct (function argument or result).
//
#define _KRC_IO_DATA_STRUCT_MEMBER(...)                                        \
   _KRC_IO_DATA_STRUCT_MEMBER_AUX __VA_ARGS__
   
// Defines a function argument.
//
#define KRC_ARGUMENTS(...)                                                     \
   _KRC_START_NAMESPACE(_______arguments_______)                        __NL__ \
                                                                        __NL__ \
      struct StructType {                                               __NL__ \
         MAP(_KRC_IO_DATA_STRUCT_MEMBER, __VA_ARGS__)                   __NL__ \
      };                                                                __NL__ \
                                                                        __NL__ \
      MAP(_KRC_IO_DATUM, __VA_ARGS__)                                   __NL__ \
                                                                        __NL__ \
      _KRC_IO_DATA_ADD_DATA_TYPE(StructType)                            __NL__ \
                                                                        __NL__ \
   _KRC_END_NAMESPACE(_______arguments_______)
   
// Defines a function result.
//
#define KRC_RESULTS(...)                                                       \
   _KRC_START_NAMESPACE(_______results_______)                          __NL__ \
                                                                        __NL__ \
      struct StructType {                                               __NL__ \
         MAP(_KRC_IO_DATA_STRUCT_MEMBER, __VA_ARGS__)                   __NL__ \
      };                                                                __NL__ \
                                                                        __NL__ \
      MAP(_KRC_IO_DATUM, __VA_ARGS__)                                   __NL__ \
                                                                        __NL__ \
      _KRC_IO_DATA_ADD_DATA_TYPE(StructType)                            __NL__ \
                                                                        __NL__ \
   _KRC_END_NAMESPACE(_______results_______)
   
// Defines the body of a remote call function, exports the function
// and registers it with the remote call system.
//
#define KRC_FUNCTION_BODY(...)                                                 \
   void functionBody() {                                                __NL__ \
      __VA_ARGS__                                                       __NL__ \
   }                                                                    __NL__ \
                                                                        __NL__ \
   KRC_EXPORT_FUNCTION(functionBody)                                    __NL__ \
                                                                        __NL__ \
   namespace _______info_______ {                                       __NL__ \
      extern const kaleidoscope::remote_call::Callable callable;        __NL__ \
      const kaleidoscope::remote_call::Callable callable                __NL__ \
         = functionBody;                                                __NL__ \
   } /* namespace _______info_______ */
   
// Defines a remote call function.
//
#define KRC_FUNCTION(NAME, ...)                                                \
   /* Export stuff for namepspace _______function_______ */                    \
   /* has already been initialized in KRC_PACKAGE(...) */                      \
   /**/                                                                        \
   namespace _______function_______ {                                   __NL__ \
   _KRC_START_NAMESPACE(NAME)                                           __NL__ \
      __VA_ARGS__                                                       __NL__ \
   _KRC_END_NAMESPACE(NAME)                                             __NL__ \
   } /* namespace _______function_______ */
   
#define KALEIDOSCOPE_REMOTE_CALL_END                                           \
   _KRC_GLOBAL_FINISH_SYMBOL_EXPORTS                                           \
   _KRC_GLOBAL_FINISH_IO_DATA
   
#define KRC_NO_UPDATE                                                          \
   KRC_UPDATE(&kaleidoscope::remote_call::_______noUpdate_______)

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

_KRC_GLOBAL_INIT_SYMBOL_EXPORT
_KRC_GLOBAL_INIT_IO_DATA
   
#else // #ifndef KALEIDOSCOPE_REMOTE_CALL_DISABLED

// If the remote call module is disabled, we need at least an empty
// symbol export function.
//
#define _KRC_GLOBAL_FINISH_SYMBOL_EXPORTS                                      \
   namespace kaleidoscope {                                             __NL__ \
   namespace remote_call {                                              __NL__ \
      void exportSymbols() {}                                           __NL__ \
   } /* namespace remote_call */                                        __NL__ \
   } /* namespace kaleidoscope */

#endif // #ifndef KALEIDOSCOPE_REMOTE_CALL_DISABLED

#define KALEIDOSCOPE_REMOTE_CALL(...) __VA_ARGS__

#else

// An empty version of the KALEIDOSCOPE_REMOTE_CALL macro
// is required to be used in all non-sketch compilation units.
//
#define KALEIDOSCOPE_REMOTE_CALL(...)

#endif // #ifdef KALEIDOSCOPE_SKETCH
