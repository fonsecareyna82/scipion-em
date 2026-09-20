import unittest
from unittest.mock import MagicMock, Mock, patch

from pwem.protocols.protocol_import.images import ProtImportImages


class TestImportStreamingResumeSafety(unittest.TestCase):

    def test_ContinueClearsStaleStopMarkerWithEmptyOutputSet(self):
        protocol = ProtImportImages()
        protocol.isContinued = Mock(return_value=True)

        outputSet = MagicMock()
        outputSet.getSize.return_value = 0
        outputSet.getFileName.return_value = "/tmp/micrographs.sqlite"
        outputSet.getAcquisition.return_value = MagicMock()
        protocol._getOutputSet = Mock(return_value=outputSet)

        protocol._getStopStreamingFilename = Mock(
            return_value="/tmp/STOP_STREAMING.TXT"
        )
        protocol.stopStreamingFileExists = Mock(
            side_effect=[True, False]
        )

        protocol.haveDataBeenPhaseFlipped = MagicMock()
        protocol.haveDataBeenPhaseFlipped.get.return_value = False
        protocol.fillAcquisition = Mock()
        protocol.setSamplingRate = Mock()
        protocol._getOutputName = Mock(return_value="outputMicrographs")
        protocol.getCopyOrLink = Mock(return_value=Mock())
        protocol.iterNewInputFiles = Mock(return_value=iter(()))
        protocol.getFileNamesList = Mock(return_value=[])
        protocol._updateOutputSet = Mock()
        protocol._cleanUp = Mock()
        protocol._checkStacks = False

        protocol.dataStreaming = True
        protocol.timeout = MagicMock()
        protocol.timeout.toSeconds.return_value = 0
        protocol.fileTimeout = MagicMock()
        protocol.fileTimeout.toSeconds.return_value = 0

        with patch(
            "pwem.protocols.protocol_import.images.time.sleep",
            return_value=None,
        ), patch(
            "pwem.protocols.protocol_import.images.os.remove"
        ) as remove:
            protocol.importImagesStreamStep(
                "*.mrc",
                300,
                2.7,
                0.1,
                50000,
            )

        remove.assert_called_once_with("/tmp/STOP_STREAMING.TXT")

    def test_FillImportedFilesRestoresNonMicrographFiles(self):
        protocol = ProtImportImages()
        protocol.importedFiles = set()

        persistedParticle = MagicMock()
        persistedParticle.getFileName.return_value = (
            "/project/extra/already_imported.stk"
        )

        particleSet = MagicMock()
        particleSet.__iter__.return_value = iter([persistedParticle])

        protocol._fillImportedFiles(particleSet)

        self.assertEqual(
            {"already_imported.stk"},
            protocol.importedFiles,
            "Continue must rebuild importedFiles for non-micrograph "
            "image Sets from their persisted file names.",
        )

    def test_FillImportedFilesAcceptsEmptyOptionalSet(self):
        protocol = ProtImportImages()
        protocol.importedFiles = set()

        protocol._fillImportedFiles(None)

        self.assertEqual(set(), protocol.importedFiles)

    def test_IterNewInputFilesMatchesPersistedCleanFileName(self):
        from pwem.objects import SetOfMicrographsBase

        protocol = ProtImportImages()
        protocol.importedFiles = set()

        persistedMic = MagicMock()
        persistedMic.getMicName.return_value = "alreadyimported.mrc"
        persistedMic.getFileName.return_value = (
            "/project/extra/already imported.mrc"
        )

        micSet = MagicMock(spec=SetOfMicrographsBase)
        micSet.__iter__.return_value = iter([persistedMic])

        protocol._fillImportedFiles(micSet)
        protocol.iterFiles = Mock(
            return_value=iter([
                ("/data/already imported.mrc", 7),
            ])
        )
        protocol._getUniqueFileName = Mock(
            return_value="already imported.mrc"
        )
        protocol.isBlacklisted = Mock(return_value=False)

        self.assertEqual([], list(protocol.iterNewInputFiles()))

    def test_FillImportedFilesKeepsPartialStackRetryable(self):
        protocol = ProtImportImages()
        protocol.importedFiles = set()
        protocol.importedLocations = set()

        persistedParticle = MagicMock()
        persistedParticle.getFileName.return_value = (
            "/project/extra/particles.stk"
        )
        persistedParticle.getIndex.return_value = 1

        particleSet = MagicMock()
        particleSet.__iter__.return_value = iter([persistedParticle])

        protocol._fillImportedFiles(particleSet)

        self.assertNotIn(
            "particles.stk",
            protocol.importedFiles,
            "A partially persisted stack must remain retryable on Continue.",
        )
        self.assertIn(
            (1, "particles.stk"),
            protocol.importedLocations,
            "Persisted stack item locations must be reconstructed on Continue.",
        )

    def test_ContinueSkipsPersistedItemsInsidePartialStack(self):
        protocol = ProtImportImages()
        protocol.isContinued = Mock(return_value=True)
        protocol.dataStreaming = False
        protocol._checkStacks = True

        persistedParticle = MagicMock()
        persistedParticle.getFileName.return_value = (
            "/project/extra/particles.stk"
        )
        persistedParticle.getIndex.return_value = 1

        image = MagicMock()

        outputSet = MagicMock()
        outputSet.getSize.return_value = 1
        outputSet.__iter__.return_value = iter([persistedParticle])
        outputSet.getFileName.return_value = "/tmp/particles.sqlite"
        outputSet.getAcquisition.return_value = MagicMock()
        outputSet.ITEM_TYPE.return_value = image
        protocol._getOutputSet = Mock(return_value=outputSet)

        protocol.haveDataBeenPhaseFlipped = MagicMock()
        protocol.haveDataBeenPhaseFlipped.get.return_value = False
        protocol.fillAcquisition = Mock()
        protocol.setSamplingRate = Mock()
        protocol._getOutputName = Mock(return_value="outputParticles")
        protocol.getCopyOrLink = Mock(return_value=Mock())
        protocol._getExtraPath = Mock(
            return_value="/project/extra/particles.stk"
        )
        protocol.fileModified = Mock(return_value=False)
        protocol.iterNewInputFiles = Mock(
            side_effect=[
                iter([
                    (
                        "/data/particles.stk",
                        "particles.stk",
                        None,
                    )
                ]),
                iter(()),
            ]
        )
        protocol.stopStreamingFileExists = Mock(
            side_effect=[False, True]
        )
        protocol.getFileNamesList = Mock(return_value={})
        protocol._updateOutputSet = Mock()
        protocol._cleanUp = Mock()
        protocol._addImageToSet = Mock()
        protocol.debug = Mock()

        with patch(
            "pwem.protocols.protocol_import.images.time.sleep",
            return_value=None,
        ), patch(
            "pwem.protocols.protocol_import.images.ImageHandler"
        ) as imageHandler:
            imageHandler.return_value.getDimensions.return_value = (
                64,
                64,
                1,
                2,
            )

            protocol.importImagesStreamStep(
                "*.stk",
                300,
                2.7,
                0.1,
                50000,
            )

        image.setIndex.assert_called_once_with(2)
        self.assertEqual(1, protocol._addImageToSet.call_count)

    def test_ContinueReloadsAndEnablesAppendForEmptyOutputSet(self):
        protocol = ProtImportImages()
        protocol.isContinued = Mock(return_value=True)
        protocol.dataStreaming = False
        protocol._checkStacks = False

        outputSet = MagicMock()
        outputSet.getSize.return_value = 0
        outputSet.getFileName.return_value = "/tmp/empty.sqlite"
        outputSet.getAcquisition.return_value = MagicMock()
        outputSet.ITEM_TYPE.return_value = MagicMock()

        protocol._getOutputSet = Mock(return_value=outputSet)
        protocol.haveDataBeenPhaseFlipped = MagicMock()
        protocol.haveDataBeenPhaseFlipped.get.return_value = False
        protocol.fillAcquisition = Mock()
        protocol.setSamplingRate = Mock()
        protocol.getCopyOrLink = Mock(return_value=Mock())
        protocol._getOutputName = Mock(return_value="outputImages")
        protocol.iterNewInputFiles = Mock(return_value=iter(()))
        protocol.stopStreamingFileExists = Mock(
            side_effect=[False, True]
        )
        protocol.getFileNamesList = Mock(return_value={})
        protocol._updateOutputSet = Mock()
        protocol._cleanUp = Mock()
        protocol.debug = Mock()

        with patch(
            "pwem.protocols.protocol_import.images.time.sleep",
            return_value=None,
        ):
            protocol.importImagesStreamStep(
                "*.mrc",
                300,
                2.7,
                0.1,
                50000,
            )

        outputSet.loadAllProperties.assert_called_once_with()
        outputSet.enableAppend.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
