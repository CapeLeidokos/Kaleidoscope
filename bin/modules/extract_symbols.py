#!/usr/bin/python
  
# -*- coding: utf-8 -*-

# -*- mode: python -*-

# Author: noseglasses (shinynoseglasses@gmail.com)

import os
import sys
import re
import subprocess
import logging
import copy

# For ARV, RAM (SRAM) starts at addr 0x0000000000800000
ram_memory_offset = int("0x0000000000800000", 16)

type_ids = { \
   0 : "uint8_t", \
   1 : "uint16_t", \
   2 : "uint32_t", \
   3 : "int8_t", \
   4 : "int16_t", \
   5 : "int32_t", \
   6 : "float" \
   }

indent_level = "   "

SYMBOL_TYPE_NONE = 0
SYMBOL_TYPE_MODULE = 1
SYMBOL_TYPE_MODULE_MEMBER = 2
SYMBOL_TYPE_PROCEDURE = 3
SYMBOL_TYPE_PROCEDURE_ARG = 4
      
def is_exe(fpath):
   return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

def unique(list1):
   list_set = set(list1)
   return (list(list_set))

def findFirstFile(directory, extension):
            
   for file in os.listdir(directory):
      if file.endswith(extension):
         return os.path.join(directory, file)
      
   return None

def dump_object(obj, target = sys.stdout, indent = ""):
   for (key, value) in obj.__dict__.items():
      target.write(indent + key + ": " + str(value) + "\n")

class ProcedureArgument(object):
   
   def __init__(self, procedure, name):
      self.name = name
      self.callable = procedure
      self.description = None
      self.data = DataEntity()
      
   def writeYaml(self, target, indent):
      target.write(indent + "- name: " + self.name + "\n")
      target.write(indent + "  description: " + self.description + "\n")
      target.write(indent + "  data:\n")
      self.data.writeYaml(target, indent + indent_level)

class Procedure(object):
   
   def __init__(self, module, name):
      self.module = module
      self.name = name
      self.callable = None
      self.arguments = {}
      
   def getArgument(self, name):
      
      if not name in self.arguments.keys():
         self.arguments[name] = ProcedureArgument(self, name)
         
      return self.arguments[name]
      
   def getName(self):
      return self.module.getName() + "::" + self.name
   
   def writeYaml(self, target, indent):
      target.write(indent + "- name: " + self.name + "\n")
      target.write(indent + "  callable:\n")
      self.callable.writeYaml(target, indent + indent_level)
      target.write(indent + "  arguments:\n")
      for arg in self.arguments.values():
         arg.writeYaml(target, indent + indent_level)

class Callable(object):
   
   def __init__(self, symbol_mangled, symbol_unmangled):
      self.symbol_mangled = symbol_mangled
      self.symbol_unmangled = symbol_unmangled
      self.address = None
      
   def writeYaml(self, target, indent):
      target.write(indent + "  address: " + str(self.address) + "\n")
      target.write(indent + "  symbol_mangled: " + str(self.symbol_mangled) + "\n")
      target.write(indent + "  symbol_unmangled: " + str(self.symbol_unmangled) + "\n")
      
      if "inherited" in self.__dict__.keys():
         target.write(indent + "  inherited: " + str(self.inherited) + "\n")
   
class DataEntity(object):
   
   def __init__(self):
      #self.symbol_mangled = None
      #self.symbol_unmangled = None
      self.offset = 0
      self.size = 0
      self.type = None
      self.address = None
      self.base_address = None
      
   def writeYaml(self, target, indent):
      target.write(indent + "  address: " + str(self.address) + "\n")
      target.write(indent + "  base_address: " + str(self.base_address) + "\n")
      target.write(indent + "  offset: " + str(self.offset) + "\n")
      target.write(indent + "  size: " + str(self.size) + "\n")
      target.write(indent + "  type: " + str(self.type) + "\n")
      if "symbol_unmangled" in self.__dict__.keys():
         target.write(indent + "  symbol_unmangled: " + str(self.symbol_unmangled) + "\n")
      if "symbol_mangled" in self.__dict__.keys():
         target.write(indent + "  symbol_mangled: " + str(self.symbol_mangled) + "\n")
         
class Input(object):
   
   def __init__(self, module, name):
      self.name = name
      self.description = ""
      self.callable = None
      self.data = DataEntity()
      
   def getName(self):
      return self.module.getName() + "::" + self.name
   
   def writeYaml(self, target, indent = ""):
      target.write(indent + "- name: " + self.name + "\n")
      
      target.write(indent + "  description: " + str(self.description) + "\n")
      
      target.write(indent + "  data:\n")
      self.data.writeYaml(target, indent + indent_level)
      
      if self.callable:
         target.write(indent + "  callable:\n")
         self.callable.writeYaml(target, indent + indent_level)
         
   def getParentCallable(self):
      
      m = self.module
      
      while m:
         if m.callable:
            return copy.deepcopy(m.callable)
         else:
            m = m.parent_module
            
      return None
   
class Module(object):
   
   def __init__(self, name):
      self.name = name
      self.inputs = {}
      self.procedures = {}
      self.modules = {}
      self.description = ""
      self.callable = None
      self.parent_module = None
      
   def getName(self):
      return self.name
   
   def writeYaml(self, target, indent = ""):
      target.write(indent + "- name: " + self.name + "\n")
      target.write(indent + "  description: " + str(self.description) + "\n")
      if self.callable:
         target.write(indent + "  callable:\n")
         self.callable.writeYaml(target, indent + indent_level)
         
      if len(self.inputs) > 0:
         target.write(indent + "  inputs:\n")
         for input in self.inputs.values():
            input.writeYaml(target, indent + indent_level)
            
      if len(self.procedures) > 0:
         target.write(indent + "  procedures:\n")
         for procedure in self.procedures.values():
            procedure.writeYaml(target, indent + indent_level)
            
      if len(self.modules) > 0:
         target.write(indent + "  modules:\n")
         for module in self.modules.values():
            module.writeYaml(target, indent + indent_level)

# This class parses a mangled symbol name and extract related information
#
class Symbol(object):
   
   def __init__(self, extractor, name_mangled):
      
      self.extractor = extractor
      self.name_mangled = name_mangled
      self.name_unmangled = extractor.demangleSymbolName(self.name_mangled)
      self.symbol_type = SYMBOL_TYPE_NONE
      
      self.is_relevant = False

      for module_name in extractor.module_names:
         
         input_name_regex = 'kaleidoscope::module::' + module_name \
            + '::(_______module_______|_______inputs_______|_______procedure_______|_______info_______)' \
            + '(::([\w:]+))?'

         input_info_match = re.match(input_name_regex, self.name_unmangled)
         
         if input_info_match == None:
            continue
         
         self.is_relevant = True
         self.symbol_type = SYMBOL_TYPE_MODULE
         self.module_name = module_name
         
         sub_type = input_info_match.group(1)
         rest = input_info_match.group(3)
         
         if sub_type == "_______module_______":
            self.is_relevant = False
            break
         elif sub_type == "_______info_______":
            self.info_type = rest
         elif sub_type == "_______inputs_______":
            
            self.symbol_type = SYMBOL_TYPE_MODULE_MEMBER
            
            input_data_regex = '(\w+)::_______info_______::(\w+)'
            input_data_match = re.match(input_data_regex, rest)
            
            if not input_data_match:
               logging.error("Strange input data \'" + rest + "\'")

            self.input_name = input_data_match.group(1)
            self.info_type = input_data_match.group(2)

            if not (   (self.info_type == "description") \
                    or (self.info_type == "size") \
                    or (self.info_type == "type") \
                    or (self.info_type == "callable") \
                    or (self.info_type == "address")):
               logging.error("Strange module input datum \'" + self.info_type + "\'")
               
         elif sub_type == "_______procedure_______":
         
            self.symbol_type = SYMBOL_TYPE_PROCEDURE
               
            proc_info_regex = '(\w+)::_______info_______::(\w+)'
            proc_data_match = re.match(proc_info_regex, rest)
            
            if proc_data_match:
               self.proc_name = proc_data_match.group(1)
               self.info_type = proc_data_match.group(2)
            else:
               
               args_info_regex = '(\w+)::_______arguments_______::(\w+)::_______info_______::(\w+)'
               args_data_match = re.match(args_info_regex, rest)
               
               if not args_data_match:
                  logging.error("Strange procedure args data \'" + rest + "\'") 
                  
               self.symbol_type = SYMBOL_TYPE_PROCEDURE_ARG
                  
               self.proc_name = args_data_match.group(1)
               self.arg_name = args_data_match.group(2)
               self.info_type = args_data_match.group(3)
         else:
            # Do not report an error to enable nested modules
            pass
     
class SymbolExtractor(object):
   
   def __init__(self):
      
      self.modules = {}
      
      self.parseCommandLineArgs()
      self.findExecutables()
      self.findBuildArtifacts()
      
   def run(self):
      self.readModulesAndSymbols()
      
   def parseCommandLineArgs(self):
      
      import argparse

      parser = argparse.ArgumentParser(description='Extracts module information from Kaleidoscope binaries.')
            
      parser.add_argument('--sketch_dir', \
                           help = 'Base build directory with sketch information')
      parser.add_argument('--binutils_dir', \
                           help = 'Directory where binutils are stored')
      parser.add_argument('--binutils_prefix', \
                           help = 'Prefix for binutils (optional)',
                           default = '')
      parser.add_argument('--yaml_output_file', \
                           help = 'The filename of a yaml output file to create',
                           default = '')
      
      args = parser.parse_args()
      
      self.sketch_dir = args.sketch_dir
      self.binutils_dir = args.binutils_dir
      self.binutils_prefix = args.binutils_prefix
      self.yaml_output_file = args.yaml_output_file
      
   def findBuildArtifacts(self):
      
      sketch_obj_dir = self.sketch_dir + '/build/sketch'
      
      self.sketch_object = findFirstFile(sketch_obj_dir, '.o')
      
      if not self.sketch_object:
         logging.error('Unable to find sketch object file')
      else:
         print 'Sketch object file: ' + self.sketch_object
         
      elf_dir = self.sketch_dir + '/build'
      
      self.map_file = findFirstFile(elf_dir, '.map')
      
      if not self.map_file:
         logging.error('Unable to find firmware linker map file')
      else:
         print 'Firmware linker map file: ' + self.map_file
                  
      self.elf_file = findFirstFile(elf_dir, '.elf')
      
      if not self.elf_file:
         logging.error('Unable to find firmware elf file')
      else:
         print 'Firmware elf file: ' + self.elf_file
         
   def findExecutables(self):
      
      self.objdump_executable = self.binutils_dir + '/' + self.binutils_prefix + 'objdump'
      
      if not is_exe(self.objdump_executable):
         logging.error('Unable to find objdump executable \'' + self.objdump_executable + '\'')
      
      self.objcopy_executable = self.binutils_dir + '/' + self.binutils_prefix + 'objcopy'
      
      if not is_exe(self.objcopy_executable):
         logging.error('Unable to find objcopy executable \'' + self.objcopy_executable + '\'')
         
      self.cpp_filt_executable = self.binutils_dir + '/' + self.binutils_prefix + 'c++filt'
      
      if not is_exe(self.cpp_filt_executable):
         logging.error('Unable to find c++filt executable \'' + self.cpp_filt_executable + '\'')
         
   def demangleSymbolName(self, name):
      
      cmd = [self.cpp_filt_executable, name]
      proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

      o, e = proc.communicate()
      
      return o.decode('utf8').rstrip()
   
   # Retreives the value of a mangled symbol from the sketch object file
   #
   def getValueFromSection(self, symbol_name_mangled):
      
      data = self.getValueFromSectionAux('.rodata.' + symbol_name_mangled)
      
      if data != None:
         return data
      
      data = self.getValueFromSectionAux('.data.' + symbol_name_mangled)
      
      if data != None:
         return data
      
      data = self.getValueFromSectionAux('.bss.' + symbol_name_mangled)
      
      if data != None:
         return data
      
      logging.error("Unable to find section for mangled symbol \'" + symbol_name_mangled \
         + "\' in sketch object file")
      
   def getValueFromSectionAux(self, section_name):
      
      cmd = [self.objdump_executable, '-s', '-j', section_name, self.sketch_object]
      proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

      o, e = proc.communicate()
      
      objdump_output = o.decode('utf8')
         
      lines = objdump_output.splitlines()
      
      data = []
       
      data_regex = "^\s*[\da-fA-F]+\s*(([\da-fA-F]+\s*)+)"
      
      in_data_lines = False 
      for line in lines:
         if in_data_lines:
            data_block = re.match(data_regex, line)
            
            if not data_block:
               logging.error('Unable to find data block for section \'' + section_name \
                             + '\' in sketch object file')
            
            tokens = data_block.group(1).split()
            
            block_regex = "([\da-fA-F][\da-fA-F])"
            for token in tokens:
               
               for byte in re.findall(block_regex, token):
                  data.append(int(byte, 16))
         else:
            if line.find('Contents of section') != -1: 
               in_data_lines = True
         
      if not in_data_lines:
         return None

      return data
              
   # Read module and symbol information from the sketch object and the map 
   # file.
   #
   def readModulesAndSymbols(self):
      
      cmd = [self.objdump_executable, '-x', self.sketch_object]
      proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

      o, e = proc.communicate()
      
      objdump_output = o.decode('utf8')
      
      self.readModules(objdump_output)
      self.readRelocationInfo(objdump_output)
      self.extractModuleInfo(objdump_output)
      self.parseMapFile()
      self.collectSymbolAddressesOfModule()
      self.resolveProcedureArgsAbsAddress()
      
      self.replaceElfFileChecksum()
      #self.listModules(sys.stdout)
      
      if self.yaml_output_file:
         with open(self.yaml_output_file, 'w') as yaml_file:
            self.writeYaml(yaml_file)
      else:
         self.writeYaml(sys.stdout)
      
   def getModule(self, module_name):
      
      module_tokens = module_name.split("::")
      
      cur_modules = self.modules
      cur_module = None

      for token in module_tokens:
         
         if not token in cur_modules.keys():
            cur_modules[token] = Module(token)
            cur_modules[token].parent_module = cur_module
         
         cur_module = cur_modules[token]
         cur_modules = cur_module.modules

      return cur_module
      
   def getInput(self, module_name, input_name):
         
      module = self.getModule(module_name)
      
      if not input_name in module.inputs.keys():
         module.inputs[input_name] = Input(module, input_name)
         module.inputs[input_name].module = module
         
      return module.inputs[input_name]
   
   def getModuleProcedure(self, module_name, procedure_name):
         
      module = self.getModule(module_name)
      
      if not procedure_name in module.procedures.keys():
         module.procedures[procedure_name] = Procedure(module, procedure_name)
         module.procedures[procedure_name].module = module
         
      return module.procedures[procedure_name]
   
   def readRelocationLine(self, line, symbol):
      
      match = re.match("\d+ \w+\s+(\S+)", line)
      reloc_target = match.group(1)
      
      if match == None:
         logging.error("Strange reloc info line: \'" + line + "\'")
         
      if symbol.symbol_type == SYMBOL_TYPE_MODULE_MEMBER:
         target = self.getInput(symbol.module_name, symbol.input_name)
      elif symbol.symbol_type == SYMBOL_TYPE_MODULE:
         target = self.getModule(symbol.module_name)
      elif symbol.symbol_type == SYMBOL_TYPE_PROCEDURE:
         target = self.getModuleProcedure(symbol.module_name, symbol.proc_name)
      elif symbol.symbol_type == SYMBOL_TYPE_PROCEDURE_ARG:
         target = self.getModuleProcedure(symbol.module_name, symbol.proc_name).getArgument(symbol.proc_arg)
      else:
         logging.error("Strange symbol type " + str(symbol.symbol_type))
         dump_object(symbol, sys.stdout, indent_level)
      
      match = re.match("\.text\.(\w+)", reloc_target)
      
      if match:
         target.callable \
            = Callable(match.group(1), \
                              self.demangleSymbolName(match.group(1)))
      else:
         #print "target: " + reloc_target
      
         match = re.match("\.(bss|data)\.(\w+)(\+([\da-fA-Fx]+))?", reloc_target)
         if match:
            target.data.symbol_mangled = match.group(2)
            target.data.symbol_unmangled = self.demangleSymbolName(match.group(2))
            
            if match.group(4):
               target.data.offset = int(match.group(4), 16)
            else:
               target.data.offset = 0
            
   def readRelocationInfo(self, objdump_output):
      
      # Parse relocation info generated by the compiler.
      # It enables the linker to generate correct addresses in case of program relocation.
      # Whenever the addresses of any global symbol has been assigned to a global variable
      # the linker must resolve this address at program startup and compute the correct value.
      #
      # Here we exploit this feature to determine the correct symbol that is used as update procedure
      # and to get the relative symbol offset or address of object input variables or global
      # variables.
      
      lines = objdump_output.splitlines()
      base_reloc_regex = "RELOCATION RECORDS FOR \[([\.\w]+)\]"
      
      skip = False
      parse_next_line = False
      for line in lines:
         
         if skip:
            skip = False
            continue
         
         if parse_next_line:
            
            parse_next_line = False
            
            self.readRelocationLine(line, symbol)
            
         reloc_line_match = re.match(base_reloc_regex, line)
         
         if not reloc_line_match:
            continue
         
         r_line_tokens = reloc_line_match.group(1).split('.')
         
         symbol_name_mangled = r_line_tokens[len(r_line_tokens) - 1]
         
         #print "Symbol mangled: " + symbol_name_mangled
         
         symbol = Symbol(self, symbol_name_mangled)
         
         if not symbol.is_relevant:
            continue
         
         #print "Is module symbol"
         if    (symbol.info_type == "callable") \
            or (symbol.info_type == "address"):
            #print "Parsing next line"
            skip = True
            parse_next_line = True
            
   def readModules(self, objdump_output):
      
      module_regex = "\.(\w+kaleidoscope[0-9]+module[0-9]+\S+)"
      module_candidates = unique(re.findall(module_regex, objdump_output))
      
      self.module_names = []
      module_cand_regex = "kaleidoscope::module::([:\w]+)::_______module_______"
      
      for module_candidate in module_candidates:
         module_candidate_unmangled = self.demangleSymbolName(module_candidate)
         
         match = re.match(module_cand_regex, module_candidate_unmangled)
         
         if match:
            module_name = match.group(1)
            
            if not module_name in self.module_names:
               self.module_names.append(module_name)
         
   def extractModuleInfo(self, objdump_output):
      
      print ""
      
      module_regex = '\.(\w+kaleidoscope[0-9]+module\w+)'
      symbol_names_mangled = unique(re.findall(module_regex, objdump_output))
      
      for symbol_name_mangled in symbol_names_mangled:
         
         symbol = Symbol(self, symbol_name_mangled)
         
         if not symbol.is_relevant:
            continue
         
         if symbol.symbol_type == SYMBOL_TYPE_MODULE:
            
            target = self.getModule(symbol.module_name)
            
            if symbol.info_type == "description":
               data = self.getValueFromSection(symbol.name_mangled)
               target.description = str(bytearray(data))[:-1] # remove last char
            elif symbol.info_type == "callable":
               # Parsed from relocation data
               pass
            elif symbol.info_type == "address":
               # Parsed from relocation data
               pass
            else:
               logging.error("Strange module info type \'" + symbol.info_type + "\'")
               
         elif symbol.symbol_type == SYMBOL_TYPE_MODULE_MEMBER:
            
            target = self.getInput(symbol.module_name, symbol.input_name)
            
            if symbol.info_type == "description":
               data = self.getValueFromSection(symbol.name_mangled)
               target.description = str(bytearray(data))[:-1] # remove last char
            elif symbol.info_type == "callable":
               # Parsed from relocation data
               pass
            elif symbol.info_type == "address":
               # Parsed from relocation data
               pass
            elif symbol.info_type == "size":
               data = self.getValueFromSection(symbol.name_mangled)
               target.data.size = data[0] + 0xFF*data[1]
            elif symbol.info_type == "type":
               data = self.getValueFromSection(symbol.name_mangled)
               target.data.type = type_ids[data[0]]
            else:
               logging.error("Strange module input info type \'" + symbol.info_type + "\'")
               
         elif symbol.symbol_type == SYMBOL_TYPE_PROCEDURE:
            
            target = self.getModuleProcedure(symbol.module_name, symbol.proc_name)
            
            if symbol.info_type == "description":
               data = self.getValueFromSection(symbol.name_mangled)
               target.description = str(bytearray(data))[:-1] # remove last char
            elif symbol.info_type == "callable":
               # Parsed from relocation data
               pass
            else:
               logging.error("Strange module procedure info type \'" + symbol.info_type + "\'")
               
         elif symbol.symbol_type == SYMBOL_TYPE_PROCEDURE_ARG:
            
            proc = self.getModuleProcedure(symbol.module_name, symbol.proc_name)
            target = proc.getArgument(symbol.arg_name)
            
            if symbol.info_type == "description":
               data = self.getValueFromSection(symbol.name_mangled)
               target.description = str(bytearray(data))[:-1] # remove last char
            elif symbol.info_type == "offset":
               data = self.getValueFromSection(symbol.name_mangled)
               target.data.offset = data[0]
            elif symbol.info_type == "size":
               data = self.getValueFromSection(symbol.name_mangled)
               target.data.size = data[0] + 0xFF*data[1]
            elif symbol.info_type == "type":
               data = self.getValueFromSection(symbol.name_mangled)
               target.data.type = type_ids[data[0]]
            else:
               logging.error("Strange module procedure argument info type \'" + symbol.info_type + "\'")
               
         else:
            logging.error("Strange symbol type \'" + str(symbol.symbol_type) + "\'")
            
   # The linker map file provides information about where global variables
   # and functions reside in RAM and PROGMEM, respectively.
   #
   def parseMapFile(self):
      
      my_file = open(self.map_file, "rt")
      
      text_regex = '\s+\.(text|bss|data)\.(\w+)'
      address_line_regex = '\s+(\w+)\s'
      
      self.unmangled_symbol_to_address = {}
      self.mangled_symbol_to_address = {}
      
      parse_next_line = False
      in_map_section = False
      
      for line in my_file.readlines():
         
         if not in_map_section:
            if line.find("Linker script and memory map") != -1:
               in_map_section = True
            continue
         
         if parse_next_line:
            address_line_match = re.match(address_line_regex, line)
            
            if not address_line_match:
               logging.error("Strange address line \'" + line + "\'")
               
            address = address_line_match.group(1)
            
            self.unmangled_symbol_to_address[symbol_unmangled] = address
            self.mangled_symbol_to_address[symbol_mangled] = address
            
            parse_next_line = False
            
            continue
         
         text_match = re.match(text_regex, line)
         
         if not text_match:
            continue
         
         symbol_mangled = text_match.group(2)
         symbol_unmangled = self.demangleSymbolName(symbol_mangled)
         parse_next_line = True
         
   # After the map file has been read, the absolute addresses of
   # module inputs and update procedures need to be resolved.
   # This is done by checking the map file and calculating the right
   # addresses.
   #
   def collectSymbolAddressesOfModule(self, module = None):
      
      if module == None:
         for module in self.modules.values():
            self.collectSymbolAddressesOfModule(module)
         return
      
      for sub_module in module.modules.values():
         self.collectSymbolAddressesOfModule(sub_module)
         
      if module.callable:
         self.collectSymbolAddressesOfCallable(module.callable)
            
      for input in module.inputs.values():
         self.collectSymbolAddressesOfData(input.data)
         self.collectSymbolAddressesOfCallable(input.callable, input = input)
         
      for procedure in module.procedures.values():
         self.collectSymbolAddressesOfCallable(procedure.callable)
     
   def collectSymbolAddressesOfData(self, data):
      
      if not "symbol_unmangled" in data.__dict__.keys():
         logging.error("Data is missing symbol_unmangled key")
         dump_object(data)
      
      if data.symbol_unmangled in self.unmangled_symbol_to_address.keys():
         data.address = int(self.unmangled_symbol_to_address[data.symbol_unmangled], 16) + data.offset - ram_memory_offset
         data.base_address = int(self.unmangled_symbol_to_address[data.symbol_unmangled], 16) - ram_memory_offset
      else:
         data.address = "unexported"
         data.base_address = "unexported"

   def collectSymbolAddressesOfCallable(self, callable, input = None):
      
      if callable:
         if callable.symbol_unmangled in self.unmangled_symbol_to_address.keys():
            # Function addresses must be divided by two (two byte words)
            callable.address \
               = int(self.unmangled_symbol_to_address[callable.symbol_unmangled], 16)/2
         elif callable.symbol_unmangled == "kaleidoscope::module::_______noUpdate_______()":
            callable = None
         else:
            callable.address = "unexported"
            
         if input:
            callable.inherited = False
      elif input:
         callable = input.getParentCallable()
         callable.inherited = True
         
   def resolveProcedureArgsAbsAddressProc(self, procedure):
      
      for arg in procedure.arguments.values():
         arg.data.address = self.args_start + arg.data.offset - ram_memory_offset
         arg.data.base_address = self.args_start - ram_memory_offset
         arg.data.symbol_unmangled = self.args_symbol_unmangled
      
   def resolveProcedureArgsAbsAddress(self, module = None):
      
      if module == None:

         self.args_symbol_unmangled = 'kaleidoscope::module::_______procedure_args_union_______'
         
         if not self.args_symbol_unmangled in self.unmangled_symbol_to_address.keys():
            logging.error("Unable to find address of symbol \'" + self.args_symbol_unmangled + '\'')
         
         self.args_start = int(self.unmangled_symbol_to_address[self.args_symbol_unmangled], 16)
         
         for module in self.modules.values():
            self.resolveProcedureArgsAbsAddress(module)
         return
      
      for procedure in module.procedures.values():
         self.resolveProcedureArgsAbsAddressProc(procedure)
      
   #def listModules(self, target):
      
      #if len(self.modules) > 0:
         #target.write("modules:\n")
         #for module in self.modules.values():
            #module.write(target)
      #else:
         #target.write("no modules\n")
         
   def computeFileHash64(self, filename):
      
      import hashlib
 
      hasher = hashlib.sha1()
      with open(filename, 'rb') as afile:
         buf = afile.read()
         hasher.update(buf)
         
      return int(hasher.hexdigest(), 16) % (2 ** 64)
   
   def replaceElfFileChecksum(self):
      
      data = self.getValueFromSectionAux('.progmem.data._ZN12kaleidoscope6module17firmware_checksumE')
      
      checksum = 0
      for datum in data:
         checksum += datum
      
      checksum = self.computeFileHash64(self.sketch_object)
      
      import struct
      self.checksum_bytearray = bytearray(struct.pack('<Q', checksum))
      
      if checksum != 0:
         print "Checksum " + str(map(hex, data)) + " already set"
         return
      
      checksum_file = self.sketch_object + '.checksum'
      with open(checksum_file, 'w+b') as f:
         f.write(self.checksum_bytearray)
         
      print "Setting checksum " + str(hex(checksum))
      
      cmd = [self.objcopy_executable, "--update-section", ".progmem.data._ZN12kaleidoscope6module17firmware_checksumE=" + checksum_file, self.sketch_object]
      
      proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

      o, e = proc.communicate()
         
   def writeYaml(self, target):
      
      target.write("checksum: ")
      
      for byte in self.checksum_bytearray:
         target.write(str(hex(byte)) + " ")
      target.write("\n")
      
      target.write("modules:\n")
      if len(self.modules) > 0:
         for module in self.modules.values():
            module.writeYaml(target, indent_level)
         
if __name__ == "__main__":
   SymbolExtractor().run()
