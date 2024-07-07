# Contest package

This documentation goes over how each field (or group of fields) in `contest.rbx.yml` works.

## Contest definition

**Schema**: [robox.box.contest.schema.Contest][]

The only required field of a contest is its `name`.

A barebones package would look something like:

```yaml
name: "my-problem"
```

## Contest information

**Schema**: `Dict[str, `[`ContestInformation`][robox.box.contest.schema.ContestInformation]`]`

In contest information we can configure localized information about the contest, such as:

- Problem title;
- Location;
- Date

```yaml
name: "my-contest"
information:
  en:
    title: "My contest"
    location: "My house"  # Optional
    date: "Today"  # Optional
  pt:
    title: "Meu contest"
    location: "Minha casa"  # Optional
    date: "Hoje"  # Optional
```

## Contest problem

**Schema**: `List[`[`ContestProblem`][robox.box.contest.schema.ContestProblem]`]`

```yaml
name: "my-contest"
problems:
  - short_name: "A"
    path: "A"
    color: "ff0000"
  - short_name: "B"
    path: "B"
    color: "00ff00"
```