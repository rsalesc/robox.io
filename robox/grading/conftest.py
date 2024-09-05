import pathlib
from collections.abc import Iterator

import pytest

from robox.grading.caching import DependencyCache
from robox.grading.judge.cacher import FileCacher
from robox.grading.judge.sandbox import SandboxBase
from robox.grading.judge.sandboxes.stupid_sandbox import StupidSandbox
from robox.grading.judge.storage import FilesystemStorage, Storage


@pytest.fixture
def storage(request, cleandir: pathlib.Path) -> Iterator[Storage]:
    storage_path = cleandir / '.box' / '.storage'
    yield FilesystemStorage(storage_path)


@pytest.fixture
def file_cacher(request, storage: Storage) -> Iterator[FileCacher]:
    yield FileCacher(storage)


@pytest.fixture
def sandbox(request, file_cacher: FileCacher) -> Iterator[SandboxBase]:
    yield StupidSandbox(file_cacher=file_cacher)


@pytest.fixture
def dependency_cache(
    request, cleandir: pathlib.Path, storage: Storage
) -> Iterator[DependencyCache]:
    yield DependencyCache(cleandir / '.box', storage)
