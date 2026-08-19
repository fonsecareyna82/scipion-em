# ******************************************************************************
# *
# * Authors:     Yunior C. Fonseca Reyna
# *
# * Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
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
# ******************************************************************************
import os
import tempfile
import unittest

import mrcfile
import numpy as np

from pwem.emlib.image.image_readers import ImageReadersRegistry


class TestMrcImageReader(unittest.TestCase):

    def testRegistryOpensMrcReadOnly(self):
        with tempfile.TemporaryDirectory() as tmpDir:
            fileName = os.path.join(tmpDir, "volume.mrc")
            expected = np.arange(
                60,
                dtype=np.float32,
            ).reshape((3, 4, 5))

            with mrcfile.new(fileName, overwrite=True) as mrc:
                mrc.set_data(expected)

            mtimeBefore = os.stat(fileName).st_mtime_ns

            ImageReadersRegistry._openInternal.cache_clear()

            imageStack = ImageReadersRegistry.open(fileName)
            data = np.asarray(imageStack.getImages())

            mtimeAfter = os.stat(fileName).st_mtime_ns

            np.testing.assert_array_equal(data, expected)
            self.assertFalse(data.flags.writeable)
            self.assertEqual(mtimeBefore, mtimeAfter)