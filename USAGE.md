# `codefreaker`

**Usage**:

```console
$ codefreaker [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `checker, check`: Commands to manage the checker of a problem.
* `clone, c`: Clones by waiting for a set of problems to...
* `config, cfg`: Manage the configuration of the tool.
* `edit, e`: Edit the code of a problem using the...
* `new, n`: Create a new problem from scratch.
* `submit, s`: Submit a problem using the provided language.
* `test, t`: Test a problem using the provided language.
* `testcase, tc`: Commands to manage the testcases of a...

## `codefreaker checker, check`

Commands to manage the checker of a problem.

**Usage**:

```console
$ codefreaker checker, check [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `add, a`: Add a new checker for the problem.
* `edit, e`: Edit the checker for a problem.
* `set, s`: Set a checker for the problem.
* `unset, u`: Use the default checker for a problem.

### `codefreaker checker, check add, a`

Add a new checker for the problem.

**Usage**:

```console
$ codefreaker checker, check add, a [OPTIONS] PROBLEM
```

**Arguments**:

* `PROBLEM`: [required]

**Options**:

* `-t, --template TEXT`: Checker that should be used as template.
* `--help`: Show this message and exit.

### `codefreaker checker, check edit, e`

Edit the checker for a problem.

**Usage**:

```console
$ codefreaker checker, check edit, e [OPTIONS] PROBLEM
```

**Arguments**:

* `PROBLEM`: [required]

**Options**:

* `--help`: Show this message and exit.

### `codefreaker checker, check set, s`

Set a checker for the problem.

**Usage**:

```console
$ codefreaker checker, check set, s [OPTIONS] PROBLEM CHECKER
```

**Arguments**:

* `PROBLEM`: [required]
* `CHECKER`: Path to a testlib checker file.  [required]

**Options**:

* `--help`: Show this message and exit.

### `codefreaker checker, check unset, u`

Use the default checker for a problem.

**Usage**:

```console
$ codefreaker checker, check unset, u [OPTIONS] PROBLEM
```

**Arguments**:

* `PROBLEM`: [required]

**Options**:

* `--help`: Show this message and exit.

## `codefreaker clone, c`

Clones by waiting for a set of problems to be sent through Competitive Companion.

**Usage**:

```console
$ codefreaker clone, c [OPTIONS]
```

**Options**:

* `-l, --language, --lang TEXT`: Language to use.  [default: (dynamic)]
* `--help`: Show this message and exit.

## `codefreaker config, cfg`

Manage the configuration of the tool.

**Usage**:

```console
$ codefreaker config, cfg [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `edit, e`: Open the config in an editor.
* `list, ls`: Pretty print the config file.
* `path`: Show the absolute path of the config file.
* `reset`: Reset the config file to the default one.

### `codefreaker config, cfg edit, e`

Open the config in an editor.

**Usage**:

```console
$ codefreaker config, cfg edit, e [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `codefreaker config, cfg list, ls`

Pretty print the config file.

**Usage**:

```console
$ codefreaker config, cfg list, ls [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `codefreaker config, cfg path`

Show the absolute path of the config file.

**Usage**:

```console
$ codefreaker config, cfg path [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `codefreaker config, cfg reset`

Reset the config file to the default one.

**Usage**:

```console
$ codefreaker config, cfg reset [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `codefreaker edit, e`

Edit the code of a problem using the provided language.

**Usage**:

```console
$ codefreaker edit, e [OPTIONS] PROBLEM
```

**Arguments**:

* `PROBLEM`: [required]

**Options**:

* `-l, --language, --lang TEXT`: Language to use.
* `--help`: Show this message and exit.

## `codefreaker new, n`

Create a new problem from scratch.

**Usage**:

```console
$ codefreaker new, n [OPTIONS] NAME
```

**Arguments**:

* `NAME`: [required]

**Options**:

* `-l, --language, --lang TEXT`: Language to use.  [default: (dynamic)]
* `-t, --timelimit INTEGER`: Time limit in milliseconds.  [default: 1000]
* `-m, --memorylimit INTEGER`: Memory limit in megabytes.  [default: 256]
* `-m, --multitest`: Whether this problem have multiple tests per file.
* `--help`: Show this message and exit.

## `codefreaker submit, s`

Submit a problem using the provided language.

**Usage**:

```console
$ codefreaker submit, s [OPTIONS] PROBLEM
```

**Arguments**:

* `PROBLEM`: [required]

**Options**:

* `-l, --language, --lang TEXT`: Language to use.
* `--keep-sandbox / --no-keep-sandbox`: [default: no-keep-sandbox]
* `--help`: Show this message and exit.

## `codefreaker test, t`

Test a problem using the provided language.

**Usage**:

```console
$ codefreaker test, t [OPTIONS] PROBLEM
```

**Arguments**:

* `PROBLEM`: [required]

**Options**:

* `-l, --language, --lang TEXT`: Language to use.
* `--keep-sandbox / --no-keep-sandbox`: [default: no-keep-sandbox]
* `-i, --index, --idx INTEGER`
* `--help`: Show this message and exit.

## `codefreaker testcase, tc`

Commands to manage the testcases of a problem.

**Usage**:

```console
$ codefreaker testcase, tc [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `add, a`: Add a testcase to a problem.
* `delete, d`: Remove the i-th testcase from a problem.
* `edit, e`: Edit the testcases of a problem.
* `hydrate`: Populate all samples of a problem (or of...

### `codefreaker testcase, tc add, a`

Add a testcase to a problem.

**Usage**:

```console
$ codefreaker testcase, tc add, a [OPTIONS] PROBLEM
```

**Arguments**:

* `PROBLEM`: [required]

**Options**:

* `--help`: Show this message and exit.

### `codefreaker testcase, tc delete, d`

Remove the i-th testcase from a problem.

**Usage**:

```console
$ codefreaker testcase, tc delete, d [OPTIONS] PROBLEM
```

**Arguments**:

* `PROBLEM`: [required]

**Options**:

* `-i, --index, --idx INTEGER`: [required]
* `--help`: Show this message and exit.

### `codefreaker testcase, tc edit, e`

Edit the testcases of a problem.

**Usage**:

```console
$ codefreaker testcase, tc edit, e [OPTIONS] PROBLEM
```

**Arguments**:

* `PROBLEM`: [required]

**Options**:

* `-i, --index, --idx INTEGER`: [required]
* `--help`: Show this message and exit.

### `codefreaker testcase, tc hydrate`

Populate all samples of a problem (or of all problems in the folder).

**Usage**:

```console
$ codefreaker testcase, tc hydrate [OPTIONS]
```

**Options**:

* `-p, --problem TEXT`
* `--help`: Show this message and exit.
