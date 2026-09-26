from unittest import TestCase
from unittest.mock import Mock

from pwem.protocols.protocol_movies import ProtProcessMovies


class TestProtProcessMoviesFinalizationRegression(TestCase):

    def testFinishedStepsCheckIsNoOp(self):
        class _Harness:
            finished = True

            def __init__(self):
                self._checkNewInput = Mock()
                self._checkNewOutput = Mock()

        protocol = _Harness()

        ProtProcessMovies._stepsCheck(protocol)

        protocol._checkNewInput.assert_not_called()
        protocol._checkNewOutput.assert_not_called()
