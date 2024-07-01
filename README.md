<p align="center">
   <img src="robox_transparent.png" width="240px">
</p>
<p align="center">
    <em>The go-to CLI tool for competitive programmers and setters.</em>
</p>
<p align="center">
	<!-- loscal repository, no metadata badges. -->
<p>
<p align="center">
	<img src="https://img.shields.io/badge/Poetry-60A5FA.svg?style=default&logo=Poetry&logoColor=white" alt="Poetry">
	<img src="https://img.shields.io/badge/Python-3776AB.svg?style=default&logo=Python&logoColor=white" alt="Python">
	<img src="https://img.shields.io/badge/FastAPI-009688.svg?style=default&logo=FastAPI&logoColor=white" alt="FastAPI">
	<img src="https://img.shields.io/badge/JSON-000000.svg?style=default&logo=JSON&logoColor=white" alt="JSON">
</p>

<br><!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary><br>

- [ Overview](#-overview)
- [ Features](#-features)
- [ Modules](#-modules)
- [ Getting Started](#-getting-started)
  - [ Installation](#-installation)
  - [ Usage](#-usage)
- [ Project Roadmap](#-project-roadmap)
- [ Contributing](#-contributing)
- [ License](#-license)
</details>
<hr>

##  Overview

[![Usage video]](https://github.com/rsalesc/robox.io/assets/4999965/111de01e-6cbd-495e-b8c2-4293921e49b3)

[![GitHub license](https://img.shields.io/github/license/rsalesc/robox.io.svg)](https://github.com/rsalesc/robox.io/blob/master/LICENSE)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/robox.svg)](https://pypi.python.org/pypi/robox.io/)
[![PyPI version shields.io](https://img.shields.io/pypi/v/robox.svg)](https://pypi.python.org/pypi/robox.io/)

robox is a CLI tool and library that aims to help contestants and setters from the competitive programming community to have an easier time.

Although trying to solve the issues of these two audiences seems to be too much for a single tool to handle, we exploit the fact that the journeys of contestants and setters have a lot in common.

---

##  Features

#### For contestants

- 🤖 **Parsing**: provides an entrypoint for contests and problems to be parsed through Competitive Companion.
- 🔨 **Testing**: provides commands for automatically running your problems against both downloaded and manually added testcases, and shows a clear report.
- 📤 **Submit**: provides the option of submiting your solution for a few supported online judges from the command line.
- 🧱 **Structure**: provides an opinionated structure for the file tree of both parsed and manually created problems.
- ⚙️ **Flexibility**: still gives enough flexibility for you to extend your problem. Add testcases, set a custom checker, write a generator.

#### For setters

🔜 Still coming up!

---

##  Getting Started

**System Requirements:** the tool was developed for Unix systems and was tested only in Ubuntu.

If you want to use the parsing feature, you also have to install [Competitive Companion](https://github.com/jmerle/competitive-companion).

###  Installation

#### From `pipx`

> Use `pipx` for better isolation between apps!
> ```console
> $ pipx install robox.io
> $ pipx install exinc
> ```

#### From `pip`

> [![PyPi](https://badgen.net/badge/icon/pypi?icon=pypi&label)](https://https://pypi.org/)
> ```console
> $ pip install robox.io exinc
> ```


#### From code

> Go to the cloned folder and run:
> ```console
> $ pip install .
> ```

#### In Poetry venv (while developing)

> Run the following when in the Poetry venv.
> ```console
> $ poetry install
> ```


###  Usage

#### 0. Be familiar with Competitive Companion

Make sure you're familiarized with [Competitive Companion](https://github.com/jmerle/competitive-companion)
-- a helper that facilitates parsing tasks directly from your browser.

#### 1. Clone a contest or a single problem

```console
$ # Or simply `rbc c`
$ rbc clone
```

After running the command above, hit the ➕ (plus) icon in Competitive Companion,
and you should start seeing parsing logs in the command line.

![clone](https://github.com/rsalesc/robox.io/assets/4999965/edb4611e-e459-49ba-940f-c362f27dc76e)

#### 2. Implement a solution and run testcases

```console
$ # Or simply `rbc test A`
$ rbc test A
```
![test_wa](https://github.com/rsalesc/robox.io/assets/4999965/309090e3-179b-4bd7-8961-a54fd109ac16)
![test](https://github.com/rsalesc/robox.io/assets/4999965/49681373-1663-46a1-a63a-06ed1176e82d)

#### 3. Submit your solution

```console
$ # Or simply `rbc s A`
$ rbc submit A
```
![submit](https://github.com/rsalesc/robox.io/assets/4999965/153eb278-384b-401b-94a1-0b1df23ce4ad)

###  Tests

TODO

---

##  Project Roadmap

TODO

---

##  Contributing

Contributions are welcome! Here are several ways you can contribute:

- **[Report Issues](https://local//issues)**: Submit bugs found or log feature requests for the `.` project.
- **[Submit Pull Requests](https://local//blob/main/CONTRIBUTING.md)**: Review open PRs, and submit your own PRs.
- **[Join the Discussions](https://local//discussions)**: Share your insights, provide feedback, or ask questions.

<details closed>
<summary>Contributing Guidelines</summary>

1. **Fork the Repository**: Start by forking the project repository to your local account.
2. **Clone Locally**: Clone the forked repository to your local machine using a git client.
   ```sh
   git clone ../.
   ```
3. **Create a New Branch**: Always work on a new branch, giving it a descriptive name.
   ```sh
   git checkout -b new-feature-x
   ```
4. **Make Your Changes**: Develop and test your changes locally.
5. **Commit Your Changes**: Commit with a clear message describing your updates.
   ```sh
   git commit -m 'Implemented new feature x.'
   ```
6. **Push to local**: Push the changes to your forked repository.
   ```sh
   git push origin new-feature-x
   ```
7. **Submit a Pull Request**: Create a PR against the original project repository. Clearly describe the changes and their motivations.
8. **Review**: Once your PR is reviewed and approved, it will be merged into the main branch. Congratulations on your contribution!
</details>

<details closed>
<summary>Contributor Graph</summary>
<br>
<p align="center">
   <a href="https://local{//}graphs/contributors">
      <img src="https://contrib.rocks/image?repo=">
   </a>
</p>
</details>

---

##  License

This project is protected under the [Apache License 2.0](http://www.apache.org/licenses/) License. For more details, refer to the [LICENSE](LICENSE) file.

---

[**Return**](#-overview)

---
