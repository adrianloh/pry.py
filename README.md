# pry.py

A simple Python test runner inspired by stuff I like from Go's testing framework.

To test a folder of test files:

```
$ pry.py /path/to/folder
```

Files suffixed with `_test` eg. `module_test.py` are automatically discovered. Running without passing arguments:

```
$ pry.py
```

Will run test files in current directory.

To test specifically one (or more) files:

```
$ pry.py /path/to/module1_test.py /path/to/module2_test.py
```

Run only specific test(s) in one file:

```
$ pry.py /path/to/module_test.py test_function1 test_function2
```

## Test functions

Top-level functions in test files prefixed with `test_` are automatically discovered. 

```python
def test_function_1(T):
	pass

def test_function_2(T):
	pass
```

Tests run in the order in which they are declared (top to bottom).

Test functions take only one argument, a `Test` object.

They don't have to return anything, or, do anything. 

Running the tests above will produce the output:

```
[PASS] test_function_1
[PASS] test_function_2
```

## The `Test` object

To fail a test:

```python
test_fail_function(T):
	T.fail("optional message to print at end of test")
```

To skip a test:

```python
test_skip_function(T):
	T.skip()
```

More adversely, you can call `T.fatal` which skips all subsequent tests.

You can "carry forward" values via `return` e.g.

```python
def test_producer(T):
	return 1
	
def test_consumer(T):
	if T.result != 1:
		T.fail("Expected 1 got %s" % T.result)
```


To skip a file entirely, declare the top-level variable:

```python
__skiptest__ = True
```











