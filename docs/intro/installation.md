# Installation

You can install {{robox}} with a single command, either using `pip` or `pipx`. Prefer using `pipx` to have a better isolation between the dependencies. Read more about `pipx` [here](https://pipx.pypa.io/stable/installation/).

## Requirements

- Python 3.9 or above (stable with Python 3.10).
- A C++ toolchain to compile {{testlib}} libraries (usually `g++`).
- Optional:
    - Compilers/interpreters that you need to run your solutions on (e.g. `g++`, `java`).
    - [Competitive Companion](https://github.com/jmerle/competitive-companion) for contestants
    - pdfLaTeX and other additional packages to convert TeX files into PDF

## From PyPI

```bash
$ pipx install robox.io
```

## From the repository

```bash
$ git clone https://github.com/rsalesc/robox.io
$ cd robox.io
$ pipx install .
```

## Verify installation

<!-- termynal -->
```bash
$ rbx --help
# Robox help string should show up here
```

---

Proceed to the [Configuration](configuration.md) section.