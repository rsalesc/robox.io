from typing import List, Optional
import rich.status
import rich
import fastapi
import uvicorn
import logging
import threading
import pathlib

from .schema import Problem
from .console import console
from .config import get_config, Language, format_vars

def clear_loggers():
  for logger_name in [
    'uvicorn',
    'uvicorn.access',
    'uvicorn.asgi',
  ]:
    logging.getLogger(logger_name).handlers.clear()
    logging.getLogger(logger_name).propagate = False

def create_problem_structure(problem: Problem, lang: Language):
  # Create directory structure.
  root = pathlib.Path()
  root.parent.mkdir(parents=True, exist_ok=True)

  code_path = root / lang.get_file(problem.get_file_basename())
  json_path = root / f'{problem.get_file_basename()}.cfk.json'

  json_path.write_text(problem.model_dump_json())
  code_path.write_text(format_vars(lang.get_template(), **problem.get_vars()))

def process_problems(problems: List[Problem], lang: Language):
  console.print(f'Creating problem structure for [item]{len(problems)}[/item] problems...')
  for problem in problems:
    create_problem_structure(problem, lang)
                                                                                                                                                                    
def main(lang: Optional[str] = None):
  if get_config().get_language(lang) is None:
    console.print(f'[error]Language {lang or get_config().defaultLanguage} not found in config. Please check your configuration.[/error]')
    return

  app = fastapi.FastAPI()

  async def shutdown():
    server.should_exit = True

  batch_to_left_lock = threading.Lock()
  batch_to_left = {}
  ignored = set()
  saved_status = None
  problems_to_process = []

  def process_batch_item(problem: Problem):
    batch_to_left_lock.acquire()
    if problem.batch.id in ignored:
      batch_to_left_lock.release()
      return True
    if problem.batch.id not in batch_to_left:
      if len(batch_to_left) > 0:
        console.print(f'[error]Ignoring extra batch [item]{problem.batch.id}[/item] since other batch is being parsed.[/error]')
        ignored.add(problem.batch.id)
        batch_to_left_lock.release()
        return True
      if problem.batch.size > 1:
        saved_status.update(f'[cfk]Codefreaker[/cfk] is parsing problems from group [item]{problem.group}[/item]')
      else:
        saved_status.update(f'[cfk]Codefreaker[/cfk] is parsing problems...')
      console.print(f'Started parsing batch [item]{problem.batch.id}[/item] with size [item]{problem.batch.size}[/item].')
      batch_to_left[problem.batch.id] = problem.batch.size
    console.print(f'Parsing problem [item]{problem.name}[/item]...')
    problems_to_process.append(problem)
    finished = False
    if batch_to_left[problem.batch.id] == 1:
      finished = True
      if problem.batch.size > 1:
        console.print(f'[status][cfk]Codefreaker[/cfk] parsed all problems from group [item]{problem.group}[/item].[/status]')
      else:
        console.print(f'[status][cfk]Codefreaker[/cfk] parsed problem from [item]{problem.url}[/item].[/status]')
    else:
      batch_to_left[problem.batch.id] -= 1
    batch_to_left_lock.release()
    return not finished

  @app.post('/')
  async def parse(problem: Problem, background_tasks: fastapi.BackgroundTasks):
    if not process_batch_item(problem):
      background_tasks.add_task(shutdown)
    return {}

  config = uvicorn.Config(app, port=10045)
  server = uvicorn.Server(config=config)
  clear_loggers()
  with console.status('Waiting for Competitive Companion request...') as status:
    saved_status = status
    server.run()

  with console.status('Processing parsed problems...') as status:
    process_problems(problems_to_process, get_config().get_language(lang))