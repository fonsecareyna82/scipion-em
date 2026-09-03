# **************************************************************************
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
# **************************************************************************
"""
pwem-native ImportCapabilityProvider implementations for the particle-import
formats that don't (yet) self-register from their own plugin repos:
emx, xmipp3, relion, frealign (cistem), eman, and pwem's own local scipion
(.sqlite) format.

These are thin wrappers around exactly the same Domain.importFromPlugin(...)
calls ProtImportParticles.getImportClass() used to make inline -- no
conversion logic changed, only where the dispatch/registration lives. Once
a given plugin (e.g. scipion-em-xmipp) migrates to self-registering its own
provider (see scipion-em-cryosparc2 for the reference migration), its
wrapper here should be deleted, not kept alongside a duplicate.

Registered via the 'pyworkflow.capability_provider' entry-point group in
pyproject.toml. See scipion-pyworkflow's .ai/capability-providers.md for
the contract these implement.
"""
import pyworkflow.protocol.params as params
from pyworkflow.capability import ImportCapabilityProvider
from pyworkflow.plugin import Domain
import pwem.constants as emcts

PARTICLES_TARGETS = ['ProtImportParticles']


class _PluginProbedImportProvider(ImportCapabilityProvider):
    """ Shared availability probe for providers wrapping a plugin that
    isn't installed by default alongside pwem. """

    #: dotted plugin module to probe, e.g. 'xmipp3'
    PLUGIN_MODULE = None

    def isAvailable(self):
        if not self.PLUGIN_MODULE:
            return True
        return Domain.importFromPlugin(self.PLUGIN_MODULE, doRaise=False) is not None


class EmxParticlesImportProvider(_PluginProbedImportProvider):
    TARGET_PROTOCOLS = PARTICLES_TARGETS
    KEY = 'emx'
    LABEL = 'emx'
    FILE_EXTENSIONS = ['emx']
    PLUGIN_MODULE = 'emxlib'

    ALIGN_TYPE_LIST = [emcts.ALIGN_2D, emcts.ALIGN_3D, emcts.ALIGN_PROJ,
                       emcts.ALIGN_NONE]

    def defineParams(self, form, condition):
        form.addParam('emxFile', params.FileParam,
                      condition=condition,
                      label='Input EMX file',
                      help="Select the EMX file containing particles "
                           "information.\n See more about \n"
                           "[[http://i2pc.cnb.csic.es/emx][EMX format]]")

        form.addParam('alignType', params.EnumParam,
                      condition=condition,
                      default=0,
                      choices=self.ALIGN_TYPE_LIST,
                      label='Alignment Type',
                      help="Is this a 2D alignment, a 3D alignment or a set of projections")

    def getFilePath(self, protocol):
        return protocol.emxFile.get('').strip()

    def _buildImporter(self, protocol):
        EmxImport = Domain.importFromPlugin(
            'emxlib.convert', 'EmxImport',
            errorMsg='Emx is needed to import .emx files', doRaise=True)
        importFilePath = self.getFilePath(protocol)
        alignType = self.ALIGN_TYPE_LIST[protocol.alignType.get()]
        return EmxImport(protocol, importFilePath, alignType)

    def validate(self, protocol):
        return self._buildImporter(protocol).validateParticles()

    def importFrom(self, protocol):
        self._buildImporter(protocol).importParticles()


class Xmipp3ParticlesImportProvider(_PluginProbedImportProvider):
    TARGET_PROTOCOLS = PARTICLES_TARGETS
    KEY = 'xmipp3'
    LABEL = 'xmipp3'
    FILE_EXTENSIONS = ['xmd']
    PLUGIN_MODULE = 'xmipp3'

    def defineParams(self, form, condition):
        form.addParam('mdFile', params.FileParam,
                      condition=condition,
                      label='Particles metadata file',
                      help="Select the particles Xmipp metadata file.\n"
                           "It is usually a images.xmd file result\n"
                           "from Xmipp protocols execution.")

    def getFilePath(self, protocol):
        return protocol.mdFile.get('').strip()

    def _buildImporter(self, protocol):
        XmippImport = Domain.importFromPlugin(
            'xmipp3.convert', 'XmippImport',
            'Xmipp is needed to import .xmd files', doRaise=True)
        return XmippImport(protocol, protocol.mdFile.get())

    def validate(self, protocol):
        return self._buildImporter(protocol).validateParticles()

    def importFrom(self, protocol):
        self._buildImporter(protocol).importParticles()


class RelionParticlesImportProvider(_PluginProbedImportProvider):
    TARGET_PROTOCOLS = PARTICLES_TARGETS
    KEY = 'relion'
    LABEL = 'relion'
    FILE_EXTENSIONS = ['star']
    PLUGIN_MODULE = 'relion'

    def defineParams(self, form, condition):
        form.addParam('starFile', params.FileParam,
                      condition=condition,
                      label='Star file',
                      help="Select a *_data.star file from a\n"
                           "previous Relion execution."
                           "To detect if the input particles contains alignment "
                           "information, it is required to have the "
                           "optimiser.star file corresponding to the data.star")

        form.addParam('ignoreIdColumn', params.BooleanParam, default=False,
                      condition=condition,
                      label='Ignore ID column?',
                      help="Set this option to True to regenerate \n"
                           "the id's of the particles. By default \n"
                           "it is read from metadata file.        \n"
                           "This option can be useful when merging\n"
                           "different metadatas and id's are not  \n"
                           "longer unique.")

    def getFilePath(self, protocol):
        return protocol.starFile.get('').strip()

    def _buildImporter(self, protocol):
        RelionImport = Domain.importFromPlugin(
            'relion.convert', 'RelionImport',
            errorMsg='Relion is needed to import .star files', doRaise=True)
        return RelionImport(protocol, protocol.starFile.get())

    def validate(self, protocol):
        return self._buildImporter(protocol).validateParticles()

    def importFrom(self, protocol):
        self._buildImporter(protocol).importParticles()


class ScipionParticlesImportProvider(ImportCapabilityProvider):
    """ Imports from pwem's own local .sqlite Set format -- no external
    plugin dependency, always available. """
    TARGET_PROTOCOLS = PARTICLES_TARGETS
    KEY = 'scipion'
    LABEL = 'scipion'
    FILE_EXTENSIONS = ['sqlite']

    def defineParams(self, form, condition):
        form.addParam('sqliteFile', params.FileParam,
                      condition=condition,
                      label='Particles sqlite file',
                      help="Select the particles sqlite file.\n")

    def getFilePath(self, protocol):
        return protocol.sqliteFile.get('').strip()

    def _buildImporter(self, protocol):
        from .dataimport import ScipionImport
        return ScipionImport(protocol, self.getFilePath(protocol))

    def validate(self, protocol):
        return self._buildImporter(protocol).validateParticles()

    def importFrom(self, protocol):
        self._buildImporter(protocol).importParticles()


class FrealignParticlesImportProvider(_PluginProbedImportProvider):
    TARGET_PROTOCOLS = PARTICLES_TARGETS
    KEY = 'frealign'
    LABEL = 'frealign'
    FILE_EXTENSIONS = ['par']
    PLUGIN_MODULE = 'cistem'

    def defineParams(self, form, condition):
        form.addParam('frealignLabel', params.LabelParam,
                      condition=condition,
                      label='For Frealign you need to import both stack and .par files.')
        form.addParam('stackFile', params.FileParam,
                      condition=condition,
                      label='Stack file',
                      help="Select an stack file with the particles.")
        form.addParam('parFile', params.FileParam,
                      condition=condition,
                      label='Param file',
                      help="Select a Frealign .par file with the refinement information.")

    def getFilePath(self, protocol):
        return protocol.parFile.get('').strip()

    def _buildImporter(self, protocol):
        GrigorieffLabImportParticles = Domain.importFromPlugin(
            'cistem.convert', 'GrigorieffLabImportParticles',
            errorMsg='Cistem is needed to import .stk files', doRaise=True)
        return GrigorieffLabImportParticles(
            protocol, protocol.parFile.get(), protocol.stackFile.get())

    def validate(self, protocol):
        return self._buildImporter(protocol).validateParticles()

    def importFrom(self, protocol):
        self._buildImporter(protocol).importParticles()


class EmanParticlesImportProvider(_PluginProbedImportProvider):
    TARGET_PROTOCOLS = PARTICLES_TARGETS
    KEY = 'eman'
    LABEL = 'eman'
    FILE_EXTENSIONS = ['lst']
    PLUGIN_MODULE = 'eman2'

    def defineParams(self, form, condition):
        form.addParam('lstFile', params.FileParam,
                      condition=condition,
                      label='Lst file',
                      help='Select a *.lst set file from EMAN2 project.')

    def getFilePath(self, protocol):
        return protocol.lstFile.get('').strip()

    def _buildImporter(self, protocol):
        EmanImport = Domain.importFromPlugin(
            'eman2.convert', 'EmanImport', doRaise=True)
        return EmanImport(protocol, protocol.lstFile.get())

    def validate(self, protocol):
        return self._buildImporter(protocol).validateParticles()

    def importFrom(self, protocol):
        self._buildImporter(protocol).importParticles()
