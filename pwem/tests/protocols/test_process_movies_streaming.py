import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from pwem.protocols.protocol_movies import ProtProcessMovies


class TestProcessMoviesStreaming(unittest.TestCase):

    def test_CheckNewInputReloadsLogicalSetWhenPhysicalMtimeIsUnchanged(self):
        protocol = ProtProcessMovies()
        protocol.insertedDict = {}
        protocol.listOfMovies = []
        protocol.lastCheck = datetime.now()
        protocol._getFirstJoinStep = Mock(return_value=None)

        inputMoviesSet = MagicMock()
        inputMoviesSet.getFileName.return_value = "/tmp/movies.sqlite"

        inputMovies = MagicMock()
        inputMovies.get.return_value = inputMoviesSet
        protocol.inputMovies = inputMovies

        with patch(
            "pwem.protocols.protocol_movies.os.path.getmtime",
            return_value=0,
        ), patch.object(
            protocol,
            "_loadInputList",
        ) as loadInputList:
            protocol._checkNewInput()

        loadInputList.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
