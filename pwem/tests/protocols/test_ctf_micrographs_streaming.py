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

        fileStat = MagicMock()
        fileStat.st_mtime_ns = 123
        fileStat.st_size = 456

        with patch(
            "pwem.protocols.protocol_micrographs.os.stat",
            return_value=fileStat,
        ), patch.object(
            protocol,
            "_loadInputList",
            return_value=({}, False),
        ) as loadInputList:
            protocol._checkNewInput()
            protocol._checkNewInput()

        self.assertEqual(
            2,
            loadInputList.call_count,
            "Logical Set state must be reloaded even when the compatibility "
            "SQLite/WAL physical signature is unchanged.",
        )


if __name__ == "__main__":
    unittest.main()
