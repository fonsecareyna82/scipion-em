import unittest
from unittest.mock import MagicMock, Mock, patch

from pwem.protocols.protocol_extract_coordinates import ProtExtractCoords


class _FakeMic:
    def __init__(self, objId, micName):
        self._objId = objId
        self._micName = micName

    def getObjId(self):
        return self._objId

    def getMicName(self):
        return self._micName

    def clone(self):
        return _FakeMic(self._objId, self._micName)


class _FakeMicsSet:
    def __init__(self, mics):
        self._mics = mics

    def getSamplingRate(self):
        return 1.0

    def loadAllProperties(self):
        pass

    def iterItems(self):
        return iter(self._mics)


class _FakeCoordinate:
    def __init__(self, micName, micId, x=0, y=0):
        self._micName = micName
        self._micId = micId
        self._x = x
        self._y = y

    def getMicName(self):
        return self._micName

    def getMicId(self):
        return self._micId

    def getPosition(self):
        return (self._x, self._y)


class _FakeParticle:
    def __init__(self, objId, coord):
        self._objId = objId
        self._coord = coord

    def getObjId(self):
        return self._objId

    def getCoordinate(self):
        return self._coord

    def getTransform(self):
        return None


class _FakeParticlesSet(dict):
    """dict keyed by objId - already supports __contains__/__getitem__
    matching Set membership/indexing semantics."""

    def __init__(self, items):
        super().__init__({p.getObjId(): p for p in items})

    def getSamplingRate(self):
        return 1.0

    def loadAllProperties(self):
        pass

    def getAlignment(self):
        import pwem.constants as emcts
        return emcts.ALIGN_NONE

    def getXDim(self):
        return 100


class _FakeOutputCoords:
    def __init__(self):
        self.appended = []

    def append(self, coord):
        self.appended.append(coord)

    def setBoxSize(self, size):
        pass


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

    def test_ExtractCoordinatesSkipsParticleNotYetVisibleAndKeepsProcessingOthers(self):
        # Regression test: getInputParticles()/getInputMicrographs()
        # resolve a Pointer whose cached value is never refreshed -
        # unlike loadInputs(), which already reopens fresh copies before
        # scheduling a particle here. Set.__getitem__(int) returns None
        # (not a raise) for a missing row, but indexing straight into
        # appendCoordFromParticle would still crash. A particle not yet
        # visible must be skipped (and logged) instead, while the rest
        # of the batch is still processed.
        protocol = ProtExtractCoords()
        protocol.streamingModeOn = True
        protocol.applyShifts = False
        protocol.warning = Mock()
        protocol.error = Mock()

        goodCoord = _FakeCoordinate('mic1', 1)
        goodPart = _FakeParticle(1, goodCoord)

        inMics = _FakeMicsSet([_FakeMic(1, 'mic1')])
        inPart = _FakeParticlesSet([goodPart])  # particle 2 is missing

        protocol.getInputParticles = Mock(return_value=inPart)
        protocol.getInputMicrographs = Mock(return_value=inMics)
        protocol.getInputMicrographsPointer = Mock(return_value=MagicMock())

        outputCoords = _FakeOutputCoords()
        protocol._createSetOfCoordinates = Mock(return_value=outputCoords)

        result = protocol.extractCoordinates(partsIds=[1, 2])

        self.assertIs(result, outputCoords)
        self.assertEqual(1, len(outputCoords.appended))
        protocol.warning.assert_called_once()

    def test_ExtractCoordinatesSkipsParticleThatFailsToExtractAndKeepsProcessingOthers(self):
        # Regression test: a single corrupted particle (e.g. missing
        # coordinate) must not crash the whole batch (and hence the
        # whole protocol via pyworkflow's fail-on-any-exception step
        # boundary) - it must be skipped with a clear error while the
        # rest of the batch is still processed.
        protocol = ProtExtractCoords()
        protocol.streamingModeOn = True
        protocol.applyShifts = False
        protocol.warning = Mock()
        protocol.error = Mock()

        class _BadCoordParticle(_FakeParticle):
            def getCoordinate(self):
                raise ValueError("corrupted coordinate")

        goodPart = _FakeParticle(2, _FakeCoordinate('mic1', 1))
        badPart = _BadCoordParticle(1, None)

        inMics = _FakeMicsSet([_FakeMic(1, 'mic1')])
        inPart = _FakeParticlesSet([badPart, goodPart])

        protocol.getInputParticles = Mock(return_value=inPart)
        protocol.getInputMicrographs = Mock(return_value=inMics)
        protocol.getInputMicrographsPointer = Mock(return_value=MagicMock())

        outputCoords = _FakeOutputCoords()
        protocol._createSetOfCoordinates = Mock(return_value=outputCoords)

        protocol.extractCoordinates(partsIds=[1, 2])

        self.assertEqual(1, len(outputCoords.appended))
        protocol.error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
