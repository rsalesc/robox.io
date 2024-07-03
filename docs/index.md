# Getting started

<figure markdown="span">
  ![Image title](robox_transparent.png){ width="300" }
  <figcaption>The go-to CLI tool for competitive programmers and setters.</figcaption>
</figure>

---

{{robox}} is a CLI tool and library that aims to help setters and contestants from the competitive programming community to have an easier time.

Although trying to solve the issues of these two audiences seems to be too much for a single tool to handle, we exploit the fact that the journeys of setters and contestants have a lot in common.

That's why {{robox}} packages two CLI solutions: `rbx` (short for {{robox}} for setters) and `rbc` (short for {{robox}} for contestants).

## Features

**For setters** `rbx`

- 🤖 Generation: provides hooks for calling generators and generating testcases automatically.
- 🔨 Testing: provides commands for automatically running correct and incorrect solutions against the testcases of your problem, automatically judging whether the verdict was as expected or not.
- ✅ Verify: checks if your testcases and solutions are strictly conformant.
- 📝 Statements: provides tooling for writing and building statements.
- 📤 Package: provides a single command for packaging your problems for use in judge systems.

**For contestants** `rbc`

- 🤖 Parsing: provides an entrypoint for contests and problems to be parsed through Competitive Companion.
- 🔨 Testing: provides commands for automatically running your problems against both downloaded and manually added testcases, and shows a clear report.
- 📤 Submit: provides the option of submiting your solution for a few supported online judges from the command line.
- 🧱 Structure: provides an opinionated structure for the file tree of both parsed and manually created problems.
- ⚙️ Flexibility: still gives enough flexibility for you to extend your problem. Add testcases, set a custom checker, write a generator.

---

Proceed to the [Installation](intro/installation.md) section.