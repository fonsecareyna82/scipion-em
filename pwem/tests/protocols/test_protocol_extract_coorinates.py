import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock, Mock
from pwem.protocols import ProtExtractCoords
from pwem.tests.utils import getSoPartMock, getSoMMock, getMicNameFromId


class TestExtractCoordinates(unittest.TestCase):
    """ Tests extract coordinates protocol mocking some behaviour"""

    def test_ContinueKeepsOriginalStreamingModeAfterInputCloses(self):
        protocol = ProtExtractCoords()

        inputParticles = MagicMock()
        inputParticles.isStreamOpen.return_value = False
        protocol.getInputParticles = Mock(return_value=inputParticles)

        previousStreamingStep = MagicMock()
        previousStreamingStep.funcName = "extractCoordsStep"

        protocol.isContinued = Mock(return_value=True)
        protocol.loadSteps = Mock(return_value=[previousStreamingStep])
        protocol._getProcessedParticleIds = Mock(return_value={10})
        protocol.loadInputs = Mock(return_value=([11], True))
        protocol._insertNewSteps = Mock(return_value=[1])
        protocol._insertFunctionStep = Mock(return_value=2)

        protocol._insertAllSteps()

        self.assertTrue(
            protocol.streamingModeOn,
            "Continue must preserve the original streaming execution mode "
            "even if the input Set has closed since the previous run.",
        )
        protocol._getProcessedParticleIds.assert_called_once_with()
        protocol.loadInputs.assert_called_once_with()
        protocol._insertNewSteps.assert_called_once_with([11])

    def test_ProcessedParticleIdsAreRestoredFromOutputAndTemporarySets(self):
        protocol = ProtExtractCoords()

        outputCoordinates = MagicMock()
        outputCoordinates.getFileName.return_value = (
            "/tmp/coordinates.sqlite"
        )
        protocol.outputCoordinates = outputCoordinates

        persistedSet = MagicMock()
        persistedSet.getIdSet.return_value = {10, 11}

        tmpSetA = MagicMock()
        tmpSetA.getIdSet.return_value = {11, 12}

        tmpSetB = MagicMock()
        tmpSetB.getIdSet.return_value = {13}

        with patch(
            "pwem.protocols.protocol_extract_coordinates.emobj.SetOfCoordinates",
            side_effect=[persistedSet, tmpSetA, tmpSetB],
        ), patch(
            "pwem.protocols.protocol_extract_coordinates.pwutils.glob",
            return_value=[
                "/tmp/coordinates_tmp12.sqlite",
                "/tmp/coordinates_tmp13.sqlite",
            ],
        ):
            processedIds = protocol._getProcessedParticleIds()

        self.assertEqual({10, 11, 12, 13}, processedIds)
        persistedSet.close.assert_called_once_with()
        tmpSetA.close.assert_called_once_with()
        tmpSetB.close.assert_called_once_with()

    def test_LoadInputsDoesNotDropNewParticlesFromKnownMicrograph(self):
        protocol = ProtExtractCoords()
        protocol.micsDone = [1]
        protocol.partsDone = {10}

        mic = MagicMock()
        mic.getObjId.return_value = 1

        micsSet = MagicMock()
        micsSet.__iter__.return_value = iter([mic])
        micsSet.isStreamClosed.return_value = False

        def _particle(partId):
            particle = MagicMock()
            particle.getObjId.return_value = partId
            coordinate = MagicMock()
            coordinate.getMicId.return_value = 1
            particle.getCoordinate.return_value = coordinate
            return particle

        oldParticle = _particle(10)
        newParticle = _particle(11)

        partsSet = MagicMock()
        partsSet.__iter__.return_value = iter(
            [oldParticle, newParticle]
        )
        partsSet.getSize.return_value = 2
        partsSet.isStreamClosed.return_value = False

        inputMics = MagicMock()
        inputMics.getFileName.return_value = "/tmp/micrographs.sqlite"
        inputParts = MagicMock()
        inputParts.getFileName.return_value = "/tmp/particles.sqlite"

        protocol.getInputMicrographs = Mock(return_value=inputMics)
        protocol.getInputParticles = Mock(return_value=inputParts)

        with patch(
            "pwem.protocols.protocol_extract_coordinates.emobj.SetOfMicrographs",
            return_value=micsSet,
        ), patch(
            "pwem.protocols.protocol_extract_coordinates.emobj.SetOfParticles",
            return_value=partsSet,
        ):
            newParts, streamClosed = protocol.loadInputs()

        self.assertEqual([11], newParts)
        self.assertFalse(streamClosed)

    def test_TemporaryCoordinatesAlreadyPersistedAreNotCopiedAgain(self):
        protocol = ProtExtractCoords()
        protocol.finished = False
        protocol.streamClosed = False
        protocol.inputSize = 2
        protocol.outputSize = 0
        protocol._getFirstJoinStep = Mock(return_value=None)

        outputSet = MagicMock()
        outputSet.getIdSet.return_value = {7}
        temporarySet = MagicMock()
        temporarySet.getBoxSize.return_value = 128

        protocol._loadOutputSet = Mock(return_value=outputSet)
        protocol._updateOutputSet = Mock()

        with patch(
            "pwem.protocols.protocol_extract_coordinates.pwutils.glob",
            return_value=["/tmp/coordinates_tmp.sqlite"],
        ), patch(
            "pwem.protocols.protocol_extract_coordinates.emobj.SetOfCoordinates",
            return_value=temporarySet,
        ), patch(
            "pwem.protocols.protocol_extract_coordinates.pwutils.cleanPath",
        ):
            protocol._checkNewOutput()

        self.assertTrue(outputSet.copyItems.called)

        copyKwargs = outputSet.copyItems.call_args.kwargs
        self.assertIn(
            "itemSelectedCallback",
            copyKwargs,
            "Resume-safe tmp ingestion must filter coordinates that are "
            "already present in the persisted output Set.",
        )

        selector = copyKwargs["itemSelectedCallback"]

        alreadyPersisted = MagicMock()
        alreadyPersisted.getObjId.return_value = 7
        alreadyPersisted.isEnabled.return_value = True

        newCoordinate = MagicMock()
        newCoordinate.getObjId.return_value = 8
        newCoordinate.isEnabled.return_value = True

        self.assertFalse(selector(alreadyPersisted))
        self.assertTrue(selector(newCoordinate))

    def test_TemporaryCoordinatesAreRemovedOnlyAfterOutputIsPersisted(self):
        protocol = ProtExtractCoords()
        protocol.finished = False
        protocol.streamClosed = False
        protocol.inputSize = 1
        protocol.outputSize = 0
        protocol._getFirstJoinStep = Mock(return_value=None)

        outputSet = MagicMock()
        temporarySet = MagicMock()
        temporarySet.getBoxSize.return_value = 128

        events = []

        outputSet.copyItems.side_effect = (
            lambda *args, **kwargs: events.append("copy")
        )
        protocol._loadOutputSet = Mock(return_value=outputSet)
        protocol._updateOutputSet = Mock(
            side_effect=lambda *args, **kwargs: events.append("persist")
        )

        with patch(
            "pwem.protocols.protocol_extract_coordinates.pwutils.glob",
            return_value=["/tmp/coordinates_tmp.sqlite"],
        ), patch(
            "pwem.protocols.protocol_extract_coordinates.emobj.SetOfCoordinates",
            return_value=temporarySet,
        ), patch(
            "pwem.protocols.protocol_extract_coordinates.pwutils.cleanPath",
            side_effect=lambda *args, **kwargs: events.append("clean"),
        ):
            protocol._checkNewOutput()

        self.assertIn("persist", events)
        self.assertIn("clean", events)
        self.assertLess(
            events.index("persist"),
            events.index("clean"),
            "Temporary coordinate checkpoints must survive until the "
            "merged output Set has been persisted.",
        )

    def test_CheckNewInputReloadsLogicalSetsWhenPhysicalMtimeIsUnchanged(self):
        protocol = ProtExtractCoords()
        protocol.streamingModeOn = True
        protocol.lastCheck = datetime.now()
        protocol._getFirstJoinStep = unittest.mock.Mock(return_value=None)

        particles = unittest.mock.MagicMock()
        particles.getFileName.return_value = "/tmp/particles.sqlite"

        micrographs = unittest.mock.MagicMock()
        micrographs.getFileName.return_value = "/tmp/micrographs.sqlite"

        protocol.getInputParticles = unittest.mock.Mock(return_value=particles)
        protocol.getInputMicrographs = unittest.mock.Mock(return_value=micrographs)

        with patch(
            "pwem.protocols.protocol_extract_coordinates.os.path.getmtime",
            return_value=0,
        ), patch.object(
            protocol,
            "loadInputs",
            return_value=([], False),
        ) as loadInputs:
            protocol._checkNewInput()

        loadInputs.assert_called_once_with()

    def test_extractCoordinatesById(self):
        """ Tests ProtExtractCoords.extractCoordinates method using mic id for matching"""

        output = self._extractCoordinatesMocker(sop=getSoPartMock(name="inParts"),
                                                som=getSoMMock(name="inMics"))

        self.assertEqual(3, output.getSize(), "Wrong coordinates extraction")

        # Test missing mics
        output = self._extractCoordinatesMocker(sop=getSoPartMock(name="inPartsMissing"),
                                                som=getSoMMock(start=2, end=4, name="inMicsMissing"))

        self.assertEqual(2, output.getSize(), "Wrong coordinates extraction when missing mic ids")

    def test_extractCoordinatesByMicName(self):
        """ Tests ProtExtractCoords.extractCoordinates method using mic name for matching"""

        # Mic id wil range from 5-7
        som = getSoMMock(5, 7, "noIdButName")

        # Set micnames from 1-3
        for key, mic in som.items():
            mic.setMicName(getMicNameFromId(key - 4))

        output = self._extractCoordinatesMocker(sop=getSoPartMock(name="inPartsNoIdButNames"),
                                                som=som)

        self.assertEqual(3, output.getSize(), "Wrong coordinates extraction, matching by micname fails")

    def test_extractCoordinatesRescaling(self):
        """ Tests that extractCoordinates() rescales coordinate positions
        and box size by the particle/micrograph sampling-rate ratio - the
        same pwem-only logic test_workflow_xmipp.py used to exercise
        through a full Xmipp pipeline just to reach this method. """
        sop = getSoPartMock(name="inPartsScale")
        som = getSoMMock(name="inMicsScale")

        # particle sampling rate 2.0, mic sampling rate 4.0 -> scale 0.5
        sop.getSamplingRate.return_value = 2.0
        som.getSamplingRate.return_value = 4.0
        sop.getAlignment.return_value = None
        sop.getXDim.return_value = 100

        for particle in sop.__iter__.return_value:
            particle.getCoordinate().setPosition(20, 40)

        output = self._extractCoordinatesMocker(sop=sop, som=som)

        self.assertEqual(3, output.getSize())
        for coord in output.iterItems():
            self.assertEqual(10, coord.getX(), "X coordinate not rescaled")
            self.assertEqual(20, coord.getY(), "Y coordinate not rescaled")
        self.assertEqual(50, output.getBoxSize(), "Box size not rescaled")

    @staticmethod
    def _extractCoordinatesMocker(sop, som):
        extractionProt = ProtExtractCoords(workingDir="/tmp")

        # Patch getInputParticles
        with patch.object(ProtExtractCoords, 'getInputParticles',
                          return_value=sop) as mock_method:
            # Patch getInputMics
            with patch.object(ProtExtractCoords, 'getInputMicrographs',
                              return_value=som) as mock_method2:
                # Not in streaming
                extractionProt.streamingModeOn = False

                return extractionProt.extractCoordinates()


if __name__ == '__main__':
    unittest.main()
