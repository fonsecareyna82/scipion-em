import unittest
from unittest.mock import MagicMock, Mock

from pwem.protocols.protocol_align_movies import ProtAlignMovies


class TestAlignMoviesStreaming(unittest.TestCase):

    def test_OutputUpdatersSkipItemsAlreadyPersisted(self):
        protocol = ProtAlignMovies()
        protocol._firstTimeOutput = False

        movie = MagicMock()
        movie.getObjId.return_value = 7
        movie.getMicName.return_value = "mic_000007"

        existingMovieSet = MagicMock()
        existingMovieSet.getIdSet.return_value = {7}
        protocol._loadOutputSet = Mock(return_value=existingMovieSet)
        protocol.getAttributeValue = Mock(return_value=False)
        protocol._createOutputMovie = Mock()

        protocol._updateOutputMovieSet([movie], 1)

        protocol._createOutputMovie.assert_not_called()
        existingMovieSet.append.assert_not_called()

        existingMicSet = MagicMock()
        existingMicSet.getIdSet.return_value = {7}
        protocol._loadOutputSet = Mock(return_value=existingMicSet)
        protocol._getExtraPath = Mock(
            return_value="/tmp/micrograph_000007.mrc"
        )

        protocol._updateOutputMicSet(
            [movie],
            "micrographs.sqlite",
            lambda m: "micrograph_000007.mrc",
            "outputMicrographs",
            1,
        )

        existingMicSet.append.assert_not_called()

    def test_DoneCheckpointIsWrittenOnlyAfterOutputsArePersisted(self):
        protocol = ProtAlignMovies()
        protocol.finished = False
        protocol.streamClosed = False

        movie = MagicMock()
        movie.getObjId.return_value = 7
        protocol.listOfMovies = [movie]

        protocol._readDoneList = Mock(return_value=[])
        protocol._isMovieDone = Mock(return_value=True)
        protocol._getFirstJoinStep = Mock(return_value=None)

        events = []
        protocol._writeDoneList = Mock(
            side_effect=lambda *args, **kwargs: events.append("done")
        )
        protocol._updateOutputSets = Mock(
            side_effect=lambda *args, **kwargs: events.append("persist")
        )

        protocol._checkNewOutput()

        self.assertIn("persist", events)
        self.assertIn("done", events)
        self.assertLess(
            events.index("persist"),
            events.index("done"),
            "DONE must not be recorded before movie outputs are persisted.",
        )


if __name__ == "__main__":
    unittest.main()
