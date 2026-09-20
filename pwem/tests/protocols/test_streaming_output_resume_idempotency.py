import unittest
from unittest.mock import MagicMock, Mock

from pwem.protocols.protocol_micrographs import ProtCTFMicrographs
from pwem.protocols.protocol_particles import ProtExtractParticles
from pwem.protocols.protocol_particles_picking import ProtParticlePickingAuto


def _mic(mic_id):
    mic = MagicMock()
    mic.getObjId.return_value = mic_id
    mic.strId.return_value = str(mic_id)
    return mic


class TestStreamingOutputResumeIdempotency(unittest.TestCase):

    def test_PickingSkipsMicrographsAlreadyPersistedBeforeDoneCheckpoint(self):
        protocol = ProtParticlePickingAuto()
        mic1 = _mic(1)
        mic2 = _mic(2)

        outputCoords = MagicMock()
        outputCoords.getUniqueValues.return_value = [1]
        protocol.outputCoordinates = outputCoords

        protocol._micIsReady = Mock(return_value=True)
        protocol.getCoordsDir = Mock(return_value="/tmp")
        protocol.readCoordsFromMics = Mock()
        protocol.getSummary = Mock(return_value="")
        protocol._updateOutputSet = Mock()

        updated = protocol._updateOutputCoordSet([mic1, mic2], 1)

        copiedMics = protocol.readCoordsFromMics.call_args.args[1]
        self.assertEqual([mic2], copiedMics)
        self.assertEqual([mic1, mic2], updated)
        outputCoords.getUniqueValues.assert_called_once_with("_micId")

    def test_ExtractParticlesSkipsMicrographsAlreadyPersistedBeforeDoneCheckpoint(self):
        protocol = ProtExtractParticles()
        mic1 = _mic(1)
        mic2 = _mic(2)

        outputParts = MagicMock()
        outputParts.getUniqueValues.return_value = [1]
        protocol.outputParticles = outputParts

        protocol.readPartsFromMics = Mock()
        protocol._updateOutputSet = Mock()

        protocol._updateOutputPartSet([mic1, mic2], 1)

        copiedMics = protocol.readPartsFromMics.call_args.args[0]
        self.assertEqual([mic2], copiedMics)
        outputParts.getUniqueValues.assert_called_once_with("_micId")

    def test_CTFSkipsMicrographsAlreadyPersistedBeforeDoneCheckpoint(self):
        protocol = ProtCTFMicrographs()
        mic1 = _mic(1)
        mic2 = _mic(2)

        outputCtf = MagicMock()
        outputCtf.getIdSet.return_value = {1}
        protocol.outputCTF = outputCtf

        ctf2 = MagicMock()
        protocol._iterMicrographs = Mock(
            return_value=iter([
                ("mic1", mic1),
                ("mic2", mic2),
            ])
        )
        protocol._createCtfModel = Mock(return_value=ctf2)
        protocol._updateOutputSet = Mock()
        protocol._writeFailedList = Mock()

        protocol._updateOutputCTFSet([mic1, mic2], 1)

        protocol._createCtfModel.assert_called_once_with(mic2)
        outputCtf.append.assert_called_once_with(ctf2)
        outputCtf.getIdSet.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
