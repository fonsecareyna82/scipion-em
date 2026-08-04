# ***************************************************************************
# * Authors:    Marta Martinez (mmmtnez@cnb.csic.es)
# *             Roberto Marabini (roberto@cnb.csic.es)
# *
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
# ***************************************************************************/

# Import-only setup shared by test_workflow_modeling.py's Chimera/Coot/
# Refmac/EMRinger/Molprobity tests (all of which need those external
# tools). This part is pure pwem (ProtImportVolumes/ProtImportPdb) with no
# plugin dependency, so it lives here instead - moved out of workflows/ so
# it's collected and cleanly skipped (not silently excluded) via the
# dataset-skip-wrapper in pwem/tests/conftest.py until the
# 'model_building_tutorial' dataset is synced (see .ai/roadmap.md).

from pyworkflow.tests import BaseTest, DataSet, setupTestProject

import pwem.protocols as emprot


class TestImportBase(BaseTest):
    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        cls.dsModBuild = DataSet.getDataSet('model_building_tutorial')


class TestImportData(TestImportBase):
    """ Import map volumes and atomic structures(PDBx/mmCIF files)
    """

    def _importVolume(self):
        args = {'filesPath': self.dsModBuild.getFile('volumes/1ake_4-5A.mrc'),
                'samplingRate': 1.5,
                'setOrigCoord': False
                }
        protImportVol = self.newProtocol(emprot.ProtImportVolumes, **args)
        protImportVol.setObjLabel('import volume 1ake_4-5A\n with default '
                                  'origin\n')
        self.launchProtocol(protImportVol)
        volume = protImportVol.outputVolume
        return volume

    def _importVolume2(self):
        args = {'filesPath': self.dsModBuild.getFile('volumes/1ake_4-5A.mrc'),
                'samplingRate': 1.5,
                'setOrigCoord': True,
                'x': 11.994,
                'y': -7.881,
                'z': 10.91
                }
        protImportVol = self.newProtocol(emprot.ProtImportVolumes, **args)
        protImportVol.setObjLabel('import volume 1ake_4-5A\n set origin in 11 '
                                  '-7 10\n')
        self.launchProtocol(protImportVol)
        volume2 = protImportVol.outputVolume
        return volume2

    def _importVolume3(self):
        args = {'filesPath': self.dsModBuild.getFile(
            'volumes/emd_4116.map'),
            'samplingRate': 0.637,
            'setOrigCoord': False
        }
        protImportVol = self.newProtocol(emprot.ProtImportVolumes, **args)
        protImportVol.setObjLabel('import volume emd_4116\nwith default '
                                  'origin\n')
        self.launchProtocol(protImportVol)
        volume3 = protImportVol.outputVolume
        return volume3

    def _importStructurePDBWoVol(self):
        args = {'inputPdbData': emprot.ProtImportPdb.IMPORT_FROM_FILES,
                'pdbFile': self.dsModBuild.getFile(
                    'PDBx_mmCIF/1ake_start.pdb'),
                }
        protImportPDB = self.newProtocol(emprot.ProtImportPdb, **args)
        protImportPDB.setObjLabel('import pdb\n 1ake_start')
        self.launchProtocol(protImportPDB)
        structure1_PDB = protImportPDB.outputPdb
        return structure1_PDB

    def _importStructuremmCIFWoVol(self):
        args = {'inputPdbData': emprot.ProtImportPdb.IMPORT_FROM_FILES,
                'pdbFile': self.dsModBuild.getFile(
                    'PDBx_mmCIF/1ake_start.pdb.cif'),
                }
        protImportPDB = self.newProtocol(emprot.ProtImportPdb, **args)
        protImportPDB.setObjLabel('import mmCIF\n 1ake_start')
        self.launchProtocol(protImportPDB)
        structure1_mmCIF = protImportPDB.outputPdb
        self.assertTrue(structure1_mmCIF.getFileName())
        return structure1_mmCIF

    def _importStructurePDBWithVol(self):
        args = {'inputPdbData': emprot.ProtImportPdb.IMPORT_FROM_FILES,
                'pdbFile': self.dsModBuild.getFile(
                    'PDBx_mmCIF/1ake_start.pdb'),
                'inputVolume': self._importVolume()
                }
        protImportPDB = self.newProtocol(emprot.ProtImportPdb, **args)
        protImportPDB.setObjLabel('import pdb\n volume associated\n 1ake_start')
        self.launchProtocol(protImportPDB)
        structure2_PDB = protImportPDB.outputPdb
        self.assertTrue(structure2_PDB.getFileName())
        return structure2_PDB

    def _importStructuremmCIFWithVol(self):
        args = {'inputPdbData': emprot.ProtImportPdb.IMPORT_FROM_FILES,
                'pdbFile': self.dsModBuild.getFile('PDBx_mmCIF/'
                                                   '1ake_start.pdb.cif'),
                'inputVolume': self._importVolume()
                }
        protImportPDB = self.newProtocol(emprot.ProtImportPdb, **args)
        protImportPDB.setObjLabel('import mmCIF\n volume associated\n '
                                  '1ake_start')
        self.launchProtocol(protImportPDB)
        structure2_mmCIF = protImportPDB.outputPdb
        self.assertTrue(structure2_mmCIF.getFileName())
        return structure2_mmCIF

    def _importMut1StructurePDBWoVol(self):
        args = {'inputPdbData': emprot.ProtImportPdb.IMPORT_FROM_FILES,
                'pdbFile': self.dsModBuild.getFile(
                    'PDBx_mmCIF/1ake_mut1.pdb'),
                }
        protImportPDB = self.newProtocol(emprot.ProtImportPdb, **args)
        protImportPDB.setObjLabel('import pdb\n 1ake_mut1')
        self.launchProtocol(protImportPDB)
        structure3_PDB = protImportPDB.outputPdb
        return structure3_PDB

    def _importMut2StructurePDBWoVol(self):
        args = {'inputPdbData': emprot.ProtImportPdb.IMPORT_FROM_FILES,
                'pdbFile': self.dsModBuild.getFile(
                    'PDBx_mmCIF/1ake_mut2.pdb'),
                }
        protImportPDB = self.newProtocol(emprot.ProtImportPdb, **args)
        protImportPDB.setObjLabel('import pdb\n 1ake_mut2')
        self.launchProtocol(protImportPDB)
        structure4_PDB = protImportPDB.outputPdb
        return structure4_PDB

    def _importCootStructureWoVol(self):
        args = {'inputPdbData': emprot.ProtImportPdb.IMPORT_FROM_FILES,
                'pdbFile': self.dsModBuild.getFile(
                    'PDBx_mmCIF/scipionOut0001.pdb')
                }
        protImportPDB = self.newProtocol(emprot.ProtImportPdb, **args)
        protImportPDB.setObjLabel('import pdb\n coot')
        self.launchProtocol(protImportPDB)
        structureCoot_PDB = protImportPDB.outputPdb
        self.assertTrue(structureCoot_PDB.getFileName())
        return structureCoot_PDB

    def _importStructurePDBWoVol2(self):
        args = {'inputPdbData': emprot.ProtImportPdb.IMPORT_FROM_FILES,
                'pdbFile': self.dsModBuild.getFile(
                    'PDBx_mmCIF/3i3e_fitted.pdb'),
                }
        protImportPDB = self.newProtocol(emprot.ProtImportPdb, **args)
        protImportPDB.setObjLabel('import pdb\n 3i3e_fitted')
        self.launchProtocol(protImportPDB)
        structure5_PDB = protImportPDB.outputPdb
        return structure5_PDB

    def _importStructureMolProbity1(self):
        args = {'inputPdbData': emprot.ProtImportPdb.IMPORT_FROM_FILES,
                'pdbFile': self.dsModBuild.getFile(
                    'PDBx_mmCIF/jlv_chimeraOut0001.pdb'),
                }
        protImportPDB = self.newProtocol(emprot.ProtImportPdb, **args)
        protImportPDB.setObjLabel('import pdb\n jlv_chimeraOut0001')
        self.launchProtocol(protImportPDB)
        structure6_PDB = protImportPDB.outputPdb
        return structure6_PDB

    def _importStructureMolProbity2(self):
        args = {'inputPdbData': emprot.ProtImportPdb.IMPORT_FROM_FILES,
                'pdbFile': self.dsModBuild.getFile(
                    'PDBx_mmCIF/jlv_cootOut0016.pdb'),
                }
        protImportPDB = self.newProtocol(emprot.ProtImportPdb, **args)
        protImportPDB.setObjLabel('import pdb\n jlv_cootOut0016')
        self.launchProtocol(protImportPDB)
        structure7_PDB = protImportPDB.outputPdb
        return structure7_PDB

    def _createExtraCommandLine(self, x, y, z, label=None):
        if label is not None:
            writeLine = 'scipion_write(0, "%s")' % label
        else:
            writeLine = 'scipion_write()'

        if x != 0. or y != 0. or z != 0.:
            return """translate_molecule_by(0, %f, %f, %f)
fit_molecule_to_map_by_random_jiggle(0,7000,2)
%s
coot_real_exit(0)
""" % (x, y, z, writeLine)
        else:
            return """%s
coot_real_exit(0)
""" % writeLine

    def testImportVolumeOnly(self):
        """ Smoke-test the pwem-only import path used by every subclass
        of this test, without needing Chimera/Coot/Refmac/Phenix. """
        volume = self._importVolume()
        self.assertIsNotNone(volume, "Volume import failed.")
        self.assertTrue(volume.getFileName())

    def testImportStructurePDBWithoutVolume(self):
        structure = self._importStructurePDBWoVol()
        self.assertIsNotNone(structure, "PDB import failed.")
        self.assertTrue(structure.getFileName())
