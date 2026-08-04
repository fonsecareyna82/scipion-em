import unittest
from unittest.mock import patch
from pwem.protocols import ProtExtractCoords
from pwem.tests.utils import getSoPartMock, getSoMMock, getMicNameFromId


class TestExtractCoordinates(unittest.TestCase):
    """ Tests extract coordinates protocol mocking some behaviour"""

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
