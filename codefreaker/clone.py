import rich.status
import rich
import fastapi
import uvicorn
import logging
import threading

from .schema import Problem
from .console import console

def clear_loggers():
  for logger_name in [
    'uvicorn',
    'uvicorn.access',
    'uvicorn.asgi',
  ]:
    logging.getLogger(logger_name).handlers.clear()
    logging.getLogger(logger_name).propagate = False

def main():
  app = fastapi.FastAPI()

  async def shutdown():
    server.should_exit = True

  batch_to_left_lock = threading.Lock()
  batch_to_left = {}
  ignored = set()
  saved_status = None

  def process_batch_item(problem: Problem):
    batch_to_left_lock.acquire()
    if problem.batch.id in ignored:
      batch_to_left_lock.release()
      return True
    if problem.batch.id not in batch_to_left:
      if len(batch_to_left) > 0:
        console.print(f'[error]Ignoring extra batch [item]{problem.batch.id}[/item] since other batch is being processed.[/error]')
        ignored.add(problem.batch.id)
        batch_to_left_lock.release()
        return True
      if problem.batch.size > 1:
        saved_status.update(f'[cfk]Codefreaker[/cfk] is cloning problems from group [item]{problem.group}[/item]')
      else:
        saved_status.update(f'[cfk]Codefreaker[/cfk] is cloning problems...')
      console.print(f'Started processing batch [item]{problem.batch.id}[/item] with size [item]{problem.batch.size}[/item].')
      batch_to_left[problem.batch.id] = problem.batch.size
    console.print(f'Processing problem [item]{problem.name}[/item]...')
    finished = False
    if batch_to_left[problem.batch.id] == 1:
      finished = True
      if problem.batch.size > 1:
        console.print(f'[status][cfk]Codefreaker[/cfk] cloned all problems from group [item]{problem.group}[/item].[/status]')
      else:
        console.print(f'[status][cfk]Codefreaker[/cfk] cloned problem from [item]{problem.url}[/item].[/status]')
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