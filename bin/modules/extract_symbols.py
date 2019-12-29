#!/usr/bin/python
  
# -*- coding: utf-8 -*-

# -*- mode: python -*-

import os
import sys
import re
import subprocess
import struct
      
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

def error(msg):
   
   print "Error: " + msg
   
class ModuleMember(object):
   
   def __init__(self, module, name):
      self.module = module
      self.name = name
      
   def getName(self):
      return self.module.getName() + "::" + self.name
   
   def write(self, target, indent = ""):
      target.write(indent + self.name + "\n")
      for (key, value) in self.__dict__.items():
         target.write(indent + "   " + key + ": " + str(value) + "\n")
   
class Module(object):
   
   def __init__(self, name):
      self.name = name
      self.members = {}
      self.modules = {}
      self.description = None
      self.update_function = None
      
   def getName(self):
      return self.name
   
   def write(self, target, indent = ""):
      target.write(indent + self.name + "\n")
      target.write(indent + "   description: " + str(self.description) + "\n")
      target.write(indent + "   update_function: " + str(self.update_function) + "\n")
      target.write(indent + "   members:\n")
      for member in self.members.values():
         member.write(target, indent + "      ")
      target.write(indent + "   modules:\n")
      for module in self.modules.values():
         module.write(target, indent + "      ")
      
class Symbol(object):
   
   def __init__(self, extractor, name_mangled):
      
      self.extractor = extractor
      self.name_mangled = name_mangled
      self.name_demangled = extractor.demangleSymbolName(self.name_mangled)
      
      self.is_module_symbol = False

      for module_name in extractor.module_names:
         
         member_name_regex = 'kaleidoscope::module::' + module_name + '::(_______tag_______|_______members_______|_______info_______)(::([\w:]+))?'

         member_info_match = re.match(member_name_regex, self.name_demangled)
         
         if member_info_match == None:
            #print "No match for mangled \'" + self.name_mangled + "\'"
            #print "No match for demangled \'" + self.name_demangled + "\'"
            #print "With regex " + member_name_regex
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
               error("Strange member data \'" + rest + "\'")

            self.member_name = member_data_match.group(1)
            self.info_type = member_data_match.group(2)
            
            #print "Member " + member_name
            #print "Datum " + member_datum

            if not (   (self.info_type == "description") \
                    or (self.info_type == "size") \
                    or (self.info_type == "update_function") \
                    or (self.info_type == "address")):
               error("Strange module member datum \'" + self.info_type + "\'")
         else:
            #error("Strange datum \'" + member_info_match.group(1) + "\'")
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
         error('No sketch object file found')
      else:
         print 'Sketch object file: ' + self.sketch_object
         
      elf_dir = self.sketch_dir + '/build'
      
      self.elf_binary = findFirstFile(elf_dir, '.elf')
      
      if not self.elf_binary:
         error('No elf finary found')
      else:
         print 'Elf binary file: ' + self.elf_binary
         
      elf_dir = self.sketch_dir + '/build'
      
      self.map_file = findFirstFile(elf_dir, '.map')
         
   def findExecutables(self):
      
      self.objdump_executable = self.binutils_dir + '/' + self.binutils_prefix + 'objdump'
      
      if not is_exe(self.objdump_executable):
         error('Unable to find objdump executable \'' + self.objdump_executable + '\'')
         
      self.cpp_filt_executable = self.binutils_dir + '/' + self.binutils_prefix + 'c++filt'
      
      if not is_exe(self.cpp_filt_executable):
         error('Unable to find c++filt executable \'' + self.cpp_filt_executable + '\'')
         
   def demangleSymbolName(self, name):
      
      cmd = [self.cpp_filt_executable, name]
      proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

      o, e = proc.communicate()
      
      return o.decode('utf8').rstrip()
   
   def getValueFromSection(self, symbol_name, section_size):
      
      data = self.getValueFromSectionAux('.rodata.' + symbol_name, section_size)
      
      if data != None:
         return data
      
      data = self.getValueFromSectionAux('.data.' + symbol_name, section_size)
      
      if data != None:
         return data
      
      error("Unable to find section for symbol \'" + symbol_name + "\'")
      
   def getValueFromSectionAux(self, section_name, section_size):
      
      cmd = [self.objdump_executable, '-s', '-j', section_name, self.sketch_object]
      proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

      o, e = proc.communicate()
      
      objdump_output = o.decode('utf8')
         
      lines = objdump_output.splitlines()
      
      data = []
       
      data_regex = "^\s*[\da-fA-F]+\s*(([\da-fA-F]+\s*)+)"
      
      in_data_lines = False 
      for line in lines:
         #print line
         if in_data_lines:
            data_block = re.match(data_regex, line)
            
            if not data_block:
               error('Unable to find data block for section \'' + section_name + '\'')
            
            tokens = data_block.group(1).split()
            
            #print 'Line: ' + line + ' (' + str(len(tokens)) + ' tokens)'
            #print 'Data block: ' + data_block.group(1)
            block_regex = "([\da-fA-F][\da-fA-F])"
            for token in tokens:
               
               for byte in re.findall(block_regex, token):
               
                  #print 'byte: ' + byte
                  number = int(byte, 16)
                  #print number
               
                  data.append(number)
         else:
            if line.find('Contents of section') != -1: 
               in_data_lines = True
         
      if not in_data_lines:
         return None
         #error("Unable to find value for section \'" + section_name + "\' (" + str(section_size) + ")")

      return data
              
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
      self.listModules()
      
   def getModule(self, module_name):
      
      module_tokens = module_name.split("::")
      
      cur_modules = self.modules

      for token in module_tokens:
         
         if not token in cur_modules.keys():
            cur_modules[token] = Module(token)
            
         cur_module = cur_modules[token]
         cur_modules = cur_module.modules

      return cur_module
      
   def getModuleMember(self, module_name, member_name):
         
      module = self.getModule(module_name)
      
      if not member_name in module.members.keys():
         module.members[member_name] = ModuleMember(module, member_name)
         
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
      
      target_regex_address = "\.bss\.(\w+)(\+([\da-fA-Fx]+))?"
      
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
               error("Strange reloc info line: \'" + line + "\'")
               
            reloc_target = match.group(1)
            
            match = re.match(target_regex_update_function, reloc_target)
            
            if match:
               target.update_function = match.group(1);
               print "   " + target.getName() + "::update_function: " + target.update_function
            else:
               #print "target: " + reloc_target
               match = re.match(target_regex_address, reloc_target)
               if match:
                  target.address_base_symbol = match.group(1)
                  
                  if match.group(3):
                     target.address_offset = match.group(3)
                  else:
                     target.address_offset = "0x0"
                     
                  print "   " + target.getName() + "::address_base_symbol: " + target.address_base_symbol
                  print "   " + target.getName() + "::address_offset: " + str(target.address_offset)
            
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
      
      #.rodata._ZN12kaleidoscope6module9MyPlugin
      
      module_regex = "\.(\w+kaleidoscope[0-9]+module[0-9]+\S+)"
      module_candidates = unique(re.findall(module_regex, objdump_output))
      
      self.module_names = []
      module_cand_regex = "kaleidoscope::module::([:\w]+)::_______tag_______"
      
      for module_candidate in module_candidates:
         module_candidate_demangled = self.demangleSymbolName(module_candidate)
         
         match = re.match(module_cand_regex, module_candidate_demangled)
         
         if match:
            module_name = match.group(1)
            
            if not module_name in self.module_names:
               self.module_names.append(module_name)
      
      #print "Modules:"
      #for module in self.module_names:
         #print "   " + module
         
   def extractModuleInfo(self, objdump_output):
      
      print ""
      
      module_regex = '\.(\w+kaleidoscope[0-9]+module\w+)'
      symbol_names_mangled = unique(re.findall(module_regex, objdump_output))
      
      for symbol_name_mangled in symbol_names_mangled:
         
         symbol = Symbol(self, symbol_name_mangled)
         
         if not symbol.is_module_symbol:
            #print "Non module: " + symbol_name_mangled
            continue
         
         if symbol.is_member_symbol:
            target = self.getModuleMember(symbol.module_name, symbol.member_name)
         else:
            target = self.getModule(symbol.module_name)
         
         if symbol.info_type == "description":
            data = self.getValueFromSection(symbol.name_mangled, 0)
            target.description = str(bytearray(data))
            print "   " + target.getName() + "::description: " + target.description
         elif symbol.info_type == "update_function":
            # Parsed from relocation data
            pass
         elif symbol.info_type == "address":
            # Parsed from relocation data
            pass
         elif symbol.info_type == "size":
            data = self.getValueFromSection(symbol.name_mangled, 0)
            target.size = data[0] + 0xFF*data[1]
            print "   " + target.getName() + "::" + "size: " + str(target.size)
         else:
            error("Srange info type \'" + symbol.info_type + "\'")
            
   def parseMapFile(self):
      
      my_file = open(self.map_file, "rt")
      
      text_regex = '\s+\.(text|bss)\.(\w+)'
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
               error("Strange address line \'" + line + "\'")
               
            address = address_line_match.group(1)
            
            self.address_mappings[symbol_mangled] = address
            
            parse_next_line = False
            
            continue
         
         text_match = re.match(text_regex, line)
         
         if not text_match:
            continue
         
         symbol_mangled = text_match.group(2)
         #print "Text match: " + symbol_mangled
         parse_next_line = True
         
   def collectSymbolAddressesOfModule(self, module = None):
      
      if module == None:
         for module in self.modules.values():
            self.collectSymbolAddressesOfModule(module)
         return
      
      for member in module.members.values():
         self.collectSymbolAddressesOfMember(member)
         
      for module in module.modules.values():
         self.collectSymbolAddressesOfModule(module)
      
   def collectSymbolAddressesOfMember(self, member):
      
      if member.address_base_symbol in self.address_mappings.keys():
         #print member.getName() + ":"
         #print "   base: " + self.address_mappings[member.address_base_symbol] + " (=" + str(int(self.address_mappings[member.address_base_symbol], 16)) + ")"
         #print "   offset: " + member.address_offset + " (=" + str(int(member.address_offset, 16)) + ")"
         member.address_abs = int(self.address_mappings[member.address_base_symbol], 16) + int(member.address_offset, 16)
         #print "   abs: " + str(member.address_abs)
      else:
         member.address_abs = "unexported"
         #print member.getName() + " address function " + member.address_base_symbol + " unexported"
      
   def listModules(self):
      
      print "Modules:"
      for module in self.modules.values():
         module.write(sys.stdout)
         
if __name__ == "__main__":
   
   SymbolExtractor().run()
