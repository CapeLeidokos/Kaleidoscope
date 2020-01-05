#!/usr/bin/env python3
  
# -*- coding: utf-8 -*-

# -*- mode: python -*-

# Author: noseglasses (shinynoseglasses@gmail.com)

import os
import logging
import string
import subprocess

def is_exe(fpath):
   return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

class Communicator(object):
   
   def __init__(self):
      
      self.parseCommandLineArgs()
      self.findExecutables()
      self.readYamlFile()
      
      self.processCommand()
      
   def parseCommandLineArgs(self):
      
      import argparse

      parser = argparse.ArgumentParser(description='Serial communication with Kaleidoscope driven devices.')
            
      parser.add_argument('--kaleidoscope_repo_dir', \
                           help = 'The path to the Kaleidoscope repository directory')
      parser.add_argument('--yaml_model_file', \
                           help = 'The filename of a yaml input file containing module information',
                           default = '')
      
      parser.add_argument('remaining_args', nargs=argparse.REMAINDER)
      
      args = parser.parse_args()
      
      self.kaleidoscope_repo_dir = args.kaleidoscope_repo_dir
      self.yaml_model_file = args.yaml_model_file
      self.remaining_args = args.remaining_args
      
   def findExecutables(self):
      
      self.focus_test_executable = self.kaleidoscope_repo_dir + '/bin/focus-test'
      
      if not is_exe(self.focus_test_executable):
         raise RuntimeError('Unable to find focus-test executable \'' + self.focus_test_executable + '\'')
   
   def readYamlFile(self):
      import yaml

      with open(self.yaml_model_file) as f:
    
         self.module_tree = yaml.safe_load(f)
         #print(data)
         
   def getModule(self, module_path_tokens):
      
      if not "modules" in self.module_tree.keys():
         raise RuntimeError('No modules defined in yaml file')
         
      modules = self.module_tree["modules"]
      result_module = None
      
      for path_token in module_path_tokens:
      
         while(modules != None):
            for module in modules:
               if module["name"] == path_token:
                  result_module = module
                  if "modules" in module.keys():
                     modules = module["modules"]
                  else:
                     modules = None
                  break
            break
               
         if result_module == None:
            raise RuntimeError('Unable to resolve module path \'' + "::".join(module_path_tokens))
                  
      return result_module
         
   def findProcedure(self, proc_name):
      
      proc_name_tokens = proc_name.split("::")
      
      if len(proc_name_tokens) < 2:
         raise RuntimeError('Strange procedure name \'' + proc_name + '\'')
         
      module = self.getModule(proc_name_tokens[:-1])

      proc_name = proc_name_tokens[-1]
      
      if not "procedures" in module.keys():
         raise RuntimeError('No procedures defined in module ' + "::".join(proc_name_tokens[:-1]))
      else:
         procs = module["procedures"]
         the_proc = None
         for proc in procs:
            if proc["name"] == proc_name:
               the_proc = proc
               break
            
         if the_proc == None:
            raise RuntimeError('Unable to find procedure \'' + proc_name + '\' in module \'' + "".join(proc_name_tokens[:-1], "::"))
         else:
            return the_proc
         
   def findInput(self, input_name):
      
      input_name_tokens = input_name.split("::")
      
      if len(input_name_tokens) < 2:
         raise RuntimeError('Strange input name \'' + input_name + '\'')
         
      module = self.getModule(input_name_tokens[:-1])

      input_name = input_name_tokens[-1]
      
      if not "inputs" in module.keys():
         raise RuntimeError('No inputs defined in module' + "::".join(input_name_tokens[:-1]))
      else:
         inputs = module["inputs"]
         the_input = None
         for an_input in inputs:
            if an_input["name"] == input_name:
               the_input = an_input
               break
            
         if the_input == None:
            raise RuntimeError('Unable to find input \'' + input_name + '\' in module \'' + "".join(proc_name_tokens[:-1], "::"))
         else:
            return the_input
      
   def pokeValue(self, address, size_bytes, value_str):
      
      import ctypes
      
      if size_bytes == 1:
         transfer_value = ctypes.c_uint8(int(value_str))
      elif size_bytes == 2:
         transfer_value = ctypes.c_uint16(int(value_str))
      else:
         raise RuntimeError('Procedure argument size ' + str(size_bytes) + \
            ' currently unsupported')
      
      cmd = [self.focus_test_executable, "poke", str(address), \
                                         str(size_bytes), str(transfer_value)]
      proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

      o, e = proc.communicate()
      
      return transfer_value
   
   def peekValue(self, address, size_bytes):
      
      import ctypes
      
      cmd = [self.focus_test_executable, "peek", str(address), \
                                         str(size_bytes)]
      proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

      o, e = proc.communicate()
      
      return o.decode('utf8').rstrip()
   
   def assertValueRange(self, type, value, lower, upper):
      if (value < lower) or (value > upper):
         raise RuntimeError('Value ' + str(value) + ' exceeds data range [' \
            + str(lower) + ';' + str(upper) + '] of type ' + type)
      
   def verifyValue(self, name, type, value_str):
      
      import ctypes
      
      if type == "uint8_t":
         self.assertValueRange(type, int(value_str), 0, 255)
         ctypes.c_uint8(int(value_str))
      elif type == "uint16_t":
         self.assertValueRange(type, int(value_str), 0, 65535)
         ctypes.c_uint16(int(value_str))
      elif type == "uint32_t":
         self.assertValueRange(type, int(value_str), 0, 4294967295)
         ctypes.c_uint32(int(value_str))
      elif type == "int8_t":
         self.assertValueRange(type, int(value_str), -128, 127)
         ctypes.c_int8(int(value_str))
      elif type == "int16_t":
         self.assertValueRange(type, int(value_str), -32768, 32767)
         ctypes.c_int16(int(value_str))
      elif type == "int32_t":
         self.assertValueRange(type, int(value_str), -2147483648, 2147483647)
         ctypes.c_int32(int(value_str))
      elif type == "float":
         self.assertValueRange(type, float(value_str), 1.2E-38, 3.4E+38)
         ctypes.c_float(float(value_str))
         
   def assignValue(self, arg_dict, value_str):
      
      self.verifyValue(arg_dict["name"], arg_dict["data"]["type"], value_str)
      
      print('   {0} = {1} [address = {2}, size = {3}]'.format(\
         arg_dict["name"], \
         value_str, \
         str(arg_dict["data"]["address"]), \
         str(arg_dict["data"]["size"])))
      
      transfer_value = self.pokeValue(arg_dict["data"]["address"], arg_dict["data"]["size"], value_str)
      
   def retreiveValue(self, arg_dict):
      return self.peekValue(arg_dict["data"]["address"], arg_dict["data"]["size"])
   
   def assignProcArgs(self, proc_name, args, args_pairs):
      
      arg_names_accepted = set()
      args_accepted = {}
      for arg in args:
         arg_names_accepted.add(arg['name'])
         args_accepted[arg['name']] = arg
         
      arg_names_supplied = set()
      
      args_supplied = {}
      
      for args_pair in args_pairs:
         
         tokens = args_pair.split("=")
         
         if len(tokens) != 2:
            raise RuntimeError('Strange procedure args pair \'' + args_pair + '\'')
         else:
            arg_names_supplied.add(tokens[0])
            args_supplied[tokens[0]] = tokens[1]
            
      common_arg_names = arg_names_accepted.intersection(arg_names_supplied)
      
      if len(common_arg_names) != len(arg_names_accepted):
         
         arg_names_unsupplied = arg_names_accepted.difference(arg_names_supplied)
         
         raise RuntimeError('The following arguments of procedure ' + proc_name + \
            ' are unsupplied: ' + str(arg_names_unsupplied))
            
      superfluous_arg_names = arg_names_supplied.difference(arg_names_accepted)
      
      if len(superfluous_arg_names) != 0:
         
         raise RuntimeError('The following unaccepted arguments have been supplied '
            + 'to a call of procedure ' + proc_name + ': ' + str(superfluous_arg_names))
      
      #print("Args accepted: " + str(arg_names_accepted))
      #print("Args supplied: " + str(arg_names_supplied))
      
      for (name, value) in args_supplied.items():
         self.assignValue(args_accepted[name], value)
         
   def invokeCallable(self, address):
            
      cmd = [self.focus_test_executable, "call", str(address)]
      proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

      o, e = proc.communicate()
         
   def callProcedure(self, name, args_pairs):
      proc = self.findProcedure(name)
      
      self.assignProcArgs(name, proc['arguments'], args_pairs)
      
      self.invokeCallable(proc['callable']['address'])
      
   def setInput(self, input_name, value_str):
      
      the_input = self.findInput(input_name)
      
      self.assignValue(the_input, value_str)
      self.invokeCallable(the_input['callable']['address'])
      
   def getInput(self, input_name):
         
      the_input = self.findInput(input_name)
      value = self.retreiveValue(the_input)
      
      print("Value of input \'" + input_name + "\': " + value)
      
   def processCommand(self):
      
      if len(self.remaining_args) == 0:
         raise RuntimeError('No commands provided')
         
      # Make sure the firmware that is running on the device is the same
      # that was used to generate the module information.
      #
      # TODO: This is currently not supported as there is no build step
      #       available that would allow us to save the checksum in 
      #       the firmware.
      #
      #self.validateChecksum()
         
      if self.remaining_args[0] == "call":
         if len(self.remaining_args) < 2:
            raise RuntimeError('Subcommand \'call\' requires a procedure name')
         else:
            proc_name = self.remaining_args[1]
            
            print("Calling procedure " + proc_name)
            print("Args: " + str(self.remaining_args[2:]))
            
            self.callProcedure(proc_name, self.remaining_args[2:])
      elif self.remaining_args[0] == "set_input":
         if len(self.remaining_args) < 2:
            raise RuntimeError('Subcommand \'set_input\' requires an input name as second argument')
         else:
            input_name = self.remaining_args[1]
            print("Setting input " + input_name)
            
            if len(self.remaining_args) < 3:
               raise RuntimeError('Subcommand \'set_input\' requires a value as third argument')
            
            self.setInput(input_name, self.remaining_args[2])
      elif self.remaining_args[0] == "get_input":
         if len(self.remaining_args) < 2:
            raise RuntimeError('Subcommand \'get_input\' requires an input name as second argument')
         else:
            input_name = self.remaining_args[1]
            self.getInput(input_name)
            
   def validateChecksum(self):
      
      checksum_tokens_expected = self.module_tree['checksum'].split(' ')
      checksum_bytes_expected = map(int, checksum_tokens_expected)
      
      cmd = [self.focus_test_executable, "call", str(address)]
      proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

      o, e = proc.communicate()
      
      checksum_tokens_recieved = o.decode('utf8').rstrip().split(" ")
      checksum_bytes_received = map(int, checksum_tokens_recieved)
         
if __name__ == "__main__":
   Communicator()
