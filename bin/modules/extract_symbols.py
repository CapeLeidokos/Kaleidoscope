#!/usr/bin/python
  
# -*- coding: utf-8 -*-

# -*- mode: python -*-

# Author: noseglasses (shinynoseglasses@gmail.com)

import os
import sys
import re
import subprocess
import struct
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

class UpdateFunction(object):
   
   def __init__(self, symbol_mangled, symbol_unmangled):
      self.symbol_mangled = symbol_mangled
      self.symbol_unmangled = symbol_unmangled
      self.address = None
      self.inherited = False
   
   def write(self, target, indent = ""):
      for (key, value) in self.__dict__.items():
         target.write(indent + "   " + key + ": " + str(value) + "\n")
   
class DataEntity(object):
   
   def __init__(self):
      self.symbol_mangled = None
      self.symbol_unmangled = None
      self.offset = 0
      self.size = 0
      self.type = None
      self.address = None
   
   def write(self, target, indent = ""):
      target.write(indent + "   symbol_unmangled: " + str(self.symbol_unmangled) + "\n")
      target.write(indent + "   symbol_mangled: " + str(self.symbol_mangled) + "\n")
      target.write(indent + "   address: " + str(self.address) + "\n")
      target.write(indent + "   offset: " + str(self.offset) + "\n")
      target.write(indent + "   size: " + str(self.size) + "\n")
      target.write(indent + "   type: " + str(self.type) + "\n")
         
class ModuleMember(object):
   
   def __init__(self, module, name):
      self.name = name
      self.description = None
      self.update_function = None
      self.data = DataEntity()
      
   def getName(self):
      return self.module.getName() + "::" + self.name
   
   def write(self, target, indent = ""):
      target.write(indent + self.name + "\n")
      target.write(indent + "   description: " + str(self.description) + "\n")
      
      target.write(indent + "   data:\n")
      self.data.write(target, indent + "   ")
      
      if self.update_function:
         target.write(indent + "   update_function:\n")
         self.update_function.write(target, indent + "   ")
         
   def getParentUpdateFunction(self):
      
      m = self.module
      
      while m:
         if m.update_function:
            return copy.deepcopy(m.update_function)
         else:
            m = m.parent_module
            
      return None
   
class Module(object):
   
   def __init__(self, name):
      self.name = name
      self.members = {}
      self.modules = {}
      self.description = None
      self.update_function = None
      self.parent_module = None
      
   def getName(self):
      return self.name
   
   def write(self, target, indent = ""):
      target.write(indent + self.name + "\n")
      target.write(indent + "   description: " + str(self.description) + "\n")
      if self.update_function:
         target.write(indent + "   update_function:\n")
         self.update_function.write(target, indent + "   ")
         
      if len(self.members) > 0:
         target.write(indent + "   members:\n")
         for member in self.members.values():
            member.write(target, indent + "      ")
      if len(self.modules) > 0:
         target.write(indent + "   modules:\n")
         for module in self.modules.values():
            module.write(target, indent + "      ")

# This class parses a mangled symbol name and extract related information
#
class Symbol(object):
   
   def __init__(self, extractor, name_mangled):
      
      self.extractor = extractor
      self.name_mangled = name_mangled
      self.name_unmangled = extractor.demangleSymbolName(self.name_mangled)
      
      self.is_module_symbol = False

      for module_name in extractor.module_names:
         
         member_name_regex = 'kaleidoscope::module::' + module_name \
            + '::(_______tag_______|_______members_______|_______info_______)' \
            + '(::([\w:]+))?'

         member_info_match = re.match(member_name_regex, self.name_unmangled)
         
         if member_info_match == None:
            continue
         
         self.is_module_symbol = True
         self.is_member_symbol = False
         self.module_name = module_name
         
         sub_type = member_info_match.group(1)
         rest = member_info_match.group(3)
         
         if sub_type == "_______tag_______":
            self.is_module_symbol = False
            break
         elif sub_type == "_______info_______":
            self.info_type = rest
         elif sub_type == "_______members_______":
            
            self.is_member_symbol = True
            
            member_data_regex = '(\w+)::_______info_______::(\w+)'
            member_data_match = re.match(member_data_regex, rest)
            
            if not member_data_match:
               logging.error("Strange member data \'" + rest + "\'")

            self.member_name = member_data_match.group(1)
            self.info_type = member_data_match.group(2)

            if not (   (self.info_type == "description") \
                    or (self.info_type == "size") \
                    or (self.info_type == "type") \
                    or (self.info_type == "update_function") \
                    or (self.info_type == "address")):
               logging.error("Strange module member datum \'" + self.info_type + "\'")
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
      
      args = parser.parse_args()
      
      self.sketch_dir = args.sketch_dir
      self.binutils_dir = args.binutils_dir
      self.binutils_prefix = args.binutils_prefix
      
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
         
   def findExecutables(self):
      
      self.objdump_executable = self.binutils_dir + '/' + self.binutils_prefix + 'objdump'
      
      if not is_exe(self.objdump_executable):
         logging.error('Unable to find objdump executable \'' + self.objdump_executable + '\'')
         
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
      self.listModules(sys.stdout)
      
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
      
   def getModuleMember(self, module_name, member_name):
         
      module = self.getModule(module_name)
      
      if not member_name in module.members.keys():
         module.members[member_name] = ModuleMember(module, member_name)
         module.members[member_name].module = module
         
      return module.members[member_name]
      
   def readRelocationInfo(self, objdump_output):
      
      # Parse relocation info generated by the compiler.
      # It enables the linker to generate correct addresses in case of program relocation.
      # Whenever the addresses of any global symbol has been assigned to a global variable
      # the linker must resolve this address at program startup and compute the correct value.
      #
      # Here we exploit this feature to determine the correct symbol that is used as update function
      # and to get the relative symbol offset or address of object member variables or global
      # variables.
      
      lines = objdump_output.splitlines()
      base_reloc_regex = "RELOCATION RECORDS FOR \[([\.\w]+)\]"
      
      info_regex = "\d+ \w+\s+(\S+)"
      
      target_regex_update_function = "\.text\.(\w+)"
      
      target_regex_address = "\.(bss|data)\.(\w+)(\+([\da-fA-Fx]+))?"
      
      skip = False
      parse_next_line = False
      for line in lines:
         
         if skip:
            skip = False
            continue
         
         if parse_next_line:
            
            parse_next_line = False
            
            if symbol.is_member_symbol:
               target = self.getModuleMember(symbol.module_name, symbol.member_name)
            else:
               target = self.getModule(symbol.module_name)
            
            match = re.match(info_regex, line)
            
            if match == None:
               logging.error("Strange reloc info line: \'" + line + "\'")
               
            reloc_target = match.group(1)
            
            match = re.match(target_regex_update_function, reloc_target)
            
            if match:
               target.update_function \
                  = UpdateFunction(match.group(1), \
                                   self.demangleSymbolName(match.group(1)))
            else:
               #print "target: " + reloc_target
               match = re.match(target_regex_address, reloc_target)
               if match:
                  target.data.symbol_mangled = match.group(2)
                  target.data.symbol_unmangled = self.demangleSymbolName(match.group(2))
                  
                  if match.group(4):
                     target.data.offset = int(match.group(4), 16)
                  else:
                     target.data.offset = 0
                     
                  #print "   " + target.getName() + "::symbol: " + target.symbol_unmangled
                  #print "   " + target.getName() + "::offset: " + str(target.symbol_offset)
            
            #print reloc_source + "->" + reloc_target
            
         reloc_line_match = re.match(base_reloc_regex, line)
         
         if not reloc_line_match:
            continue
         
         r_line_tokens = reloc_line_match.group(1).split('.')
         
         symbol_name_mangled = r_line_tokens[len(r_line_tokens) - 1]
         
         #print "Symbol mangled: " + symbol_name_mangled
         
         symbol = Symbol(self, symbol_name_mangled)
         
         if not symbol.is_module_symbol:
            continue
         
         #print "Is module symbol"
         if    (symbol.info_type == "update_function") \
            or (symbol.info_type == "address"):
            #print "Parsing next line"
            skip = True
            parse_next_line = True
            
   def readModules(self, objdump_output):
      
      module_regex = "\.(\w+kaleidoscope[0-9]+module[0-9]+\S+)"
      module_candidates = unique(re.findall(module_regex, objdump_output))
      
      self.module_names = []
      module_cand_regex = "kaleidoscope::module::([:\w]+)::_______tag_______"
      
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
         
         if not symbol.is_module_symbol:
            continue
         
         if symbol.is_member_symbol:
            target = self.getModuleMember(symbol.module_name, symbol.member_name)
         else:
            target = self.getModule(symbol.module_name)
         
         if symbol.info_type == "description":
            data = self.getValueFromSection(symbol.name_mangled)
            target.description = str(bytearray(data))
         elif symbol.info_type == "update_function":
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
            print symbol.module_name + "::" + symbol.member_name
            print "type " + str(data[0]) + "->" + type_ids[data[0]]
         else:
            logging.error("Strange info type \'" + symbol.info_type + "\'")
            
   # The linker map file provides information about where global variables
   # and functions reside in RAM and PROGMEM, respectively.
   #
   def parseMapFile(self):
      
      my_file = open(self.map_file, "rt")
      
      text_regex = '\s+\.(text|bss|data)\.(\w+)'
      address_line_regex = '\s+(\w+)\s'
      
      self.address_mappings = {}
      
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
            
            self.address_mappings[symbol_mangled] = address
            
            parse_next_line = False
            
            continue
         
         text_match = re.match(text_regex, line)
         
         if not text_match:
            continue
         
         symbol_mangled = text_match.group(2)
         parse_next_line = True
         
   # After the map file has been read, the absolute addresses of
   # module members and update functions need to be resolved.
   # This is done by checking the map file and calculating the right
   # addresses.
   #
   def collectSymbolAddressesOfModule(self, module = None):
      
      if module == None:
         for module in self.modules.values():
            self.collectSymbolAddressesOfModule(module)
         return
      
      for member in module.members.values():
         self.collectSymbolAddressesOfMember(member)
         
      for module in module.modules.values():
         self.collectSymbolAddressesOfModule(module)
         
      if module.update_function:
         if module.update_function.symbol_mangled in self.address_mappings.keys():
            module.update_function.address \
               = int(self.address_mappings[module.update_function.symbol_mangled], 16)
      
   def collectSymbolAddressesOfMember(self, member):
      
      if member.data.symbol_mangled in self.address_mappings.keys():
         member.data.address = int(self.address_mappings[member.data.symbol_mangled], 16) + member.data.offset - ram_memory_offset
      else:
         member.data.address = "unexported"
      
      if member.update_function:
         if member.update_function.symbol_mangled in self.address_mappings.keys():
            # Function addresses must be divided by two (two byte words)
            member.update_function.address \
               = int(self.address_mappings[member.update_function.symbol_mangled], 16)/2
         elif member.update_function.symbol_unmangled == "kaleidoscope::module::_______noUpdate_______()":
            member.update_function = None
         else:
            member.update_function.address = "unexported"
      else:
         member.update_function = member.getParentUpdateFunction()
         member.update_function.inherited = True
      
   def listModules(self, target):
      
      if len(self.modules) > 0:
         target.write("modules:\n")
         for module in self.modules.values():
            module.write(target)
      else:
         target.write("no modules\n")
         
if __name__ == "__main__":
   SymbolExtractor().run()
