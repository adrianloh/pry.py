def test_skip(T):
	T.skip()
	print("test_skip, you should not see this line")

def test_pass(T):
	return

def test_fail(T):
	T.fail()

def test_result_1(T):
	T.log("Returning 0 to next test")
	return 0

def test_result_2(T):
	T.log("Got %s from last test" % str(T.result))

def test_setitem_dict(T):
	T["message"] = "Hello World"

def test_getitem_dict(T):
	if T['message'] is None:
		T.fail()

def test_exception_in_func(T):
	T.log("This test will raise an exception")
	a = {}
	b = a['a']

def test_fatal(T):
	T.fatal("This test is fatal")

def test_this_will_not_run_because_of_previous_exception(T):
	return