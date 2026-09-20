import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from pwem.protocols.protocol_micrographs import ProtCTFMicrographs


class TestCTFMicrographsStreaming(unittest.TestCase):

    def test_CheckNewInputReloadsLogicalSetWhenPhysicalMtimeIsUnchanged(self):
        protocol = ProtCTFMicrographs()
        protocol.micDict = {}
        protocol.listOfMics = []
        protocol.lastCheck = datetime.now()
        protocol._getFirstJoinStep = Mock(return_value=None)

        inputMics = MagicMock()
        inputMics.getFileName.return_value = "/tmp/micrographs.sqlite"

        inputPointer = MagicMock()
        inputPointer.get.return_value = inputMics
        protocol.inputMicrographs = inputPointer

        with patch(
            "pwem.protocols.protocol_micrographs.getmtime",
            return_value=0,
            create=True,
        ), patch.object(
            protocol,
            "_loadInputList",
            return_value=({}, False),
        ) as loadInputList:
            protocol._checkNewInput()

        loadInputList.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
