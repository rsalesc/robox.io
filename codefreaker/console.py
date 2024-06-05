from rich.console import Console
from rich.theme import Theme

theme = Theme({
  'cfk': 'bold italic yellow',
  'info': 'bright_black',
  'status': 'bright_white',
  'item': 'bold blue',
  'error': 'bold red',
})
console = Console(theme=theme, style='info', highlight=False)