Many programming competitions (e.g. Google Code Jam) use a common format for
problem input and output. The driver.Main class is an attempt to implement all
the common work involved in implementing solutions to these problems and add
some nice features on top - multithreading support, profiling and unit testing.
Here's an example of a minimal implementation:

```python
#!/usr/bin/env python
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
```
    
If you want to have unit tests but don't want to mess with the unittest module,
you can simply provide the test data and test cases will be built for you.
Test data is supplied as a list of driver.TestData objects. Each TestData
has four bits of information: the test name, number of cases, input data and
expected output. Input and output data are automatically de-dented, so you can
format them for readability:

```python
from driver import Main, TestData

class CandySplit(Main):
    """Implementation of GCJ2011 qualifying problem C: Candy Split."""

    ...

    def get_test_data(self):
        return [
            driver.TestData('given', 2, 
                """\
                2
                5
                1 2 3 4 5
                3
                3 5 6
                """,
                """\
                Case #1: NO
                Case #2: 11
                """),
            driver.TestData('edge_case', 1,
                """\
                1
                1
                1
                """,
                """\
                Case #1: NO
                """)
            ]
```

Running the program:

```sh
# Run as an interactive shell. Process each input immediately after
# it is entered and prints the output.
$ problemA.py

# Read the input from stdin and write the output to stdout.
$ problemA.py -

# Read the input from ~/infile and write the output to ~/outfile
$ problemA.py ~/infile ~/outfile

# Run unit tests
$ problemA.py --test
```
