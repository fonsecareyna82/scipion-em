# **************************************************************************
# *
# * Authors:     J.M. De la Rosa Trevin (jmdelarosa@cnb.csic.es)
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

import pyworkflow.utils as pwutils
import pyworkflow.protocol.constants as pwcts
import pyworkflow.protocol.params as params

from pwem import Domain

from .images import ProtImportImages

# Capability = 'import': plugins self-register an ImportCapabilityProvider
# (pyworkflow.capability) targeting this protocol's class name instead of
# pwem hardcoding a fixed IMPORT_FROM_* list/dispatch. See
# scipion-pyworkflow's .ai/capability-providers.md for the contract, and
# .import_providers for the pwem-native providers covering formats whose
# plugin hasn't migrated to self-registering yet.


class ProtImportParticles(ProtImportImages):
    """Protocol to import a set of particles to the project"""
    _label = 'import particles'
    _outputClassName = 'SetOfParticles'

    # Shadows ProtImportFiles.IMPORT_FROM_FILES (int 0) with the string key
    # importFrom actually holds now (KeyedEnumParam, not EnumParam). This
    # is deliberate, not incidental: every inherited comparison against
    # self.IMPORT_FROM_FILES (base.py's own _validate, images.py's
    # _validate) then keeps working unmodified through normal attribute
    # resolution. The two inherited hooks that instead *format* it with
    # %d (base.py's default _getFilesCondition, images.py's
    # _acquisitionWizardCondition) are overridden below.
    IMPORT_FROM_FILES = 'files'

    def _getImportProviders(self):
        """ Available (installed) import capability providers registered
        for this protocol's class, sorted by KEY for a stable menu order. """
        providers = Domain.findCapabilityProviders('import', self.getClass())
        available = [p for p in providers if p.isAvailable()]
        return sorted(available, key=lambda p: p.KEY)

    def _getImportProviderByKey(self, key):
        for provider in self._getImportProviders():
            if provider.KEY == key:
                return provider
        return None

    def _getImportFromParamClass(self):
        return params.KeyedEnumParam

    def _getImportChoices(self):
        """ Return a list of possible choices from which the import can be
        done: 'files', plus one entry per available import capability
        provider registered for this protocol (usually package formats
        such as xmipp3, eman2, relion, or a self-registering plugin like
        cryoSPARC). """
        choices = ProtImportImages._getImportChoices(self)
        choices += [(p.KEY, p.LABEL) for p in self._getImportProviders()]
        return choices

    def _getFilesCondition(self):
        return "(importFrom == '%s')" % self.IMPORT_FROM_FILES

    def _acquisitionWizardCondition(self):
        return "importFrom != '%s'" % self.IMPORT_FROM_FILES

    def _defineImportParams(self, form):
        """
        Import files from any available import capability provider
        (emx, xmipp3, relion, scipion, cryosparc, ... -- whatever is
        actually installed and registered).
        """
        providers = self._getImportProviders()

        param = form.getParam('importFrom')
        # Customize the help of this parameter with specific information
        # of the import particles
        param.help.set(
            "You can import particles directly from the binary "
            "files, or import from other packages formats.\n"
            "Currently, we can import from: %s"
            % ', '.join(p.LABEL for p in providers))

        for provider in providers:
            condition = "(importFrom == '%s')" % provider.KEY
            provider.defineParams(form, condition)

    def _defineAcquisitionParams(self, form):
        group = ProtImportImages._defineAcquisitionParams(self, form)
        group.addParam('samplingRate', params.FloatParam,
                       label=pwutils.Message.LABEL_SAMP_RATE)

    def _insertAllSteps(self):
        importFrom = self.importFrom.get()
        provider = self._getImportProviderByKey(importFrom)

        if provider is None:
            ProtImportImages._insertAllSteps(self)
        else:
            self.importFilePath = provider.getFilePath(self)
            self._insertFunctionStep('importParticlesStep', importFrom,
                                     self.importFilePath)

    def setSamplingRate(self, imgSet):
        imgSet.setSamplingRate(self.samplingRate.get())

    def importParticlesStep(self, importFrom, *args):
        provider = self._getImportProviderByKey(importFrom)
        provider.importFrom(self)

        # getEnumText() assumes a positional-index value (plain EnumParam);
        # importFrom is a KeyedEnumParam (string value) here, so look the
        # label up through it directly instead.
        importFromLabel = self._definition.getParam('importFrom').getChoiceLabel(importFrom)
        summary = "Import from *%s* file:\n" % importFromLabel
        summary += self.importFilePath + '\n'

        if self.hasAttribute('outputParticles'):
            particles = self.outputParticles
            summary += ' Particles: *%d* ' % particles.getSize()
            summary += ('(ctf=%s, alignment=%s, phaseFlip=%s)\n'
                        % (particles.hasCTF(), particles.getAlignment(),
                           particles.isPhaseFlipped()))

        # EMX files can contain only Coordinates information
        if self.hasAttribute('outputCoordinates'):
            summary += '   Coordinates: *%d* \n' % (self.outputCoordinates.getSize())

        # EMX files can contain only Coordinates information
        if self.hasAttribute('outputMicrographs'):
            summary += '   Micrographs: *%d* \n' % (self.outputMicrographs.getSize())

        if self.copyFiles:
            summary += '\n_WARNING_: Binary files copied into project (extra disk space)'

        self.summaryVar.set(summary)

    def _validateFileExtension(self, provider):
        """ Simple check about the expected file extension. """
        extensions = provider.FILE_EXTENSIONS
        if extensions and not any(
                self.importFilePath.endswith(ext) for ext in extensions):
            return ["Expected *%s* file extension for importing from *%s*" %
                    (' or '.join(extensions), provider.LABEL)]
        return []

    def _validate(self):
        importFrom = self.importFrom.get()
        provider = self._getImportProviderByKey(importFrom)

        if provider is None:
            return ProtImportImages._validate(self)

        self.importFilePath = provider.getFilePath(self)
        errors = self._validateFileExtension(provider)
        if errors:
            return errors
        return provider.validate(self)

    def _summary(self):
        if self.importFrom == self.IMPORT_FROM_FILES:
            return ProtImportImages._summary(self)
        else:
            return [self.summaryVar.get('')]


class ProtImportAverages(ProtImportParticles):
    """Protocol to import a set of averages to the project"""
    _label = 'import averages'
    _outputClassName = 'SetOfAverages'

    def _getImportChoices(self):
        """ Return a list of possible choices
        from which the import can be done.
        (usually packages formas such as: xmipp3, eman2, relion...etc.
        """
        choices = ProtImportImages._getImportChoices(self)
        return choices

    def _defineAcquisitionParams(self, form):
        form.addParam('samplingRate', params.FloatParam, default=1.,
                      label=pwutils.Message.LABEL_SAMP_RATE)
        group = ProtImportImages._defineAcquisitionParams(self, form)
        group.expertLevel.set(pwcts.LEVEL_ADVANCED)
