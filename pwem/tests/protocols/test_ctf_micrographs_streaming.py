import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from pwem.protocols.protocol_micrographs import ProtCTFMicrographs


class _FakeMic:
    def __init__(self, objId):
        self._objId = objId

    def getObjId(self):
        return self._objId

    def getMicName(self):
        return 'mic_%03d' % self._objId


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

    def test_EstimateCtfListSkipsFailingMicrographAndKeepsProcessingOthers(self):
        # Regression test: with streamingBatchSize > 1,
        # estimateCtfListStep calls the batch-level _estimateCtfList.
        # Its default implementation must not let a single
        # corrupted/failing micrograph crash the whole batch (and hence
        # the whole protocol via pyworkflow's fail-on-any-exception step
        # boundary) - any subclass that doesn't override it with its own
        # isolation inherits this default.
        protocol = ProtCTFMicrographs()
        protocol.error = Mock()

        processed = []

        def fakeEstimateCTF(mic, *args):
            processed.append(mic.getObjId())
            if mic.getObjId() == 2:
                raise ValueError("corrupted micrograph")

        protocol._estimateCTF = fakeEstimateCTF
        micList = [_FakeMic(1), _FakeMic(2), _FakeMic(3)]

        protocol._estimateCtfList(micList)

        self.assertEqual([1, 2, 3], processed)
        protocol.error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
