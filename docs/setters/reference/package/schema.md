# Problem schema

## `problem.rbx.yml`

::: robox.box.schema
    options:
      show_root_heading: false
      show_root_toc_entry: false
      heading_level: 3
      show_labels: false

## Statements

::: robox.box.statements.schema.Statement
    options:
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

::: robox.box.statements.schema.StatementType
    options:
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
      show_labels: false
      members_order: source

### Conversion nodes

::: robox.box.statements.schema
    options:
      filters: ["!^Statement(Type)?$",]
      show_root_heading: false
      show_root_toc_entry: false
      heading_level: 4