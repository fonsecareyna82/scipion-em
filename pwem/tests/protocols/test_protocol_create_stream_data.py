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

from pyworkflow.tests import BaseTest, setupTestProject

import pwem.protocols as emprot


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
