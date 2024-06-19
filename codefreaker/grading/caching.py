import atexit
from collections.abc import Iterator
import io
import os
import pathlib
import shelve
from typing import List, Optional
from contextlib import contextmanager

from pydantic import BaseModel
from codefreaker.grading.judge.digester import digest_cooperatively
from codefreaker.grading.judge.storage import Storage
from codefreaker.grading.steps import DigestHolder, GradingArtifacts
from codefreaker import console


class CacheInput(BaseModel):
    commands: List[str]
    artifacts: List[GradingArtifacts]


class CacheFingerprint(BaseModel):
    digests: List[Optional[str]]
    fingerprints: List[str]


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


def _build_fingerprint_list(artifacts_list: List[GradingArtifacts]) -> List[str]:
    fingerprints = []
    for artifacts in artifacts_list:
        for input in artifacts.inputs:
            if input.src is None:
                continue
            fingerprints.append(digest_cooperatively(input.src.open("rb")))
    return fingerprints


def _build_cache_fingerprint(
    artifacts_list: List[GradingArtifacts],
) -> CacheFingerprint:
    digests = [digest.value for digest in _build_digest_list(artifacts_list)]
    fingerprints = _build_fingerprint_list(artifacts_list)
    return CacheFingerprint(digests=digests, fingerprints=fingerprints)


def _fingerprints_match(
    fingerprint: CacheFingerprint, reference: CacheFingerprint
) -> bool:
    lhs, rhs = fingerprint.fingerprints, reference.fingerprints
    return tuple(lhs) == tuple(rhs)


def _build_cache_key(input: CacheInput) -> str:
    return digest_cooperatively(io.BytesIO(input.model_dump_json().encode()))


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


class DependencyCacheBlock:
    class Break(Exception):
        pass

    def __init__(
        self,
        cache: "DependencyCache",
        commands: List[str],
        artifact_list: List[GradingArtifacts],
    ):
        self.cache = cache
        self.commands = commands
        self.artifact_list = artifact_list
        self._key = None

    def __enter__(self):
        input = CacheInput(commands=self.commands, artifacts=self.artifact_list)
        self._key = _build_cache_key(input)
        found = self.cache.find_in_cache(
            self.commands, self.artifact_list, key=self._key
        )
        return found

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.cache.store_in_cache(self.commands, self.artifact_list, key=self._key)
        return None


class DependencyCache:
    root: pathlib.Path
    storage: Storage

    def __init__(self, root: pathlib.Path, storage: Storage):
        self.root = root
        self.storage = storage
        self.db = shelve.open(self._cache_name())
        atexit.register(lambda: self.db.close())

    def _cache_name(self) -> str:
        return str(self.root / ".cache_db")

    def _find_in_cache(self, key: str) -> Optional[CacheFingerprint]:
        return self.db.get(key)

    def _store_in_cache(self, key: str, fingerprint: CacheFingerprint):
        self.db[key] = fingerprint

    def __call__(
        self, commands: List[str], artifact_list: List[GradingArtifacts]
    ) -> DependencyCacheBlock:
        _check_digests(artifact_list)
        return DependencyCacheBlock(self, commands, artifact_list)

    def find_in_cache(
        self,
        commands: List[str],
        artifact_list: List[GradingArtifacts],
        key: Optional[str] = None,
    ) -> bool:
        input = CacheInput(commands=commands, artifacts=artifact_list)
        key = key or _build_cache_key(input)

        fingerprint = self._find_in_cache(key)
        if fingerprint is None:
            return False

        reference_fingerprint = _build_cache_fingerprint(artifact_list)

        if not _fingerprints_match(fingerprint, reference_fingerprint):
            return False

        reference_digests = _build_digest_list(artifact_list)

        old_digest_values = [digest for digest in reference_fingerprint.digests]
        for digest, reference_digest in zip(fingerprint.digests, reference_digests):
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
        key: Optional[str] = None,
    ):
        input = CacheInput(commands=commands, artifacts=artifact_list)
        key = key or _build_cache_key(input)

        if not are_artifacts_ok(artifact_list, self.storage):
            return

        self._store_in_cache(key, _build_cache_fingerprint(artifact_list))
