import dataclasses
import pathlib
from typing import List, BinaryIO, IO, Optional, Tuple, TypeVar

import logging
import io
import os
import tempfile
from abc import ABC, abstractmethod

import gevent

logger = logging.getLogger(__name__)

T = TypeVar("T")

TOMBSTONE = "x"


def copyfileobj(
    source_fobj: IO[T], destination_fobj: IO[T], buffer_size=io.DEFAULT_BUFFER_SIZE
):
    """Read all content from one file object and write it to another.
    Repeatedly read from the given source file object, until no content
    is left, and at the same time write the content to the destination
    file object. Never read or write more than the given buffer size.
    Be cooperative with other greenlets by yielding often.
    source_fobj (fileobj): a file object open for reading, in either
        binary or str mode (doesn't need to be buffered).
    destination_fobj (fileobj): a file object open for writing, in the
        same mode as the source (doesn't need to be buffered).
    buffer_size (int): the size of the read/write buffer.
    """
    while True:
        buffer = source_fobj.read(buffer_size)
        if len(buffer) == 0:
            break
        while len(buffer) > 0:
            gevent.sleep(0)
            written = destination_fobj.write(buffer)
            buffer = buffer[written:]
        gevent.sleep(0)


@dataclasses.dataclass
class PendingFile:
    fd: BinaryIO
    filename: str


@dataclasses.dataclass
class FileWithDescription:
    filename: str
    description: str


class Storage(ABC):
    """Abstract base class for all concrete storages."""

    @abstractmethod
    def get_file(self, filename: str) -> BinaryIO:
        """Retrieve a file from the storage.
        filename (unicode): the path of the file to retrieve.
        return (fileobj): a readable binary file-like object from which
            to read the contents of the file.
        raise (KeyError): if the file cannot be found.
        """
        pass

    @abstractmethod
    def create_file(self, filename: str) -> Optional[PendingFile]:
        """Create an empty file that will live in the storage.
        Once the caller has written the contents to the file, the commit_file()
        method must be called to commit it into the store.
        filename (unicode): the filename of the file to store.
        return (fileobj): a writable binary file-like object on which
            to write the contents of the file, or None if the file is
            already stored.
        """
        pass

    @abstractmethod
    def commit_file(self, file: PendingFile, desc: str = "") -> bool:
        """Commit a file created by create_file() to be stored.
        Given a file object returned by create_file(), this function populates
        the database to record that this file now legitimately exists and can
        be used.
        fobj (fileobj): the object returned by create_file()
        file (PendingFile): the file to commit.
        return (bool): True if the file was committed successfully, False if
            there was already a file with the same filename in the database. This
            shouldn't make any difference to the caller, except for testing
            purposes!
        """
        pass

    @abstractmethod
    def describe(self, filename: str) -> str:
        """Return the description of a file given its filename.
        filename (unicode): the filename of the file to describe.
        return (unicode): the description of the file.
        raise (KeyError): if the file cannot be found.
        """
        pass

    @abstractmethod
    def get_size(self, filename: str) -> int:
        """Return the size of a file given its filename.
        filename (unicode): the filename of the file to calculate the size
            of.
        return (int): the size of the file, in bytes.
        raise (KeyError): if the file cannot be found.
        """
        pass

    @abstractmethod
    def delete(self, filename: str):
        """Delete a file from the storage.
        filename (unicode): the filename of the file to delete.
        """
        pass

    @abstractmethod
    def list(self) -> List[FileWithDescription]:
        """List the files available in the storage.
        return ([(unicode, unicode)]): a list of pairs, each
            representing a file in the form (filename, description).
        """
        pass


class FilesystemStorage(Storage):
    """This class implements a backend for FileCacher that keeps all
    the files in a file system directory, named after their filename.
    """

    def __init__(self, path: pathlib.Path):
        """Initialize the backend.
        path (string): the base path for the storage.
        """
        self.path = path

        # Create the directory if it doesn't exist
        path.mkdir(parents=True, exist_ok=True)

    def get_file(self, filename: str) -> BinaryIO:
        """See FileCacherBackend.get_file()."""
        file_path = self.path / filename

        if not file_path.is_file():
            raise KeyError("File not found.")

        return file_path.open("rb")

    def create_file(self, filename: str) -> Optional[PendingFile]:
        """See FileCacherBackend.create_file()."""
        # Check if the file already exists. Return None if so, to inform the
        # caller they don't need to store the file.
        file_path = self.path / filename

        if file_path.is_file():
            return None

        # Create a temporary file in the same directory
        temp_file = tempfile.NamedTemporaryFile(
            "wb", delete=False, prefix=".tmp.", suffix=filename, dir=self.path
        )
        return PendingFile(fd=temp_file, filename=filename)

    def commit_file(self, file: PendingFile, desc: str = "") -> bool:
        """See FileCacherBackend.commit_file()."""
        file.fd.close()

        file_path: pathlib.Path = self.path / file.filename
        # Move it into place in the cache. Skip if it already exists, and
        # delete the temporary file instead.
        if not file_path.is_file():
            # There is a race condition here if someone else puts the file here
            # between checking and renaming. Put it doesn't matter in practice,
            # because rename will replace the file anyway (which should be
            # identical).
            os.rename(file.fd.name, str(file_path))
            return True
        else:
            os.unlink(file.fd.name)
            return False

    def describe(self, filename: str) -> str:
        """See FileCacherBackend.describe()."""
        file_path: pathlib.Path = self.path / filename

        if not file_path.is_file():
            raise KeyError("File not found.")

        return ""

    def get_size(self, filename: str) -> int:
        """See FileCacherBackend.get_size()."""
        file_path: pathlib.Path = self.path / filename

        if not file_path.is_file():
            raise KeyError("File not found.")

        return file_path.stat().st_size

    def delete(self, filename: str):
        """See FileCacherBackend.delete()."""
        file_path: pathlib.Path = self.path / filename

        file_path.unlink(missing_ok=True)

    def list(self) -> List[FileWithDescription]:
        """See FileCacherBackend.list()."""
        res = []
        for path in self.path.glob("*"):
            if path.is_file():
                res.append(
                    FileWithDescription(
                        filename=str(path.relative_to(self.path)), description=""
                    )
                )
        return res
