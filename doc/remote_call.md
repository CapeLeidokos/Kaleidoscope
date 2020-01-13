# Remote Call

## Introduction

Kaleidoscope's remote call interface allows firmware functions to be directly 
called from the host. It also supports setting and retreiving values of 
global variables and member variables of global C++ objects. Communication
is carried out via the USB serial interface.

TODO: Explain the content of this document (sections).

## Motivation

Originally, the common way of data exchange between host and device was 
Kaleidoscope's Focus serial interface. This interface requires specific commands
and data to be exchanged between the host. Focus event handlers typically
do no proper value range and data type checking. Also they require a significant
amount of boiler plate code for command parsing, help string export and value routing.
Also, the implementation and handling of the Focus interface is relatively complex
e.g. when it comes to implementing Focus event handlers and understanding
what happens in case of a Focus event.

This brought up the idea to replace it entirely by an interface whose handling 
is as close as possible to ordinary C++ function calls and that goes entirely
without boiler plate code. Also the missing type and value checks are considered
really important, same as a way to add in-code documentation/description of
the exported functionality.

The *remote call* interface solves all of the above requirements. It even goes 
beyond some of the requirements, e.g. by not only removing boiler plate code 
but also by delegating most parts of the interface overhead to the host 
where resources are not limited in a similar way as on the device. The latter 
drastically reduces the program memory consumption and allows for a by far
greater amount of functionality being exported at the same costs as the Focus 
interface would allow.

## Features 

The following is a collection of the most important features of Kaleidoscope's 
remote call interface.

### Type safety

All standard `int*_t` and `uint*_t` data types
as well as `float` are supported as function arguments and results as well
as input variables. Data types and value ranges of data send and recieved
are automatically verified by the host.

### Minimum possible resource consumption

No code is required for serial command checking, error handling, data type and
value checking. Data is passed through shared buffers 
to and from functions that mostly wrap Kaleidoscope plugin and core functions.  

### Structured API

The remote call interface comes with a structured API that makes exporting
functions and inputs a simple task and minimizes the amount of boiler plate code.
Any complexity is hidden behind a layer of well documented macro functions.

### No boiler plate code

In contrast to the implementation of Focus event handlers, no boiler
plate code is required.

### Packaging

Exported functions and inputs can be hierarchically grouped as packages.

### Documentation of exported features

All entities (packages/functions/inputs/arguments/results) can be assigned
description (documentation) strings of arbitrary lenght without causing
any increase to the firmware binary size.

### Hierarchically shared information

Information such as update functions that are meant to be called upon changing
input variables can be defined on package level and shared (inherited) by all those
inputs that do not specify update functions of their own.

### Wrapper functions for common tasks

To export functions for remote calls simple wrapper functions need to be implemented
using the remote call API. This is comparably simple compared to writing Focus
event handlers.

### In-place updates of input variables

For some tasks, where specific plugin member or global variables are evaluated
in every cycle, it is much cheaper to change the value of such variables in place
instead of implementing wrapper functions. The remote call interface names such
variables *inputs* and allows them to be modified directly. The interface allows
to specify an update function, e.g. a global or static plugin member function
to be called automatically whenever an input is modified. This allows to issue
remote calls that do not consume any additional program memory.

### YAML export of remote call interface

By means of an external firmware post-processing tool, a YAML representation
of the exported functions and inputs can be generated that is used by
the supplied *remote* tool but can also be read by other tools such as
*Chrysalis*.

### Simple host-device communication

As the remote call API makes the RAM address of variables and functions
available to the host, the complex communication of most plugins 
can be routed through a single plugin that does the host-device data 
exchange via a very simple and robust peek/poke style of 
communication.

### Globally disabling the remote call infrastructure

Some users might prefer to use every byte of RAM and PROGMEM for other features
and might not have any use for remote calls.

If it's not needed, we do not want to waste resources for it. 
Thus, the overall remote call infrastructure can be disabled by defining
a single macro (`KALEIDOSCOPE_REMOTE_CALL_DISABLED`) at the top of the user sketch.
When doing so, any additional runtime overhead is prevented.

## Concepts

#### Exported Functions

An exported function is characterized by the following set of information.

* function name
* result variables (name and type - any number possible) 
* function arguments (name and type)
* function body (C++ code)
* description (optional)

For call arguments and result variables of all functions a common RAM area
is used. Its size matches the size of the lagerst set of arguments or results
of any defined remote call function.

No RAM or program memory is consumed for *function name* and *description*.

Remote functions may called by supplying name-value pairs for all arguments 
of a function together with the function's name to the *call* subcommand 
of the *remote* command line tool.

#### Exporting Inputs

Inputs can either be global variables or member variables of global class
objects. They are characterized by

* input name
* input type (global or member)
* update function
* description (optional)

The update function is a procedure (no arguments) that the interface requires to 
call (remotely) after changing the input variable.

Inputs are modified via the *set_input* subcommand of the *remote* command
line tool. The current value of a input can be queried using the *get_input* 
subcommand.

#### Packages

The remote call interface exports functions and inputs within package
namespaces. Packages enable grouping functions and inputs hierarchically and
supplying descriptions and inheritable update functions for a set of inputs.

#### Nesting Packages

Packages may be nested. Using the *remote* command line tool, functions or inputs need to be
specified via their complete package namespace path, 
e.g. as `TopLevelPackage::NestedPackage::aFunction`.

##### Update Functions and package level inheritance

Whenever an input does not supply an update function and is not explicitly marked
as not requiring an update, the *package_scan* tool will traverse the input's
package namespace path backward to find an appropriate update function.
This makes it possible to supply a default update function that can be overridden
by nested packages or by a dedicated update function that is defined by an 
input.

## Documentation

Apart from this document, the remote call API is documented in the file
`kaleidoscope/remote_call.h`. There's also a set of example sketches available 
under `examples/RemoteCall` in the Kaleidoscope repository.

## Usage

### Adding remote call capability to Kaleidoscope code

Any export directives of the remote call interface must either be added
to include files (only those that are available for being included in the 
Kaleidoscope sketch) or to the sketch itself.

Make sure to include the header `kaleidoscope/remote_call.h` in every
header file that you intent to export functions or input variables for
remote call from.

#### Exporting functions

The follwing is a commented version of the exported methods of
the *LEDControl* plugin.

```cpp
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
      
         // Export a function.
         //
         KRC_F(setCrgbAt, // The function's name (its package namespace path is
                          // 'plugin::LEDControl::setCrgbAt').
                          
            // The function has no result variables.
            //
            KRC_VOID_RESULT,
            
            // The function has five call arguments that are specified
            // by type and name. The whole set of arguments must be wrapped
            // in brackets. Every argument pair must be separated by a comma 
            // and also be wrapped in individual brackets.
            //
            ((uint8_t, row), (uint8_t, col),
             (uint8_t, red), (uint8_t, green), (uint8_t, blue)),
             
            // The function body wrapped in brackets. The two 
            // pointers 'args' and 'results' are automatically predefined
            // and appropriately typed. Both point to the beginning of the
            // common (overlapping) storage area in RAM that is used
            // for all functions' arguments and result variables.
            //
            (LEDControl.setCrgbAt(KeyAddr{args->row, args->col}, 
                                  CRGB(args->red, args->green, args->blue));),
                                  
            // The description is optional.
            //
            KRC_DESCRIPTION("Sets the LED color of a single key")
         )
         
         //...
         
         // Export a function to query the current LED mode. This function
         // has a non-void result pair but void arguments.
         //
         KRC_F(getMode, ((uint8_t, mode_id)), KRC_VOID_ARGS,
            (results->mode_id = LEDControl.get_mode_index();),
            KRC_DESCRIPTION("Queries the LED mode")
         )
      )
   )
)
```

#### Exporting global variables as inputs

To export a global variable as an input, the variable must already have been 
defined.

```cpp

extern uint8_t someGlobalVariable;
extern void someUpdateFunc();

KALEIDOSCOPE_REMOTE_CALL(
   KRC_PACKAGE(SomePackage,
   
      // Export a global variable as input.
      //
      KRC_GLOBAL(someGlobalVariable, // The variable name. Its package namespace
                                     // path is 'SomePackage::someGlobalVariable'.
                                     
         // The global variable to export. Important: Specify all exported
         // variables with complete C++ namespace path (starting with :: 
         // for the global namespace).
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

#### Inherited update functions

Update functions can be defined package-wise. Every input that does not
explicitly specify an update function will inherit the update function
defined on the next outer package level (if available).

See the example sketch `examples/RemoteCall/RemoteCall.ino` for further
information.

#### Descriptions

Description text can be added on every package level, for each exported function,
arguments, results and inputs. Description strings can have arbitrary size.
They will not be part of the final firmware binary but are exported as
part of the description of the remote call interface.

#### Disabling the remote call interface

The remote call interface can entirely be disabled by adding the following
to the very top of the sketch, before any include directives.

```cpp
#define KALEIDOSCOPE_REMOTE_CALL_DISABLED
```

### scan_packages tool

After the firmware has been build, it must be scanned for remote call exports
using the *scan_packages* tool that resides in the `bin/remote_call` folder
of the Kaleidoscope repository. This python script will extract any required
information from the firmware sketch object, the final firmware elf-file and
the linker-map file that were created during the build.

The following is an example off typical usage.

```
./scan_packages \
   --binutils_dir=<path_to_arduino>/arduino-1.8.10/hardware/tools/avr/bin/ \
   --binutils_prefix=avr- \
   --sketch_dir=/tmp/kaleidoscope-$USER/sketch/<sketch_dir> \
   --yaml_output_file=remote_call.yml
```

Please replace `<path_to_arduino>` and `<sketch_dir>` accordingly.

This will write the extracted package information to a YAML file named `remote_call.yml`.

Usage information is available via *scan_packages*' `-h` command line switch.

#### YAML export

The information generated by *scan_packages*
is used by the *remote* tool but can also be parsed by 3rd party tools that
may use it to communicate with devices in the same fashion.

It is important to mention that a remote call YAML file represents the
exported information of one version of a firmware that was build for a specific
device. It contains addressing information that are only valid on that
very device architecture.

This is an example of the YAML output.

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

### remote tool

The *remote* command line tool manages the communication between host and device. It is also
the reference implementation that can be used as a source of inspiration to add the same functionality
to other 3rd party tools.

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

We call such pieces of information *stowaways*.

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

Appart from exporting addresses of variables and functions, other information 
is valuable as well to enable validation of input data on the host.
The following pieces of information is exported by the remote call API for a
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
the entire system being optional. The whole thing can be disabled via 
a configuration in the firmware sketch. This means
in consequence that any code ...


TODO: Explain that the whole remote call export happens from the sketch
      by using the `KALEIDOSCOPE_SKETCH` macro.
TODO: Explain that only such functions and inputs are exported that are
      included directly or indirectly in the sketch.

### Protecting exported function against linker garbage collection

TODO: Explain how garbage collection can be prevented.
TODO: Explain how we do this recursively.

### Disabling remote call entirely

## TODO

### Firmware checksum

TODO: Explain how the checksum could be generated.

### Replace focus-test

TODO: Explain that currently focus-test is used under the hood.
