import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from pwem.protocols.protocol_particles_picking import ProtParticlePickingAuto


class TestParticlePickingAutoStreaming(unittest.TestCase):

    def test_CheckNewInputReloadsLogicalSetWhenPhysicalMtimeIsUnchanged(self):
        protocol = ProtParticlePickingAuto()
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
            "pwem.protocols.protocol_particles_picking.os.path.getmtime",
            return_value=0,
        ), patch.object(
            protocol,
            "_loadInputList",
            return_value=({}, False),
        ) as loadInputList:
            protocol._checkNewInput()

        loadInputList.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
