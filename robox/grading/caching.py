import atexit
import io
import os
import pathlib
import shelve
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from robox.grading.judge.digester import digest_cooperatively
from robox.grading.judge.storage import Storage
from robox.grading.steps import DigestHolder, GradingArtifacts, GradingLogsHolder


class CacheInput(BaseModel):
    commands: List[str]
    artifacts: List[GradingArtifacts]
    extra_params: Dict[str, Any] = {}


class CacheFingerprint(BaseModel):
    digests: List[Optional[str]]
    fingerprints: List[str]
    output_fingerprints: List[str]
    logs: List[GradingLogsHolder]


def _check_digests(artifacts_list: List[GradingArtifacts]):
    produced = set()
    for artifacts in artifacts_list:
        for input in artifacts.inputs:
            if input.digest is None:
                continue
            if input.digest.value is not None:
                continue
            if id(input.digest) not in produced:
                raise ValueError('Digests must be produced before being consumed')
        for output in artifacts.outputs:
            if output.digest is None:
                continue
            if output.digest.value is not None:
                continue
            if id(output.digest) in produced:
                raise ValueError('A digest cannot be produced more than once')
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
            with input.src.open('rb') as f:
                fingerprints.append(digest_cooperatively(f))
    return fingerprints


def _build_output_fingerprint_list(artifacts_list: List[GradingArtifacts]) -> List[str]:
    fingerprints = []
    for artifacts in artifacts_list:
        for output in artifacts.outputs:
            if output.dest is None or output.intermediate:
                continue
            if not output.dest.is_file():
                fingerprints.append('')  # file does not exist
                continue
            with output.dest.open('rb') as f:
                fingerprints.append(digest_cooperatively(f))
    return fingerprints


def _build_logs_list(artifacts_list: List[GradingArtifacts]) -> List[GradingLogsHolder]:
    logs = []
    for artifacts in artifacts_list:
        if artifacts.logs is not None:
            logs.append(artifacts.logs)
    return logs


def _build_cache_fingerprint(
    artifacts_list: List[GradingArtifacts],
) -> CacheFingerprint:
    digests = [digest.value for digest in _build_digest_list(artifacts_list)]
    fingerprints = _build_fingerprint_list(artifacts_list)
    output_fingerprints = _build_output_fingerprint_list(artifacts_list)
    logs = _build_logs_list(artifacts_list)
    return CacheFingerprint(
        digests=digests,
        fingerprints=fingerprints,
        output_fingerprints=output_fingerprints,
        logs=logs,
    )


def _fingerprints_match(
    fingerprint: CacheFingerprint, reference: CacheFingerprint
) -> bool:
    lhs, rhs = fingerprint.fingerprints, reference.fingerprints
    return tuple(lhs) == tuple(rhs)


def _output_fingerprints_match(
    fingerprint: CacheFingerprint, reference: CacheFingerprint
) -> bool:
    lhs, rhs = fingerprint.output_fingerprints, reference.output_fingerprints
    return tuple(lhs) == tuple(rhs)


def _build_cache_key(input: CacheInput) -> str:
    with io.BytesIO(input.model_dump_json().encode()) as fobj:
        return digest_cooperatively(fobj)


def is_artifact_ok(artifact: GradingArtifacts, storage: Storage) -> bool:
    for output in artifact.outputs:
        if output.optional or output.intermediate:
            continue
        if output.digest is not None:
            if output.digest.value is None or not storage.exists(output.digest.value):
                return False
            return True
        assert output.dest is not None
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
        cache: 'DependencyCache',
        commands: List[str],
        artifact_list: List[GradingArtifacts],
        extra_params: Dict[str, Any],
    ):
        self.cache = cache
        self.commands = commands
        self.artifact_list = artifact_list
        self.extra_params = extra_params
        self._key = None

    def __enter__(self):
        input = CacheInput(
            commands=self.commands,
            artifacts=self.artifact_list,
            extra_params=self.extra_params,
        )
        self._key = _build_cache_key(input)
        found = self.cache.find_in_cache(
            self.commands, self.artifact_list, self.extra_params, key=self._key
        )
        return found

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.cache.store_in_cache(
                self.commands, self.artifact_list, self.extra_params, key=self._key
            )
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
        return str(self.root / '.cache_db')

    def _find_in_cache(self, key: str) -> Optional[CacheFingerprint]:
        return self.db.get(key)

    def _store_in_cache(self, key: str, fingerprint: CacheFingerprint):
        self.db[key] = fingerprint

    def _evict_from_cache(self, key: str):
        if key in self.db:
            del self.db[key]

    def __call__(
        self,
        commands: List[str],
        artifact_list: List[GradingArtifacts],
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> DependencyCacheBlock:
        _check_digests(artifact_list)
        return DependencyCacheBlock(self, commands, artifact_list, extra_params or {})

    def find_in_cache(
        self,
        commands: List[str],
        artifact_list: List[GradingArtifacts],
        extra_params: Dict[str, Any],
        key: Optional[str] = None,
    ) -> bool:
        input = CacheInput(
            commands=commands, artifacts=artifact_list, extra_params=extra_params
        )
        key = key or _build_cache_key(input)

        fingerprint = self._find_in_cache(key)
        if fingerprint is None:
            return False

        reference_fingerprint = _build_cache_fingerprint(artifact_list)

        if not _fingerprints_match(fingerprint, reference_fingerprint):
            self._evict_from_cache(key)
            return False

        if not _output_fingerprints_match(fingerprint, reference_fingerprint):
            self._evict_from_cache(key)
            return False

        reference_digests = _build_digest_list(artifact_list)

        # Apply digest changes.
        old_digest_values = [digest for digest in reference_fingerprint.digests]
        for digest, reference_digest in zip(fingerprint.digests, reference_digests):
            reference_digest.value = digest

        if not are_artifacts_ok(artifact_list, self.storage):
            # Rollback digest changes.
            for old_digest_value, reference_digest in zip(
                old_digest_values, reference_digests
            ):
                reference_digest.value = old_digest_value
            self._evict_from_cache(key)
            return False

        # Apply logs changes.
        for logs, reference_logs in zip(fingerprint.logs, reference_fingerprint.logs):
            if logs.run is not None:
                reference_logs.run = logs.run.model_copy(deep=True)

        return True

    def store_in_cache(
        self,
        commands: List[str],
        artifact_list: List[GradingArtifacts],
        extra_params: Dict[str, Any],
        key: Optional[str] = None,
    ):
        input = CacheInput(
            commands=commands, artifacts=artifact_list, extra_params=extra_params
        )
        key = key or _build_cache_key(input)

        if not are_artifacts_ok(artifact_list, self.storage):
            return

        self._store_in_cache(key, _build_cache_fingerprint(artifact_list))
