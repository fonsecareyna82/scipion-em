# ***************************************************************************
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 3 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# *
# ***************************************************************************/

import unittest
from unittest.mock import MagicMock, patch

from pyworkflow.tests import BaseTest, setupTestProject

import pwem.protocols as emprot
from pwem.protocols.protocol_create_stream_data import SET_OF_COORDINATES



class TestCreateStreamResumeSafety(unittest.TestCase):

    def test_CheckNewItemsContinuesIdsFromPersistedOutput(self):
        protocol = emprot.ProtCreateStreamData(
            setof=emprot.SET_OF_RANDOM_MICROGRAPHS
        )
        protocol.counter = 0
        protocol.dictObj["/tmp/new_00008.xmp"] = True

        oldMic1 = MagicMock()
        oldMic1.getFileName.return_value = "/tmp/old_00004.xmp"
        oldMic1.getObjId.return_value = 4

        oldMic2 = MagicMock()
        oldMic2.getFileName.return_value = "/tmp/old_00007.xmp"
        oldMic2.getObjId.return_value = 7

        outputSet = MagicMock()
        outputSet.__iter__.return_value = iter([oldMic1, oldMic2])
        outputSet.getSize.return_value = 2

        _, newObj = protocol._checkNewItems(outputSet)

        self.assertTrue(newObj)
        outputSet.append.assert_called_once()
        appendedMic = outputSet.append.call_args.args[0]

        self.assertEqual(
            8,
            appendedMic.getObjId(),
            "Continue must allocate new object ids after the highest "
            "id already persisted in the output Set.",
        )
        self.assertEqual(8, protocol.counter)

    def test_CreateCoordinatesStepSkipsAlreadyPersistedCoordinates(self):
        protocol = emprot.ProtCreateStreamData(
            setof=SET_OF_COORDINATES
        )
        protocol.nDims = 2
        protocol.getTimeInterval = MagicMock(return_value=0)

        mic = MagicMock()
        micrographs = MagicMock()
        micrographs.__iter__.return_value = iter([mic])

        oldCoord = MagicMock()
        oldCoord.getObjId.return_value = 101
        newCoord = MagicMock()
        newCoord.getObjId.return_value = 102

        inputCoordinates = MagicMock()
        inputCoordinates.getMicrographs.return_value = micrographs
        inputCoordinates.iterCoordinates.return_value = iter(
            [oldCoord, newCoord]
        )

        protocol.inputCoordinates = MagicMock()
        protocol.inputCoordinates.get.return_value = inputCoordinates

        outputCoordinates = MagicMock()
        outputCoordinates.getIdSet.return_value = {101}
        protocol.outputCoordinates = outputCoordinates

        protocol.createCoordinatesStep(1)

        outputCoordinates.append.assert_called_once_with(newCoord)

    def test_CheckProcessedDataClosesCompleteSetOnRetryWithoutNewItems(self):
        protocol = emprot.ProtCreateStreamData(
            setof=emprot.SET_OF_RANDOM_MICROGRAPHS
        )
        protocol.nDims = 2
        protocol.nDim = MagicMock()
        protocol.nDim.get.return_value = 2

        outputSet = MagicMock()
        outputSet.getSize.return_value = 2
        outputSet.STREAM_CLOSED = 2

        protocol._checkNewItems = MagicMock(
            return_value=(outputSet, False)
        )
        protocol._updateOutput = MagicMock()

        with patch(
            "pwem.protocols.protocol_create_stream_data.emobj.SetOfMicrographs",
            return_value=outputSet,
        ):
            protocol._checkProcessedData()

        outputSet.setStreamState.assert_called_once_with(
            outputSet.STREAM_CLOSED
        )
        protocol._updateOutput.assert_called_once_with(outputSet)


class TestCreateStreamRandomMicrographs(BaseTest):
    """ ProtCreateStreamData's SET_OF_RANDOM_MICROGRAPHS mode generates its
    micrographs from scratch (a random image with a random CTF applied),
    needing no plugin or pre-existing input Set - see .ai/roadmap.md.
    """

    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)

    def test_createsRandomMicrographsWithoutAnyPlugin(self):
        prot = self.newProtocol(emprot.ProtCreateStreamData,
                                setof=emprot.SET_OF_RANDOM_MICROGRAPHS,
                                xDim=64,
                                yDim=64,
                                nDim=2,
                                samplingRate=4,
                                creationInterval=1)
        self.launchProtocol(prot)

        outputMics = getattr(prot, "outputMicrographs", None)
        self.assertIsNotNone(outputMics,
                             "No outputMicrographs was produced.")
        self.assertEqual(outputMics.getSize(), 2,
                         "outputMicrographs has the wrong size.")
        self.assertEqual(outputMics.getSamplingRate(), 4,
                         "outputMicrographs has the wrong sampling rate.")

        for mic in outputMics:
            self.assertTrue(mic.getFileName().endswith(".xmp"),
                            "Micrograph file was not written.")
