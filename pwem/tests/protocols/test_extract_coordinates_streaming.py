import unittest
from unittest.mock import MagicMock, Mock, patch

from pwem.protocols.protocol_extract_coordinates import ProtExtractCoords


class TestExtractCoordinatesStreaming(unittest.TestCase):

    def test_LoadOutputSetReusesLogicalOutputWithoutBackingFile(self):
        # Regression test: an output that Scipion already knows about
        # (protocol.outputCoordinates) must be reused even when its backing
        # file was never materialized on disk yet. Falling through to "no
        # backing file -> build a fresh, empty Set" would silently discard
        # whatever was already appended to the real logical output, and
        # would wrongly redefine the transform/source relations again.
        protocol = ProtExtractCoords()
        protocol._getPath = Mock(return_value="/tmp/coordinates.dat")
        protocol._store = Mock()
        protocol._defineTransformRelation = Mock()
        protocol._defineSourceRelation = Mock()
        protocol.getInputMicrographsPointer = Mock(return_value=MagicMock())

        existingCoordSet = MagicMock()
        protocol.outputCoordinates = existingCoordSet

        with patch(
            "pwem.protocols.protocol_extract_coordinates.os.path.exists",
            return_value=False,
        ):
            outputSet = protocol._loadOutputSet()

        self.assertIs(existingCoordSet, outputSet)
        existingCoordSet.enableAppend.assert_called_once()
        protocol._store.assert_not_called()
        protocol._defineTransformRelation.assert_not_called()
        protocol._defineSourceRelation.assert_not_called()


if __name__ == "__main__":
    unittest.main()
