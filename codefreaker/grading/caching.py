from collections.abc import Iterator
import os
import pathlib
import shelve
from typing import List, Optional
from contextlib import contextmanager

from pydantic import BaseModel
from codefreaker.grading.judge.digester import Digester
from codefreaker.grading.judge.storage import Storage
from codefreaker.grading.steps import DigestHolder, GradingArtifacts


class CacheInput(BaseModel):
    commands: List[str]
    artifacts: List[GradingArtifacts]


def _check_digests(artifacts_list: List[GradingArtifacts]):
    produced = set()
    for artifacts in artifacts_list:
        for input in artifacts.inputs:
            if input.digest is None:
                continue
            if input.digest.value is not None:
                continue
            if id(input.digest) not in produced:
                raise ValueError("Digests must be produced before being consumed")
        for output in artifacts.outputs:
            if output.digest is None:
                continue
            if output.digest.value is not None:
                continue
            if id(output.digest) in produced:
                raise ValueError("A digest cannot be produced more than once")
            produced.add(id(output.digest))


def _build_digest_list(artifacts_list: List[GradingArtifacts]) -> List[DigestHolder]:
    digests = []
    for artifacts in artifacts_list:
        for output in artifacts.outputs:
            if output.digest is None:
                continue
            digests.append(output.digest)
    return digests


def _build_cache_key(input: CacheInput) -> str:
    hash = Digester()
    hash.update(input.model_dump_json().encode())
    return hash.digest()


def is_artifact_ok(artifact: GradingArtifacts, storage: Storage) -> bool:
    for output in artifact.outputs:
        if output.optional or output.intermediate:
            continue
        if output.digest is not None:
            if output.digest.value is None or not storage.exists(output.digest.value):
                return False
            return True
        file_path: pathlib.Path = artifact.root / output.dest
        if not file_path.is_file():
            return False
        executable = os.access(str(file_path), os.X_OK)
        if executable != output.executable:
            return False
    return True


def are_artifacts_ok(artifacts: List[GradingArtifacts], storage: Storage) -> bool:
    for artifact in artifacts:
        if not is_artifact_ok(artifact, storage):
            return False
    return True


class DependencyCache:
    root: pathlib.Path
    storage: Storage

    def __init__(self, root: pathlib.Path, storage: Storage):
        self.root = root
        self.storage = storage

    def _cache_name(self) -> str:
        return str(self.root / ".cache_db")

    def _find_in_cache(self, key: str) -> Optional[List[Optional[str]]]:
        with shelve.open(self._cache_name()) as db:
            return db.get(key)

    def _store_in_cache(self, key: str, digests: List[Optional[str]]):
        with shelve.open(self._cache_name()) as db:
            db[key] = digests

    @contextmanager
    def __call__(
        self, commands: List[str], artifact_list: List[GradingArtifacts]
    ) -> Iterator[None]:
        _check_digests(artifact_list)
        if self.find_in_cache(commands, artifact_list):
            return
        try:
            yield
        except:
            raise
        finally:
            self.store_in_cache(commands, artifact_list)

    def find_in_cache(
        self, commands: List[str], artifact_list: List[GradingArtifacts]
    ) -> bool:
        input = CacheInput(commands=commands, artifacts=artifact_list)
        key = _build_cache_key(input)
        digests = self._find_in_cache(key)
        if digests is None:
            return False

        reference_digests = _build_digest_list(artifact_list)
        if len(digests) != len(reference_digests):
            return False

        old_digest_values = [digest.value for digest in reference_digests]
        for digest, reference_digest in zip(digests, reference_digests):
            reference_digest.value = digest
        if are_artifacts_ok(artifact_list, self.storage):
            return True

        # Rollback changes.
        for old_digest_value, reference_digest in zip(
            old_digest_values, reference_digests
        ):
            reference_digest.value = old_digest_value

        return False

    def store_in_cache(
        self,
        commands: List[str],
        artifact_list: List[GradingArtifacts],
    ):
        if not are_artifacts_ok(artifact_list, self.storage):
            return
        input = CacheInput(commands=commands, artifacts=artifact_list)
        key = _build_cache_key(input)

        reference_digests = _build_digest_list(artifact_list)
        digests = [digest.value for digest in reference_digests]
        self._store_in_cache(key, digests)
