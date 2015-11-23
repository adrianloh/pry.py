#! /usr/bin/env python

import sys
import os
import re
import inspect
import traceback
import ast


class PryException(Exception):
	pass


class PryFatalException(Exception):
	pass


class Test(object):

	def __init__(self):
		self.result = None
		self.messages = []

	def __setitem__(self, k, v):
		self.__dict__[k] = v

	def __getitem__(self, k):
		if k in self.__dict__.keys():
			return self.__dict__[k]
		else:
			return None

	def skip(self, message=None):
		if message is not None:
			self.messages.append(message)
		raise PryException("[SKIP] %s" % inspect.stack()[1][3])

	def fail(self, message=None):
		if message is not None:
			self.messages.append(message)
		raise PryException("[FAIL] %s" % inspect.stack()[1][3])

	def fatal(self, message=None):
		if message is not None:
			self.messages.append(message)
		raise PryFatalException("[FATAL] %s" % inspect.stack()[1][3])

	def log(self, message):
		self.messages.append(str(message))

	def flush(self):
		for msg in self.messages:
			print "\t| ", msg
		self.messages = []


def top_level_functions(body):
	return (f for f in body if isinstance(f, ast.FunctionDef))


def parse_ast(filename):
	with open(filename, "rt") as file:
		return ast.parse(file.read(), filename=filename)


def get_test_functions(filepath):
	tree = parse_ast(filepath)
	return [func.name for func in top_level_functions(tree.body)
			if func.name.startswith("test")]


def module_name_from_path(filepath):
	fn = os.path.split(filepath)[1]
	module_name = re.findall('^(.+)\.py$', fn)[0]
	test_functions = get_test_functions(filepath)
	return (module_name, test_functions)


def get_module_names(filepath):
	return [module_name_from_path(f) for f in os.listdir(filepath)
	        if f.endswith("_test.py")]


if __name__ == "__main__":

	test_only = []
	modules = []

	if len(sys.argv) == 1:
		sys.path.insert(0, os.path.abspath(os.getcwd()))
		modules = get_module_names(".")
	elif len(sys.argv) == 2:
		fp = sys.argv[1]
		if os.path.isdir(fp):
			sys.path.insert(0, os.path.abspath(fp))
			modules = get_module_names(fp)
		if os.path.isfile(fp):
			sys.path.insert(0, os.path.dirname(os.path.abspath(fp)))
			modules.append(module_name_from_path(fp))
	elif len(sys.argv) >= 2:
		# Assume the first one is a file
		sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[1])))
		for arg in sys.argv[1:]:
			if arg.startswith("test"):
				test_only.append(arg)
			else:
				if not os.path.isfile(arg):
					print("File not found: %s" % arg)
				else:
					modules.append(module_name_from_path(arg))

	if len(modules) == 0:
		print("No modules to test")
		exit(0)

	for (module_name, test_function_names) in modules:

		T = Test()

		if len(test_function_names) == 0:
			print("[SKIP] <module %s>" % module_name)
			print("\t| No testable functions" % module_name)
			continue

		try:
			m = __import__(module_name)
		except:
			print("[ERROR] <module %s>" % module_name)
			for line in traceback.format_exc().splitlines()[3:]:
				print "\t>>>", line
			continue

		if "__skiptest__" in dir(m) and getattr(m, "__skiptest__"):
			print("[SKIP] <module %s>" % module_name)
			continue
		else:
			print("[TEST] <module %s>" % module_name)

		test_functions = [(fname, getattr(m, fname)) for fname in test_function_names]

		skipAll = False

		for (func_name, func) in test_functions:

			if skipAll:
				print("[SKIP] %s" % func_name)
				continue

			if len(test_only)>0 and (func_name not in test_only):
				continue

			try:
				T.result = func(T)
				print("[PASS] %s" % func_name)
			except PryException as e:
				print(e)
			except PryFatalException as e:
				skipAll = True
				print(e)
			except:
				print("[FAIL] %s" % func_name)
				for line in traceback.format_exc().splitlines()[3:]:
					print "\t>>>", line
			finally:
				T.flush()
