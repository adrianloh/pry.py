#! /usr/bin/env python3

import sys
import os
import re
import inspect
import traceback
import ast
import collections
from pprint import pprint
from functools import wraps


class PryException(Exception): pass


class PryFatalException(Exception): pass


class Mock(object):

	def __init__(self, module_name):
		self.module_name = module_name
		self.debug = True
		self.methods = {}

	def f(self, *args, **kwargs):
		if self.debug:
			pprint(args, indent=2)
		return "_"

	def __setattr__(self, key, value):
		self.__dict__[key] = value

	def __getattr__(self, name):
		if self.debug:
			print("\n{%s} called {%s.%s}" % (inspect.stack()[1][3], self.module_name, name))
		if name in self.__dict__.keys():
			return self.__dict__[name]
		else:
			return self.f


class Test(object):

	def __init__(self):
		self.result = None
		self.messages = []
		self.argv = []

	def __setitem__(self, k, v):
		self.__dict__[k] = v

	def __getitem__(self, k):
		if k in self.__dict__.keys():
			return self.__dict__[k]
		else:
			return None

	@staticmethod
	def pprint(message):
		print('\t ', message)

	def skip(self, message=None):
		if message is not None:
			self.messages.append(message)
		caller = inspect.stack()[1][3]
		raise PryException("-------- [SKIP] %s" % caller)

	def fail(self, message=None):
		if message is not None:
			self.messages.append(message)
		caller = inspect.stack()[1][3]
		raise PryException("++++++++ [FAIL] %s" % caller)

	def fatal(self, message=None):
		if message is not None:
			self.messages.append(message)
		caller = inspect.stack()[1][3]
		raise PryFatalException("++++++++ [FATAL] %s" % caller)

	def log(self, message):
		self.messages.append(str(message))

	def flush(self):
		for msg in self.messages:
			print("\t>>> ", msg)
		self.messages = []


def _top_level_functions(body):
	return (f for f in body if isinstance(f, ast.FunctionDef))


def _parse_ast(filename):
	with open(filename, "rt") as file:
		return ast.parse(file.read(), filename=filename)


def _get_test_functions(filepath):
	tree = _parse_ast(filepath)
	return [func.name for func in _top_level_functions(tree.body) if func.name.startswith("test")]


def module_name_from_path(filepath):
	fn = os.path.split(filepath)[1]
	module_name = re.findall('^(.+)\.py$', fn)[0]
	test_functions = _get_test_functions(filepath)
	return module_name, test_functions


def get_module_names(filepath):
	return [module_name_from_path(f) for f in os.listdir(filepath) if f.endswith("_test.py")]


class PatchError(Exception): pass

def _reassign_(path, target, o):
	name = path[0]
	if len(path) == 1:
		setattr(target, name, o)
		return True
	else:
		if hasattr(target, name):
			next_target = getattr(target, name)
			return _reassign_(path[1:], next_target, o)
		else:
			return False

def patch(path):

	frm = inspect.stack()[1]
	caller_module = inspect.getmodule(frm[0])

	def decorator(func):
		ok = _reassign_(path.split("."), caller_module, func)
		if not ok:
			raise PatchError(path)
		return func

	return decorator

TestFunction = collections.namedtuple("TestFunction", ['name', 'func'])


if __name__ == "__main__":

	modules = []
	test_only = []

	if len(sys.argv) == 1:
		# Without arguments -- Run every test file in os.getcwd()
		sys.path.insert(0, os.path.abspath(os.getcwd()))
		modules = get_module_names(".")
	elif len(sys.argv) == 2:
		# Either:
		#   pry.py /path/to/dir
		#   pry.py /path/to/file_to_test.py
		fp = sys.argv[1]
		if os.path.isdir(fp):
			sys.path.insert(0, os.path.abspath(fp))
			modules = get_module_names(fp)
		if os.path.isfile(fp):
			sys.path.insert(0, os.path.dirname(os.path.abspath(fp)))
			modules.append(module_name_from_path(fp))
	elif len(sys.argv) >= 2:
		# Either:
		#   pry.py /path/to/file1_test.py /path/to/file2_test.py
		#   pry.py /path/to/file_to_test.py test_function1 test_function2
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
		T.argv = sys.argv

		valid_tests_only = []
		invalid_tests = []

		if len(test_only) > 0:
			for fname in test_only:
				if fname not in test_function_names:
					invalid_tests.append(fname)
				else:
					valid_tests_only.append(fname)
			test_function_names = valid_tests_only

		if len(test_function_names) == 0:
			print("[SKIP] <module %s>" % module_name)
			print("\t| No testable functions")
			for fname in invalid_tests:
				print("[SKIP] %s not found" % fname)
			continue

		try:
			m = __import__(module_name)
		except:
			print("[ERROR] <module %s>" % module_name)
			for line in traceback.format_exc().splitlines()[3:]:
				print("\t>>>", line)
			continue

		if "__skiptest__" in dir(m) and m.__skiptest__:
			print("[SKIP] <module %s>" % module_name)
			continue
		else:
			print("[TEST] <module %s>" % module_name)

		test_functions = [TestFunction(fname, getattr(m, fname)) for fname in test_function_names]

		abort = False

		for test_function in test_functions:

			if abort:
				print("======== [SKIP] %s" % test_function.name)
				abort = False
				continue

			try:
				print("======== [START] %s" % test_function.name)
				T.result = test_function.func(T)
				print("-------- [PASS] %s" % test_function.name)
			except PryException as e:
				print(e)
			except PryFatalException as e:
				abort = True
				print(e)
			except:
				# For all other exception, we simply fail the test instead of aborting
				print("++++++++ [FATAL] %s" % test_function.name)
				for line in traceback.format_exc().splitlines()[3:]:
					print("\t>>>", line)
			finally:
				T.flush()