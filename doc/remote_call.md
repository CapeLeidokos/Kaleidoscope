# Remote Call

Author: Florian Fleissner (shinynoseglasses@gmail.com)

## Introduction

Kaleidoscope's remote call interface exports firmware functions for being
directly called from the host. It supports setting and retreiving values of 
global variables. Device and host thereby communicate via USB serial.

This document is describes all aspects of the remote call interface.

It starts with a description of the motivation behind the development of 
the interface. Then the most important features of the interface are explained.
Before usage and implementation are described in detail, the most important
abstract concepts of the approach are explained. Then a
comparison of the interface's resource requirements is provided and a comparison
with the requirements of Focus event handlers. The document ends with a list
of possible enhancements.

## Motivation

Before the remote call infrastructure was implemented, the common way of 
data exchange between host and device was using the Focus interface and
by implementing Focus event handlers for plugins.

The focus interface comes with some shortcomings that the new approach
was supposed to fix, namely 

* its high amount of boiler plate code, 
* its comparably complex way of implementing event handlers,
* large resource consumption in terms of program memory,
* the absence of type safety in communication,
* the absence of value range checking with respect to the target data types and
* missing documentation (commands are stored in PROGMEM).

The remote call infrastructure does not intent to replace Focus entirely, it 
even uses it under the hood. It just intents to replace it in those 
applications where the use of Focus comes along with the above shortcommings.

The remote call interface does away with all shortcomings mentioned. It

* comes without boiler plate code (everything is tightly wrapped in well documented macros),
* has a very simple API,
* reduces PROGMEM consumption to approximately 20% of that of Focus event handlers,
* adds type safety and value range checks,
* encourages in-code documentation of the communication interface where
* documentation comes without runtime costs (no PROGMEM strings stored)
* and is exported with the overall interface description.

By delegating great parts of the communication overhead to the host, 
the remote call interface supports for a much larger set of functionality 
being exported for remote control than it would be possible by using
Focus event handlers.

## Features 

The previous section already names some of the new features of the remote call API 
and the most important differences to Focus event handlers. But some of the new 
features deserve a closer look.

### Type safety

All standard `int*_t` and `uint*_t` data types
as well as `float` are supported as function arguments and return values (results)
as well as for input variables. 

Any user input that is supposed to be passed to the device is automatically 
checked against the exported data types to see if types match and if values are within the
supported range.

### Minimum possible resource consumption

No additional code is required for checking serial commands. As error handling, 
data type and value ranges are checked by the host, no device resources are
consumed by this task. This is in contrast to Focus event handlers that require
a lot of string comparisons to root communication to the sender/receiver (plugin)
on the device side. 

Thin wrapper functions serve as a standardized and resource-saving 
communication interface for exported core and plugin functions.

### Packaging

Exported functions and inputs can be hierarchically grouped as packages.
This packaging may but does not have to follow Kaleidoscope's 
namespace hierarchy. It thus possibly enables an alternative grouping of 
information compared to the core/plugin structure which might better suite
the view of a non-programmer user.

### Documentation of exported features

All entities (packages/functions/inputs/arguments/results) can be assigned
description (documentation) strings of arbitrary length without affecting
firmware binary size.

### Hierarchically shared information

Information such as update procedures that are meant to be called upon changing
input variables can be defined on package level and shared (inherited) by 
nested packages and those inputs that do not specify update procedures of their own.

### Wrapper functions for common tasks

Exporting remote call functions means defining simple wrapper functions 
using the remote call API. This is comparably simple compared to writing Focus
event handlers.

### In-place updates of input variables

For some tasks, where specific plugin members or global variables are evaluated
in every cycle, it is cheaper to modify the value of such variables in place
instead of implementing wrapper functions. 

In the terminology of the remote call interface such
variables are named *inputs*. The interface allows
specification of an update procedure to be called automatically 
whenever an input is modified. See the description of inputs in the *concepts*
section for more details.

### YAML export of remote call interface

A YAML representation of the remote call interface for a given firmware
configuration can be auto-generated using the *scan_packages* script.
Such YAML files are meant to be used by the *remote* tool to handle
type safe host-device communication. The same files can also be read by 
other tools if they implement the *remote* scripts functionality.
*Chrysalis* would e.g. be a candidate.

### Simple host-device communication

As the remote call API makes the RAM address of variables and functions
available to the host, communication of most plugins 
can be routed through the RemoteCall plugin that handles the host-device data 
exchange via a very simple and robust typed PEEK/POKE communication interface.

### Globally disabling the remote call infrastructure

Some users might not have any use for remote calls and 
prefer to use every byte of RAM and PROGMEM for other features.

The implemention of the remote call interface respects that. If it's not needed, 
we should not want to waste resources for it.

Thus, the overall remote call infrastructure can be disabled by defining
a single macro (`KALEIDOSCOPE_REMOTE_CALL_DISABLED`) at the top of the user's sketch.

This will not only disable functionality but exclude any pieces of the remote
call infrastructure from being compiled. Thus, any additional runtime overhead
is prevented.

## Concepts

The remote call interface defines some concepts for the interaction between 
host and device, namely exported *remote call functions* and *inputs*.

#### Functions

An exported function is basically a way to make a C++ function accessible 
for being called remotely. It is characterized by the following information.

* function name
* function arguments (name and type)
* function return values/results (name and type) 
* function body (C++ code)
* description (optional)

The remote call API allows for functions to have multiple named return values.

No RAM or program memory is consumed neither for *function name* and *description*
nor for names and type information of arguments and results.

Remote functions are called by supplying name-value pairs for all function
arguments together with the function's name to the *call* subcommand 
of the *remote* command line tool (see the usage section).

#### Inputs

Inputs can either be global variables or member variables of global class
objects. They are characterized by their

* name,
* type (global or member),
* update procedure (optional) and
* description (optional).

If specified, the update procedure (a void function without arguments) 
is expected to be called remotely after changing the input variable for the
changes to be come effective. For such inputs that are picked up during
every firmware cycle no update procedure is required.

Inputs are modified via the *set_input* subcommand of the *remote* command
line tool. The current value of a input can be queried using the *get_input* 
subcommand (see the usage section for more information).

#### Packages

The remote call interface exports any functions and inputs within package
namespaces. Packaging enable grouping functions and inputs hierarchically and
supplying descriptions and inheritable update procedures for a set of inputs.
Packaging is similar to C++ namespaces but adds some additional features
such as sharing documentation and inheritance of input update procedures.

#### Nesting Packages

Packages may be nested. When passed as arguments to the *remote* 
command line tool, function or input names need to be
specified using their complete package namespace path, 
e.g. as `TopLevelPackage::NestedPackage::aFunction`.

##### Update Procedures and package level inheritance

Whenever an input does not supply an update procedure and is not explicitly marked
as not requiring an update, the *scan_packages* tool will traverse the input's
package namespace path in direction of the package trees root
to find an appropriate update procedure.
This allows to define a default update procedure that may optionally be overridden
by nested packages or by a dedicated update procedure that is defined by an 
input.

## Usage

### Adding remote call capability to Kaleidoscope code

Any export directives of the remote call interface must either be added
to C++ include files (only those that are available for being included in the 
Kaleidoscope sketch) or to the sketch .ino-file itself.

Make sure to include the header `kaleidoscope/remote_call.h` in every
header file that you intent to export functions or input variables for
remote call from.

#### Exporting functions

The follwing is a commented version of the exported methods of
Kaleidoscope's *LEDControl* plugin.

```cpp
#include "kaleidoscope/remote_call.h"

...

// Any remote call specifications must be wrapped by in
// an invocation of `KALEIDOSCOPE_REMOTE_CALL`. This allows any remote call
// exports to be globally disabled.
//
KALEIDOSCOPE_REMOTE_CALL(

   // Every function/input must be wrapped by at least one package level.
   // The root level must be specified by using the KRC_ROOT_PACKAGE(...)
   // function macro.
   //
   KRC_ROOT_PACKAGE(plugin,
   
      // All nested package levels are specified by invoking KRC_PACKAGE(...).
      //
      KRC_PACKAGE(LEDControl,
      
         // Export a function to set the LED color of an individual key.
         //
         KRC_F(setCrgbAt, // The function's name (its package namespace path is
                          // 'plugin::LEDControl::setCrgbAt').
                          
            // Signal the function to have no result variables.
            //
            KRC_VOID_RESULT,
            
            // The function has five call arguments that are specified
            // by type and name. The whole set of arguments must be wrapped
            // in brackets. Every argument pair must be separated by a comma 
            // and also be wrapped in individual brackets.
            //
            ((uint8_t, row), (uint8_t, col),
             (uint8_t, red), (uint8_t, green), (uint8_t, blue)),
             
            // The function body must also be wrapped in brackets. The two 
            // pointers 'args' and 'results' are always automatically predefined
            // and appropriately typed. Both point to the beginning of the
            // common (overlapping) storage area in RAM that is used
            // for all functions' arguments and result variables.
            //
            (
               LEDControl.setCrgbAt(KeyAddr{args->row, args->col}, 
                                    CRGB(args->red, args->green, args->blue));
            ),
                                  
            // The description text is optional.
            //
            KRC_DESCRIPTION("Sets the LED color of a single key")
         )
         
         //... more exported functions ...
         
         // Export a function to query the current LED mode. This function
         // has a non-void result pair and no arguments.
         //
         KRC_F(getMode, ((uint8_t, mode_id)), KRC_VOID_ARGS,
            (results->mode_id = LEDControl.get_mode_index();),
            KRC_DESCRIPTION("Queries the LED mode")
         )
      )
   )
)
```

#### Exporting inputs

To export a global variable as an input, the variable must already have been 
defined.

```cpp

extern uint8_t someGlobalVariable; // The variable to be exported as input.

extern void someUpdateFunc(); // An update procedure that is expected
                              // to be called by remote communication
                              // whenever the input has been modified.

KALEIDOSCOPE_REMOTE_CALL(

   KRC_PACKAGE(SomePackage,
   
      // Export a global variable as input.
      //
      KRC_GLOBAL(someGlobalVariable, // The variable name. Its package namespace
                                     // path is 'SomePackage::someGlobalVariable'.
                                     
         // The global variable to export. 
         //
         // Important: Specify all exported variables with complete 
         //            C++ namespace path (starting with :: 
         //            for the global namespace).
         //
         ::someGlobalVariable,
         
         // An (optional) description string.
         //
         KRC_DESCRIPTION("The red LED color portion")
         
         // The global function that is expected to be called remotely after the
         // input value has been modified.
         //
         KRC_UPDATE_THROUGH_GLOBAL_FUNCTION(::someUpdateFunc)
      )
   )
```

#### Exporting Kaleidoscope plugins as packages

To simplify exporting Kaleidoscope plugins as a package and to access 
the member variables of a global singleton instance of the plugin, 
an additional macro `KRC_Plugin(...)` is provided.

The following example assumes that there exists a plugin instance 
`kaleidoscope::plugin::MyPlugin`.

```cpp
KALEIDOSCOPE_REMOTE_CALL(
   KRC_PLUGIN(MyPlugin, // Remote call package name
      kaleidoscope::plugin::MyPlugin, // Global plugin instance
      KRC_DESCRIPTION("MyPlugin description") // optional description
      KRC_MEMBER(a, a_, // Exports plugin member a_ as a
         KRC_DESCRIPTION("a is ...") // optional
         // No update required
      )
      KRC_MEMBER(b, b_, 
         KRC_DESCRIPTION("b is ...")
         // Assumes the plugin class to have a static method 
         // void bUpdate()
         //
         KRC_UPDATE_THROUGH_STATIC_MEMBER_FUNCTION(bUpdate)
      )
      
      // Global functions can be added to the plugin package if necessary.
      //
      KRC_GLOBAL(someGlobalVariable, ::someGlobalVariable,
         KRC_UPDATE_THROUGH_GLOBAL_FUNCTION(::someUpdateFunc)
      )
   )
)
```

#### Inherited update procedures

Update procedures can be defined on package level. Every input that does not
explicitly specify an update procedure will inherit the update procedure
defined on the next higher package level (if available).

Exported inputs can specify the macro `KRC_NO_UPDATE` to explicity 
prevent update procedure inheritance.

See the example sketch `examples/RemoteCall/RemoteCall.ino` for further
information.

#### Descriptions

Description text can be added on package level, to exported functions,
arguments, results and inputs. Description strings can have arbitrary size
at zero cost.

#### Disabling the remote call interface

The entire remote call interface can be disabled by adding the following
to the very top of the sketch, before any include directives.

```cpp
#define KALEIDOSCOPE_REMOTE_CALL_DISABLED
```

### scan_packages tool

To export the remote call interface, the readily build firmware and its 
build artifacts must manually be post-processed using the *scan_packages* tool.
This tool, a Python script, currently resides in the `bin/remote_call` folder
of the Kaleidoscope repository.

The following is an example off a typical usage.

```
./scan_packages \
   --binutils_dir=<path_to_arduino_installation>/arduino-1.8.10/hardware/tools/avr/bin/ \
   --binutils_prefix=avr- \
   --sketch_dir=/tmp/kaleidoscope-$USER/sketch/<sketch_dir> \
   --yaml_output_file=remote_call.yml
```

Please replace `<path_to_arduino_installation>` and `<sketch_dir>` accordingly.

This will write the extracted package information to a YAML file named `remote_call.yml`
in the current working directory.

Usage information is available via *scan_packages*' `-h` command line switch.

#### YAML export

The information generated by *scan_packages* is exported as YAML files.
One such YAML file represents the remote call interface of one specific 
configuration of the firmware, build by a specific compiler version for a specific
device. It contains addressing information that is only valid on that
very device architecture. Because of that it is important to name the YAML files
appropriately. For more information, read the section about 
firmware checksums at the end of this document.

This is an example of possible YAML output of a remote call interface
specification. This information is generated by evaluating 
the information collected under the hood by the remote call API macros.

```yml
packages:
   - name: PackageLevel1
     description: PackageLevel1 description
     callable:
        address: 789
        symbol_mangled: _Z14updateMyPluginv
        symbol_unmangled: updateMyPlugin()
     packages:
      - name: PackageLevel2
        description: PackageLevel2 description
        callable:
           address: 789
           symbol_mangled: _Z14updateMyPluginv
           symbol_unmangled: updateMyPlugin()
        inputs:
         - name: blue
           description: The blue LED color portion
           data:
              address: 258
              base_address: 258
              offset: 0
              size: 1
              type: uint8_t
              symbol_unmangled: b
              symbol_mangled: b
           callable:
              address: 790
              symbol_mangled: _Z8someFuncv
              symbol_unmangled: someFunc()
              inherited: False
```

### Host-Device communication

The *remote* command line tool manages the communication between host and 
device. It serves as a reference implementation that can be adapted to add 
the same host-device communication functionality to other tools.




TODO:




The tool serves as a command interpreter and validates and converts user input to a set of
transactions with the device.

Here's an example that demonstrates how the remote tool is used to set the LED color of a specific
key-LED on the device.

```
cd <kaleidoscope_repo>/bin/remote_call
./remote \
   --kaleidoscope_repo_dir=$PWD/../../ \
   --yaml_model_file=<path_to_yaml_file> \
   call plugin::LEDControl::setCrgbAt row=1 col=2 red=255 green=0 blue=0
```

Please replace `<kaleidoscope_repo>` and `<path_to_yaml_file>` appropriately.

Commands are specified after any flags as a combination of command and arguments. In the above example the command `call` is supplied with the full package namespace path of the exported function and the arguments as name-value pairs. Arguments may be specified in arbitrary order.

Please note that it may be necessary to set the device via the `DEVICE` environment variable
in order for the serial communication to work, e.g. `DEVICE=/dev/ttyACM<x>` where `<x>` must be replaced
with an integer number that is assigned by the system when the device is plugged in.

Usage information is available via *remote*' `-h` command line switch.

## Implementation

The remote call interface is mostly based on a set of API function macros
that can be found in the file `kaleidoscope/remote_call.h`. 
Any public function macros start with the prefix `KRC_`.

In the following we will explain some important concepts the remote call
implementation is based upon.

### Linker garbage collection

When the Kaleidoscope firmware is build, first all relevant compilation units
are compiled and then passed to the linker which generates the .elf firmware
file in a separate processing step. During this step, the linker can
determine which symbols (functions and variables) are not accessed (called)
directly or indirectly by the `main(...)` function. As not used by the final
firmware, all such symbols are considered as garbage and removed.

This mechanism helps to keep the firmware binary as small as possible as device resources
are typically fairly restricted.

The same mechanism can elegantly be used to extract information about the firmware
that is otherwise only available to the compiler. The idea is to store such
information in symbols whose values are extracted before the final linker
stage eliminates them during garbage collection.

We call such pieces of meta information *stowaways*.

### Exporting data/program layout information

#### Stowaways

Any information that is available at compile time and possibly reflects characteristics
of the target platform is hard to access during normal builds if not instrumentalizing the
compiler which is currently only supported by the clang compiler suite.

But if such information is stored in variables that are exported from 
compiled object files, it can easily be retrieved using *binutils* tools 
that are typically shipped with the gcc compiler - at least for Arduino.

Let's look at a simple example that demonstrates how the runtime address of a global 
variable can be exported.

```cpp
// Define a global variable and optionally initialize it. We assume here
// that a_variable is protected against linker garbage collection due
// to being used in some place by the firmware.
//
uint8_t a_variable = 42;

// Mark the address symbol as extern to force the compiler to export it in
// the object file.
//
extern const void* a_variable_address;

// Store the address of a_variable. The pointer a_variable_address
// will later be removed during garbage collection.
//
const void* a_variable_address = &a_variable;
```

To obtain the load address of a_variable, we first parse the output 
of `objdump -x` and parse the relocation records to find the address of
the symbol (`a_variable`) that was assigned to the pointer `a_variable_address`.

For members of global class objects, we also have to parse the member's 
byte offset from the beginning of the memory area that is occupied by the
object.

The runtime address (the actual address used during program execution) 
can then be obtained as follows.
```
runtime_address = load_address + offset - ram_start_address
```

For non class typed global variables, `offset` is always zero.

Some architectures such as AVR, have different address spaces for RAM and
program memory. Those require a non zero `rams_start_address` to be subtracted. 
In the case of the AVR architecture this is `0x800000`.

The runtime address thus obtained can be passed via serial communication
to the device to assign data to `a_variable`.

The stowaway `a_variable_address` will be eliminated by the linker during
garbage collection and will not consume any runtime resources at all.

Exporting function addresses works exactly the same way except for `rams_start_address`
being ommited. Also the value of the runtime address of a function for AVR
must be divided by two as PROGMEM pointers for AVR are counting words instead of bytes.

#### Stowaway meta data export

Appart from exporting addresses of variables and functions, other pieces of
meta information enable validation of input data on the host.
The following meta information is exported by the remote call API for every
variable:

* address
* data size [integer, no. bytes]
* data type [string]
* name [string]
* description [string] (optional)

None of this information generates any runtime costs. By knowing a datum's 
size and data type, the host can automatically check if user specified input
data is of appropriate type and in the acceptable (signed/unsigned) value 
range. It can, thus, e.g. check if a value for a `int8_t` within the range 
[-128; 127].

It is important to mention that the stowaway approach elegantly solves the
task of making platform dependent information accessible that is otherwise hard to access as
only known to the compiler.

### Typed remote PEEK/POKE

To set the value of a global device variable, the host sends its address,
a data type enumerator and the value to be assigned to the host. 
Any values, regardless of their actual type, are transfered as 
unsigned data and, only if necessary, casted to signed data on the device.

This type of communication is handled by a very simple typed PEEK/POKE-style 
transfer protocol.

### Remote function calls

The same method as described for remotely reading/writing data is used
to call functions, i.e. the host sends the address to the device that then calls
the function through its pointer.

This method is somewhat restricted as passing arguments and results to and from function calls
is highly platform dependent. Some platforms might use stack variables, other registers and others again a mixture of both.

That's why there is no feasible way for the device to calling a function
without knowing its type already at compile time. The latter would not be very
convenient. Because of that, remote call supports wrapper procedures (void functions without arguments).
Arguments and results are exchanged via dedicated RAM areas.

Here's a basic example how this works.

```cpp

uint8_t someDeviceFunction(uint16_t arg) {
   // does something with arg and returns a value...
}

uint16_t result, arg;
void someDeviceFunction_remoteCallWrapper() {

   // The argument `arg` has automagically been assigned a value by 
   // the calling instance
   //
   result = someDeviceFunction(arg);
   
   // The calling instance will take care to pass the value of `result`
   // back to the host.
}
```

### Shared results/args structs

The problem with this approach is that all function might have different
number and type of arguments. But there is a solution. As a single tasking
system can only execute on function at a time, all functions' arguments
can share the same memory area. This can be achieved as follows.

```cpp
uint8_t f1(uint16_t arg) { ... }

cRGB f2(uint8_t arg1, uint8_t arg2) { ... }

struct F1Args {
   uint16_t arg;
};

struct F1Results {
   uint8_t res;
};

struct F2Args {
   uint8_t arg1, arg2;
};

struct F2Results {
   uint8_t r, g, b;
};

union SharedIOData {
   F1Args f1args;
   F1Results results;
   F2Args f2args;
   F2Results f2results;
};

SharedIOData shared_io_data;

void f1_remoteCallWrapper() { ... }

void f2_remoteCallWrapper() {

   auto args = static_cast<F1Args *>(&shared_io_data);
   auto results = static_cast<F1Results *>(&shared_io_data);
   
   cRGB r_tmp = f2(args->arg1, args->arg2);
   
   // Important: The memory area pointed to by `results` overlaps with 
   //            the area pointed to by `args`. Because of that,
   //            all arguments must be read from RAM before results can be
   //            assigned.
   
   results->r = cRGB.r;
   results->g = cRGB.g;
   results->b = cRGB.b;
}

```

Although the wrapper `f2_remoteCallWrapper` seems to contain a lot of code,
it can actually be compiled to a very small number of instructions by
an optimizing compiler like gcc.

A nice side effect of passing arguments/results via memory to wrapper
procedures is that we can have more than one function return value.

As the remote call API does only support a restricted set of intrinsic data types
(`uint*_t`, `int*_t` and float) any C++ structs must be passed member by member.
   
The remote call API uses template union specialization to automatically
compile a global `SharedIOData` data type for **all** functions
exported for remote call.

### Protecting exported function against linker garbage collection

The problem with remote call wrapper functions like `f1_remoteCallWrapper`
from previous section's example is that it is only meant to be used 
for remote calls and thus will never be called neither directly nor indirectly
from `main(...)`. Therefore it is a premium candidate for garbage collection.

There are some tricks to prevent garbage collection like using a custom
ld-linker script or setting the symbol's visibility to default (gcc). Unfortunately
the former would require very ugly tweaking of the build system and the
latter is not supported by AVR.

So the only solution to prevent a symbol from being garbage collected is
to let the firmware actually use it directly or indirectly. The term *using* here 
could mean *calling* for a function and *assign* or *reading* for a variable symbol.

All of those operations are not really intented as they will likely cause strange side
effects. Fortunately, *using* can also mean to read the address of the symbol.
This can even mean to just read the address and then doing nothing with the 
retreived value. The problem is that such kinds of operations will definitely
be optimized away by the compiler as an operation without effects and side effects.

There is still a way out of this dilemma, which is using inline assembler
instead of C++. That way we circumvent the compilers eagerness to optimize.

Here's a code example that accesses the lower byte of 
a global function pointer `f1_remoteCallWrapper`.

```cpp
asm volatile("ldi r26, lo8(%0)" :: "p" (f1_remoteCallWrapper));
```

This assembles to two bytes for opcode and address of the load instruction
and thus two bytes of PROGMEM per symbol that is supposed to be protected against
gargabe collected.

To automatically enable exported functions to be protected against gargabe
collection we use a combination of template specialization and recursive
namespace traversal. See the implementation of `_KRC_EXPORT_SYMBOLS_OF_NAMESPACE_AUX`
in `kaleidoscope/remote_call.h` for details about this approach.

### The sketch does the work

One important object of the design of the remote call API was to make 
the entire system being disabled. This is achieved via 
a configuration in the firmware sketch. This means
in consequence that the sketch compilation unit is the only place where 
anything related to remote calls can be compiled. 

For regardlessly being able to export inputs and functions from any other
part of the firmware, cord and plugins, the entire remote call export
specifications must be defined in headers that are included by the sketch.

The sketch will then generate the required infrastructure code by invoking
remote call API macros. 

For this approach to work, we have to ensure that in any other compilation units
any remote call macro invocations will evaluate empty. This is achieved
by passing all remote call API invocations to macro `KALEIDOSCOPE_REMOTE_CALL(...)`.
This macro is conditionally defined based on macro `KALEIDOSCOPE_SKETCH` being
defined or not, which is only true in the sketch compilation unit. Only there
it will evaluate non-empty.

As the whole remote call system relies on exports being defined in headers,
only for those headers directly or indirectly included by the sketch,
remote call exports will happen.

### Disabling remote call entirely

Disabling the remote call infrastructure entirely works by defining
`KALEIDOSCOPE_REMOTE_CALL(...)` for all compilation units.

## Resource Consumption

The remote call interface replaces Focus event handlers with thin wrappers
around existing firmware functions. The reduction of PROGMEM consumption 
is exemplified by comparing the Focus event handler function of the `LEDPaletteTheme`
plugin with an equivalent set of function exported for remote call.

The original Focus code reads as follows.

```cpp
EventHandlerResult LEDPaletteTheme::onFocusEvent(const char *command) {
  if (!Runtime.has_leds)
    return EventHandlerResult::OK;

  const char *cmd = PSTR("palette");

  if (::Focus.handleHelp(command, cmd))
    return EventHandlerResult::OK;

  if (strcmp_P(command, cmd) != 0)
    return EventHandlerResult::OK;

  if (::Focus.isEOL()) {
    for (uint8_t i = 0; i < 16; i++) {
      cRGB color;

      color = lookupPaletteColor(i);
      ::Focus.send(color);
    }
    return EventHandlerResult::EVENT_CONSUMED;
  }

  uint8_t i = 0;
  while (i < 16 && !::Focus.isEOL()) {
    cRGB color;

    ::Focus.read(color);
    color.r ^= 0xff;
    color.g ^= 0xff;
    color.b ^= 0xff;

    Runtime.storage().put(palette_base_ + i * sizeof(color), color);
    i++;
  }
  Runtime.storage().commit();

  ::LEDControl.refreshAll();

  return EventHandlerResult::EVENT_CONSUMED;
}
```

This method compiles to 284 bytes of PROGMEM.

The equivalent set of functions that enable querying and setting palette colors
reads as follows and compiles in total to only 56 bytes.

```cpp
KALEIDOSCOPE_REMOTE_CALL(
   KRC_ROOT_PACKAGE(plugin,
      KRC_PACKAGE(LEDPaletteTheme,
         KRC_F(getPaletteColor, 
               ((uint8_t, red), (uint8_t, green), (uint8_t, blue)),
               ((uint8_t, palette_index)),
            (
             cRGB color;
             color = LEDPaletteTheme.lookupPaletteColor(args->palette_index);
             results->red = color.r;
             results->green = color.g;
             results->blue = color.b;
            ),
            KRC_DESCRIPTION("Retrieves the RGB value of a palette color")
         )
         KRC_F(setPaletteColor, KRC_VOID_RESULT,
               ((uint8_t, palette_index), (uint8_t, red), (uint8_t, green), (uint8_t, blue)),
            (
              LEDPaletteTheme.setPaletteColor(args->palette_index,
                 cRGB{args->red, args->green, args->blue});
            ),
            KRC_DESCRIPTION("Sets the RGB value of a palette color")
         )
         KRC_F(commitPalette, KRC_VOID_RESULT, KRC_VOID_ARGS,
            (
              Runtime.storage().commit();
              ::LEDControl.refreshAll();
            ),
            KRC_DESCRIPTION("Sets the RGB value of a palette color")
         )
      )
   )
)
```

Comparing 284 to 56 bytes this means an amount of 228 bytes of PROGMEM 
being saved or an reduction by ~80%.

When taking a closer look at the above example, it becomes obvious that both
solutions do not exactly the same thing. The original Focus-based version
retreives and sets all palette colors at the same time while the remote call-based
version allows for individual colors to be set and supplies a function `commitPalette`
that is meant for changes to become effective. The reader might agree that
the latter version (remote call) is more versatile.

The RemoteCall plugin requires an additional 554 bytes of PROGMEM.

In contrast, currently the stock firmware dedicates ~1200 bytes to Focus handlers.
If those would be reduced to 20% by replacing the handlers with remote call
exports this would yield 240 bytes which, together with the 554 bytes
of the RemoteCall plugin, would sum up to ~800 bytes. 

This demonstrates that the size of the stock firmware binary could already 
be reduced by ~400 bytes by switching from Focus to remote call.

When additional remote communication will be added in the future the savings
with remote calls will become even more significant.

## Future enhancements/TODOs

There are some features that are currently not very simple to achieve. That's
why we put them on a to-do list.

### Firmware checksum

The remote call API provides advanced features such as type safety 
and value range checks at minimum resource overhead. This is achieved at the
cost of separating the interface specification (YAML-file) from the firmware 
binary during the *scan_packages* post-processing step.

To make sure that a YAML-interface definition matches the firmware running
on a device, a firmware checksum can be used. This checksum is computed
for the firmware object file and then stored in the final firmware.

Even though already implemented, this feature is currently disabled.

The reason is the lack of flexibility of Kaleidoscope's current Arduino build 
system and the fact that *scan_packages* is a Python script that currently 
requires a Python installation on the build host.

If that would be generally available or the build system would be Python driven,
we could add the execution of *scan_packages* as a build step
between the generation of the firmware .elf file and the objcopy step that generates
the .hex file.

The firmware checksum would then be stored on the device and in the YAML file.
Any tool that implements the remote call communication between host and device 
could then verify the remote call interface compatibility.

### Replace focus-test

Currently the *remote* tool relies on Focus and uses `Kaleidoscope/bin/focus-test`
under the hood. It would be preferable to add this functionality to *remote_call*'s
Python implementation and to auto-detect the `DEVICE` address.

## Documentation

Apart from this document, the remote call API is documented in the file
`kaleidoscope/remote_call.h`. There's also a set of example sketches available 
under `examples/RemoteCall` in the Kaleidoscope repository.
