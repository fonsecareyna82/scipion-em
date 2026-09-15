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
from concurrent.futures import ThreadPoolExecutor, as_completed

import mrcfile
import numpy as np

from pwem.emlib.image.image_readers import ImageReadersRegistry, STKImageReader


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


def _writeStkStack(path, images, offset=1024):
    """
    Builds a minimal synthetic Spider/Xmipp .stk stack file on disk, laid
    out the way STKImageReader expects: a main `offset`-byte header, then
    one `offset`-byte per-image header immediately before each image's raw
    float32 pixel data (see STKImageReader._readHeader/_readImage).
    """
    nImages = len(images)
    nColumns = images[0].shape[0]

    header = np.zeros(256, dtype=np.float32)
    header[0] = 1  # n_slices
    header[1] = nColumns  # n_rows / img_size
    header[11] = nColumns  # n_columns
    header[20] = 1.0  # sampling rate
    header[21] = offset  # per-record offset
    header[25] = nImages  # n_images

    with open(path, "wb") as f:
        f.write(header.tobytes())
        for img in images:
            f.write(b"\x00" * offset)
            f.write(img.astype(np.float32).tobytes())


class TestStkImageReader(unittest.TestCase):

    def testOpenSliceAndOpenMatchExpectedPixels(self):
        with tempfile.TemporaryDirectory() as tmpDir:
            fileName = os.path.join(tmpDir, "particles.stk")
            rng = np.random.default_rng(0)
            images = [rng.random((16, 16)).astype(np.float32) for _ in range(5)]
            _writeStkStack(fileName, images)

            dims = STKImageReader.getDimensions(fileName)
            self.assertEqual(dims, (16, 16, 1, 5))

            for index, expected in enumerate(images, start=1):
                np.testing.assert_allclose(
                    STKImageReader.openSlice(fileName, index), expected,
                )

            full = STKImageReader.open(fileName)
            self.assertEqual(full.shape, (5, 16, 16))
            for index, expected in enumerate(images):
                np.testing.assert_allclose(full[index], expected)

    def testConcurrentOpenSliceCallsDoNotCorruptEachOther(self):
        # Regression test: STKImageReader used to keep its open file handle
        # and parsed header as *class* attributes (cls.stk_handler,
        # cls.header_info, ...), shared by every call regardless of thread.
        # Two concurrent openSlice calls would race on that shared handle's
        # seek()+read(), each reading from wherever the OTHER call had just
        # seeked to -- silently returning the wrong image, or occasionally
        # a short/empty read. Reading many slices from many threads at once
        # must return exactly the same pixels as reading them one at a time.
        with tempfile.TemporaryDirectory() as tmpDir:
            fileName = os.path.join(tmpDir, "particles.stk")
            rng = np.random.default_rng(1)
            images = [rng.random((24, 24)).astype(np.float32) for _ in range(20)]
            _writeStkStack(fileName, images)

            def readSlice(index):
                return index, STKImageReader.openSlice(fileName, index)

            requests = [i for i in range(1, len(images) + 1) for _ in range(4)]

            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(readSlice, i) for i in requests]
                for future in as_completed(futures):
                    index, image = future.result()
                    np.testing.assert_array_equal(
                        image, images[index - 1],
                        err_msg=f"Concurrent read of slice {index} returned the wrong image",
                    )