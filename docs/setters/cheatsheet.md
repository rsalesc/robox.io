# Cheatsheet

## CLI

| Task                                            | Command                                |
| ----------------------------------------------- | -------------------------------------- |
| Show help message                               | `rbx --help`                           |
| Create a new package in folder `package`        | `rbx create package`                   |
| Open the problem configuration in a text editor | `rbx edit`                             |
| Generate all testcases                          | `rbx build`                            |
| Generate all testcases and run validators       | `rbx verify`                           |
| Run all solutions and check their tags          | `rbx run`                              |
| Run all solutions except the slow ones          | `rbx run -v2`                          |
| Run a stress test with name `break`             | `rbx stress break`                     |
| Download {{testlib}} to the current folder      | `rbx download testlib`                 |
| Download {{jngen}} to the current folder        | `rbx download jngen`                   |
| Download a built-in {{testlib}} checker         | `rbx download checker wcmp.cpp`        |
| Build PDF statements                            | `rbx statements build --output=pdf`    |
| Build PDF statements for English                | `rbx statements build en --output=pdf` |
| Package problem for {{polygon}}                 | `rbx package polygon`                  |
| Package problem for {{boca}}                    | `rbx package boca`                     |
| Clear cache                                     | `rbx clear`                            |

## `problem.rbx.yml`

### Change problem constraints

```yaml
timeLimit: 1000  # In milliseconds
memoryLimit: 256  # In megabytes
```

### Add testlib assets

#### Set a built-in {{testlib}} checker

```bash
$ rbx download checker yesno.cpp
```

```yaml
checker:
  path: "yesno.cpp"
```

!!! tip
    Find [here](https://github.com/MikeMirzayanov/testlib/tree/master/checkers) a full list of existing built-in {{testlib}} checkers.

#### Set a custom checker

```yaml
checker:
  path: "my-checker.cpp"
```


#### Add a generator

Add a new generator entry to the `generators` field.

```yaml
generators:
  # ...other generators
  - name: "my-gen"
    path: "my-gen.cpp"
```

!!! tip 
    To actually generate tests with this new generator, you have to add testcase groups
    and call the generator.

#### Set a validator

```yaml
validator:
  path: 'my-validator.cpp`
```

### Add a new solution

Implement your solution (for instance, a wrong solution in `sols/my-wa-solution.cpp`) and add it to the `solutions` field.

```yaml
solutions:
  - path: 'sols/my-wa-solution.cpp'
    outcome: WRONG_ANSWER
```

You can see the list of possible expected outcomes [here][robox.box.schema.ExpectedOutcome].

### Add testcases

#### Add a testcase group with manually defined tests

```yaml
testcases:
  # ...other testcase groups
  - name: "manual-tests"
    testcaseGlob: "tests/manual/*.in" # (1)!
```

  1.   Import all tests in the `tests/manual/` folder in lexicographic order.
       
       The test input files must end in `.in`.

#### Add a testcase group with a list of generated tests

```yaml
testcases:
  # ...other testcase groups
  - name: "single-generated"
    generators:
      - name: "gen"
        args: "1000 123" # (1)!
      - name: "gen"
        args: "1000 456" # (2)!
```

  1.   A generated test obtained from the output of the command `gen 1000 123`.
  2.   A generated test obtained from the output of the command `gen 1000 456`.
  
#### Add a testcase group with a list of generated tests from a generator script

=== "problem.rbx.yml"
    ```yaml
    testcases:
      # ...other testcase groups
       - name: "generated-from-text-script"
         generatorScript:
            path: "script.txt"
    ```

=== "script.txt"
    ```bash
    gen 1000 123
    gen 1000 456
    gen 1000 789
    # other tests...
    ```

#### Add a testcase group with a list of generated tests from a dynamic generator script

=== "problem.rbx.yml"
    ```yaml
    testcases:
      # ...other testcase groups
       - name: "generated-from-program-script"
         generatorScript:
            path: "script.py"
    ```

=== "script.py"
    ```python
    for i in range(50):
      print(f'gen 1000 {i}') # (1)!
    ```

    1.   Generates 50 random tests.

#### Add testgroup-specific validator

```yaml
validator:
  path: "my-validator.cpp"
testcases:
  - name: "small-group"
    # Define tests...
    validator:
      path: "my-small-validator.cpp" # (1)!
  - name: "large-group"
    # Define tests...
```

1.   Add a specific validator to verify constraints of a smaller sub-task of the problem.

### Add variables

The variables below can be reused across validators and statements.

```yaml
vars:
  "MAX_N": 1000
  "MAX_V": 100000
```

#### Use variables
=== "In validators"
    ```cpp
    int32_t main() {
      registerValidation(argc, argv);
      prepareOpts(argc, argv);

      int MAX_N = opt<int>("MAX_N"); // Read from package vars.

      // Rest of the validator
    }
    ```

=== "In statements"
    ```tex
    The maximum value of N is \VAR{MAX_N | sci} % (1)!
    ```

    1.   If `MAX_N` has lots of trailing zeroes, `sci` converts it to scientific notation.

### Add statements

#### Add a {{roboxTeX}} statement

```yaml
statements:
  # ...other statements
  - title: "My problem"
    path: "statement/statement.rbx.tex"
    type: roboxTeX
    language: 'en'
    pipeline:
      - type: 'rbx-tex'
        template: statement/template.rbx.tex' # (1)!
    assets: ['statement/olymp.sty', 'statement/*.png'] # (2)!
```

1.   Defines how a {{roboxTeX}} file will be converted to a normal TeX file. Here, we link
     the template where our {{roboxTeX}} sections such as *legend*, *input* and *output*
     will be inserted into.

2.   Defines assets that should be linked when the resulting statement is being compiled.

#### Add a PDF statement

```yaml
statements:
  # ...other statements
  - title: "My problem"
    path: "statement/statement.pdf"
    type: PDF
    language: 'en'
```

### Add a stress test

#### Add a stress to look for an error in a solution

```yaml
stresses:
  - name: "my-stress"
    generator:
      name: 'gen'
      args: '[1..<MAX_N>] @' # (1)!
    solutions:
      - path: "sols/my-potentially-wrong-sol.cpp"
```

1.  The `<MAX_N>` variable expands into the `vars.MAX_N` value that could be declared in
    `problem.rbx.yml`.

    The `[1..<MAX_N>]` picks a random number in this interval before generating every test in the stress run.

    The `@` appends a few extra random characters to the end of the generator call to re-seed the generator.

#### Add a stress to look for a test that causes TLE in a solution

```yaml
stresses:
  - name: "my-stress"
    generator:
      name: 'gen'
      args: '1000000 @' # (1)!
    solutions:
      - path: "sols/my-potentially-slow-sol.cpp"
    outcome: TLE
```

1.  The `@` at the end of the `args` string appends a random string to it. This is necessary here because `gen 100000` would return the same testcase over and over, since {{testlib}} rng is seeded from its command line argc and argv.