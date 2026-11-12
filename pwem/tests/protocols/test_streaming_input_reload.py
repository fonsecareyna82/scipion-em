"""The movie, micrograph and particle protocol bases read their streaming input Set itself on every poll:
the same Set object sees what its producer appends and when it closes the stream, and the Set is never
opened again by its file name (which makes some storages write a whole copy of it)."""
import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace

from pyworkflow.object import Set

import pwem.objects as emobj
from pwem.protocols.protocol_micrographs import ProtCTFMicrographs
from pwem.protocols.protocol_movies import ProtProcessMovies


class _Input:
    """A pointer holding the consumer's own Set object, as a protocol's input does."""

    def __init__(self, inputSet):
        self.inputSet = inputSet

    def get(self):
        return self.inputSet


class TestStreamingInputReload(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def _produce(self, SetClass, ItemClass, path, names, closed):
        """The producer protocol: opens the Set file, appends items and writes it."""
        existed = os.path.exists(path)
        produced = SetClass(filename=path)
        if existed:
            produced.loadAllProperties()
            produced.enableAppend()
        if not produced.getSamplingRate():
            produced.setSamplingRate(1.0)
        for name in names:
            produced.append(ItemClass(location=os.path.join(self.folder, name)))
        produced.setStreamState(Set.STREAM_CLOSED if closed else Set.STREAM_OPEN)
        produced.write()
        produced.close()

    @staticmethod
    def _noFileNames(inputSet):
        def refuse():
            raise AssertionError("The input Set was opened again by its file name")
        inputSet.getFileName = refuse

    def test_MoviesSeeWhatTheProducerAddsAndWhenItCloses(self):
        path = os.path.join(self.folder, "movies.sqlite")
        self._produce(emobj.SetOfMovies, emobj.Movie, path, ["m1.mrcs", "m2.mrcs"], closed=False)
        consumerSet = emobj.SetOfMovies(filename=path)
        self._noFileNames(consumerSet)
        protocol = SimpleNamespace(inputMovies=_Input(consumerSet), debug=lambda *args: None)

        ProtProcessMovies._loadInputList(protocol)
        self.assertEqual([m.getFileName() for m in protocol.listOfMovies],
                         [os.path.join(self.folder, n) for n in ("m1.mrcs", "m2.mrcs")])
        self.assertFalse(protocol.streamClosed)

        self._produce(emobj.SetOfMovies, emobj.Movie, path, ["m3.mrcs"], closed=True)
        ProtProcessMovies._loadInputList(protocol)
        self.assertEqual(len(protocol.listOfMovies), 3)
        self.assertTrue(protocol.streamClosed)

    def test_MicrographsSeeWhatTheProducerAddsAndWhenItCloses(self):
        path = os.path.join(self.folder, "micrographs.sqlite")
        self._produce(emobj.SetOfMicrographs, emobj.Micrograph, path, ["a.mrc"], closed=False)
        consumerSet = emobj.SetOfMicrographs(filename=path)
        self._noFileNames(consumerSet)
        protocol = SimpleNamespace(micDict={}, debug=lambda *args: None)

        def load():
            return ProtCTFMicrographs._loadSet(protocol, consumerSet, emobj.SetOfMicrographs,
                                               lambda mic: os.path.basename(mic.getFileName()))

        newItems, closed = load()
        self.assertEqual(list(newItems), ["a.mrc"])
        self.assertFalse(closed)

        protocol.micDict["a.mrc"] = newItems["a.mrc"]
        self._produce(emobj.SetOfMicrographs, emobj.Micrograph, path, ["b.mrc"], closed=True)
        newItems, closed = load()
        self.assertEqual(list(newItems), ["b.mrc"])
        self.assertTrue(closed)


    def test_StoredIdsOfANewOutputAreNone(self):
        from pwem.utils import getStoredIds
        path = os.path.join(self.folder, "output.sqlite")
        output = emobj.SetOfMovies(filename=path)
        self.assertEqual(getStoredIds(output), set())

        storedPath = os.path.join(self.folder, "stored.sqlite")
        self._produce(emobj.SetOfMovies, emobj.Movie, storedPath, ["m1.mrcs", "m2.mrcs"], closed=False)
        stored = emobj.SetOfMovies(filename=storedPath)
        stored.loadAllProperties()
        self.assertEqual(getStoredIds(stored), {1, 2})


if __name__ == "__main__":
    unittest.main()
