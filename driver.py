"""
Module: driver.py
Author: John Didion (johndidion@gmail.com)

Base class for batch programs like those created in programming competitions.
The Main class takes care of command line argument parsing, reading input and
passing it to a parse function, passing parsed input to a solver function,
and printing results. It enables parallel job processing (using the 
multiprocessing module), unit testing (using the unittest module) and profiling 
(using the cProfile module).

Example of a minimal implementation::

    from driver import Main

    class ProblemA(Main):
        def __init__(self):
            Main.__init__(self, 'problemA')
            
        def parse_input(self, case_num, input_str):
            # parse input string and return it as structured data
            
        def solve(self, case_num, case):
            # solve the problem for the given input and return ther result
    
    if __name__ == '__main__':
        ProblemA().run()
        
Running the program::

    # Run as an interactive shell. Process each input immediately after
    # it is entered and prints the output.
    $ problemA.py
        
    # Read the input from stdin and write the output to stdout.
    $ problemA.py -

    # Read the input from ~/infile and write the output to ~/outfile
    $ problemA.py ~/infile ~/outfile
    
    # Run unit tests
    $ problemA.py --test
"""

import os
import sys
import unittest

def raw_input_iter():
    """Iterator over lines from stdin."""
    
    while True:
        inp = raw_input()
        if inp:
            yield inp
        else:
            break

def test_case_iter(seq, lines_per_case=1):
    """
    Iterator over a set of test cases. Each case consists of at least one
    `lines_per_case`. Expects the first element of `seq` to be a single integer 
    specifying the number of inputs to expect, or -1 if unlimited inputs should 
    be allowed.
    """

    assert lines_per_case >= 1, "lines_per_case must be >= 1"
    assert hasattr(seq, '__iter__'), "seq must be iterable"
    
    expected = int(seq.next())
    ctr = 0
    
    next = None
    for line in seq:
        cases = (ctr / lines_per_case)
        if line:
            assert expected < 0 or cases < expected, "Too many inputs"
        else:
            assert expected < 0 or cases == expected, "Too few inputs"
            break
        
        line = line.strip()
        ctr += 1
        
        if lines_per_case == 1:
            yield line
        else:
            if next:
                next.append(line)
            else:
                next = [line]
            if ctr % lines_per_case == 0:
                yield next
                next = None

def _pickle_method(method):
    """Custom method for pickling an instance method."""
    
    func_name = method.im_func.__name__
    obj = method.im_self
    cls = method.im_class
    return _unpickle_method, (func_name, obj, cls)

def _unpickle_method(func_name, obj, cls):
    """Custom method for unpickling an instance method."""
    
    for cls in cls.mro():
        try:
            func = cls.__dict__[func_name]
        except KeyError:
            pass
        else:
            break
    return func.__get__(obj, cls)

class TestData(object):
    """Encapsulates data required to build a DriverTestCase."""
    
    __slots__ = ['test_name','num_cases','input_str','output_str','error_class']
    
    def __init__(self, test_name, num_cases, input_str, expected):
        from textwrap import dedent
        self.test_name = test_name
        self.num_cases = num_cases
        self.input_str = dedent(input_str)
        if isinstance(expected, str):
            self.output_str = dedent(output_str)
        else:
            self.error_class = error_class
    
    def iter_cases(self, lines_per_case=1):
        return test_case_iter(iter(self.input_str.splitlines()), lines_per_case)

class DriverTestCase(unittest.TestCase):
    """Test case generated from TestData. 
    
    Checks that there are the expected number of input cases and that the actual 
    results equal the expected results.
    """
    
    def __init__(self, driver, test_data):
        test_func = "test_%s" % test_data.test_name
        setattr(DriverTestCase, test_func, DriverTestCase._run)
        unittest.TestCase.__init__(self, test_func)
        self.driver = driver
        self.test_data = test_data
        self.longMessage = True
    
    def _run(self):
        data = self.test_data
        cases = data.iter_cases(self.driver.lines_per_case)
        
        if data.error_class:
            try:
                self.driver.execute_all(enumerate(cases, 1))
                raise AssertionError("Expected execution failure")
            except data.error_class:
                return
        else:
            results = self.driver.execute_all(enumerate(cases, 1))
            self.assertEqual(len(results), data.num_cases, "Incorrect number of results")
            
            from cStringIO import StringIO
            output = StringIO()
            try:
                for i, r in enumerate(results, 1):
                    self.driver.print_result(i, r, output)
                self.assertEqual(output.getvalue(), data.output_str, "Incorrect output")
            finally:
                output.close()

class Main(object):
    def __init__(self, name, lines_per_case=1):
        self.name = name
        self.lines_per_case = lines_per_case
        
    def run(self, args=None):
        ns = self.parse_arguments(args)
        
        if ns.test:
            self.run_tests(ns.test)
            return
        
        if ns.infile is None:
            input_iter = raw_input_iter()
        else:
            import fileinput
            input_iter = fileinput.input(ns.infile, mode='rU')
        cases = test_case_iter(input_iter, self.lines_per_case)
        
        if ns.profile:
            import cProfile
            profile_file = None if ns.profile == 'stdout' else ns.profile
            cProfile.run('self.execute_serially(enumerate(cases, 1))', profile_file)
        else:
            if ns.threads > 1:
                self.threads = ns.threads
                executor = self.execute_threaded
            else:
                executor = self.execute_serially
            results = executor(enumerate(cases, 1))
            outfile = sys.stdout if ns.outfile is None else open(ns.outfile, 'w')
            with outfile:
                for i, r in enumerate(results, 1):
                    self.print_result(i, r, outfile)
    
    def execute_serially(self, jobs):
        return [self.execute(job) for job in jobs]
    
    def execute_threaded(self, jobs):
        import copy_reg
        import multiprocessing
        import types
        
        # register custom un/pickler for instance methods
        copy_reg.pickle(types.MethodType, _pickle_method, _unpickle_method)
            
        threads = min(self.threads, multiprocessing.cpu_count())
        pool = multiprocessing.Pool(threads)
        try:
            return pool.map(self.execute, jobs)
        finally:
            pool.close()
            pool.join()
        
    def execute(self, job):
        case_num, input_str = job
        return self.solve(case_num, self.parse_input(case_num, input_str))
        
    def parse_arguments(self, args):
        from argparse import ArgumentParser
        parser = ArgumentParser()
        mutex_group = parser.add_mutually_exclusive_group()
        mutex_group.add_argument("--test", nargs="?", metavar="VERBOSITY", 
            default=False, const=1, help="Run test cases. Use verbosity of 1 "\
                "unless VERBOSITY is specified.")
        mutex_group.add_argument("--profile", metavar="FILE", default=False,
            help="Run program with profiling enabled. Profiling output is "\
                "written to FILE unless stdout is specified.")
        mutex_group.add_argument("--threads", type=int, metavar="N", default=1,
            help="The number of parallel threads to use.")
        parser.add_argument("infile", metavar="INFILE", nargs="?", default=None, 
            help="The input file, or '-' to read from stdin.")
        parser.add_argument("outfile", metavar="OUTFILE", nargs="?", default=None,
            help="The output file. Omit to write to stdout.")
        ns = parser.parse_args(args)
        if not ns.test and ns.infile is None:
            # TODO: it should be possible to handle these mutex cases with argparse
            assert ns.threads == 1, "Multithreading not allowed with interactive input"
            assert ns.profile is False, "Profiling not allowed with interactive input"
        return ns
    
    def parse_input(self, case_num, input_str):
        return input_str
        
    def solve(self, case_num, case):
        raise Exception("not implemented")
        
    def print_result(self, case_num, result, outfile):
        outfile.write("Case #%i: %s\n" % (case_num, str(result)))

    def run_tests(self, verbosity=1):
        if hasattr(self, 'get_test_data'):
            suite = unittest.TestSuite()
            for case in self.get_test_data():
                suite.addTest(DriverTestCase(self, case))
            unittest.TextTestRunner(verbosity=verbosity).run(suite)
        else:
            if hasattr(self, 'get_test_module'):
                testmod = self.get_test_module()
            else:
                modfile = sys.modules[self.__module__].__file__
                testmod = os.path.splitext(os.path.basename(modfile))[0]
            unittest.main(testmod, verbosity=verbosity)