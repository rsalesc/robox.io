# Problem schema

## `problem.rbx.yml`

::: rbx.box.schema
    options:
      show_root_heading: false
      show_root_toc_entry: false
      heading_level: 3
      show_labels: false

## Statements

::: rbx.box.statements.schema.Statement
    options:
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3

::: rbx.box.statements.schema.StatementType
    options:
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
      show_labels: false
      members_order: source

### Conversion nodes

::: rbx.box.statements.schema
    options:
      filters: ["!^Statement(Type)?$",]
      show_root_heading: false
      show_root_toc_entry: false
      heading_level: 4