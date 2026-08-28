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

import os
import tempfile
import unittest

import numpy as np
from PIL import Image as PILImage

from pwem import emlib
from pwem.protocols import ProtAlignMovies


class TestComputeThumbnail(unittest.TestCase):
    """ ProtAlignMovies.computeThumbnail() used to shell out to the eman2
    plugin's e2proc2d.py just to mean-shrink and rescale an image - see
    .ai/roadmap.md. Now done in-process with numpy/PIL, no plugin needed.
    """

    def setUp(self):
        self.tmpDir = tempfile.mkdtemp()
        self.inputFn = os.path.join(self.tmpDir, "mic.mrc")

        h, w = 90, 120
        data = (np.linspace(0, 1, h)[:, None] * np.linspace(0, 1, w)[None, :]
               * 1000).astype(np.float32)
        data += np.random.default_rng(0).normal(0, 20, (h, w)).astype(np.float32)

        img = emlib.Image()
        img.setDataType(emlib.DT_FLOAT)
        img.setData(data.reshape(1, 1, h, w))
        img.write(self.inputFn)

    def test_computesThumbnailWithoutAnyPlugin(self):
        prot = ProtAlignMovies(workingDir=self.tmpDir)

        outputFn = prot.computeThumbnail(self.inputFn, scaleFactor=6)

        self.assertEqual(outputFn, prot.getThumbnailFn(self.inputFn))
        self.assertTrue(os.path.exists(outputFn))

        thumb = PILImage.open(outputFn)
        self.assertEqual(thumb.size, (120 // 6, 90 // 6))

        thumbData = np.array(thumb)
        self.assertGreater(thumbData.std(), 0,
                           "Thumbnail should not be blank/constant")

    def test_respectsCustomOutputFn(self):
        prot = ProtAlignMovies(workingDir=self.tmpDir)
        customOutputFn = os.path.join(self.tmpDir, "custom.png")

        outputFn = prot.computeThumbnail(self.inputFn, scaleFactor=3,
                                         outputFn=customOutputFn)

        self.assertEqual(outputFn, customOutputFn)
        self.assertTrue(os.path.exists(customOutputFn))

        thumb = PILImage.open(customOutputFn)
        self.assertEqual(thumb.size, (120 // 3, 90 // 3))


if __name__ == '__main__':
    unittest.main()
