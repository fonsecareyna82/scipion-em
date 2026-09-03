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
Coverage for ProtImportParticles' CapabilityProvider-driven import-from
menu -- exercised entirely with fake providers, so it never depends on
whichever real plugins (xmipp3, relion, ...) happen to be installed in the
environment running these tests. See scipion-pyworkflow's
.ai/capability-providers.md for the contract, and import_providers.py for
the real (pwem-native) providers this same mechanism drives in production.
"""
import pytest

import pyworkflow.protocol.params as params
from pyworkflow.capability import ImportCapabilityProvider
# ProtImportParticles resolves providers through pwem's own Domain
# subclass (`from pwem import Domain`), not pyworkflow.plugin.Domain
# directly -- Domain._discoverCapabilityProviders does `cls._capabilityProviders
# = providers` (full reassignment), which shadows the attribute on
# whichever concrete Domain subclass first triggers real discovery. Once
# any other test in the suite has done that for pwem.Domain, patching the
# base pyworkflow.plugin.Domain class stops being visible here -- so these
# fixtures must patch the same subclass production code actually uses.
from pwem import Domain
from pwem.protocols import ProtImportParticles
from pwem.protocols.protocol_import.import_providers import (
    _PluginProbedImportProvider,
)


class _FakeAvailableProvider(ImportCapabilityProvider):
    TARGET_PROTOCOLS = ['ProtImportParticles']
    KEY = 'fakefmt'
    LABEL = 'Fake Format'
    FILE_EXTENSIONS = ['fmt']

    def __init__(self):
        self.importedFor = None
        self.validatedFor = None

    def defineParams(self, form, condition):
        form.addParam('fakeFmtFile', params.FileParam, condition=condition,
                      label='Fake format file')

    def getFilePath(self, protocol):
        return protocol.fakeFmtFile.get('').strip()

    def validate(self, protocol):
        self.validatedFor = protocol
        return []

    def importFrom(self, protocol):
        self.importedFor = protocol


class _FakeUnavailableProvider(ImportCapabilityProvider):
    TARGET_PROTOCOLS = ['ProtImportParticles']
    KEY = 'notinstalled'
    LABEL = 'Not installed format'

    def isAvailable(self):
        return False

    def defineParams(self, form, condition):
        form.addParam('shouldNeverAppear', params.FileParam, condition=condition)

    def importFrom(self, protocol):
        raise AssertionError('must never be dispatched to')


class _FakeUnrelatedTargetProvider(ImportCapabilityProvider):
    """ Targets a different protocol -- must never leak into
    ProtImportParticles' menu. """
    TARGET_PROTOCOLS = ['ProtImportMovies']
    KEY = 'unrelated'
    LABEL = 'Unrelated'

    def defineParams(self, form, condition):
        form.addParam('shouldNeverAppearEither', params.FileParam, condition=condition)


@pytest.fixture
def _fakeProviders(monkeypatch):
    providers = {
        'fakefmt': _FakeAvailableProvider(),
        'notinstalled': _FakeUnavailableProvider(),
        'unrelated': _FakeUnrelatedTargetProvider(),
    }
    monkeypatch.setattr(Domain, '_capabilityProviders', providers)
    monkeypatch.setattr(Domain, '_capabilityProvidersLoaded', True)
    return providers


def test_onlyAvailableMatchingProvidersReachTheChoiceList(_fakeProviders):
    prot = ProtImportParticles()
    choices = prot._definition.getParam('importFrom').choices

    assert ('fakefmt', 'Fake Format') in choices
    assert not any(key == 'notinstalled' for key, _ in choices)
    assert not any(key == 'unrelated' for key, _ in choices)
    assert ('files', 'files') in choices


def test_defaultChoiceIsFiles(_fakeProviders):
    prot = ProtImportParticles()
    assert prot.importFrom.get() == 'files'


def test_providerFieldOnlyRendersUnderItsOwnCondition(_fakeProviders):
    selected = ProtImportParticles(importFrom='fakefmt', fakeFmtFile='/tmp/x.fmt')
    assert selected._definition.evalParamCondition('fakeFmtFile') is True

    notSelected = ProtImportParticles(importFrom='files')
    assert notSelected._definition.evalParamCondition('fakeFmtFile') is False


def test_unavailableProviderFieldIsNeverDefinedAtAll(_fakeProviders):
    # Unlike the legacy hardcoded elif chain (every format's fields were
    # always defined, just gated by condition=, regardless of whether the
    # underlying plugin was installed), an unavailable provider's
    # defineParams() is never even called -- its fields don't clutter the
    # form at all, not just stay hidden.
    prot = ProtImportParticles(importFrom='files')
    assert not prot._definition.hasParam('shouldNeverAppear')
    assert not prot._definition.hasParam('shouldNeverAppearEither')


def test_insertAllStepsDispatchesToMatchingProvider(_fakeProviders):
    prot = ProtImportParticles(importFrom='fakefmt', fakeFmtFile='/tmp/x.fmt')
    prot._insertAllSteps()

    assert prot.importFilePath == '/tmp/x.fmt'
    assert len(prot._steps) == 1
    assert prot._steps[0].funcName == 'importParticlesStep'


def test_importParticlesStepDispatchesToProviderImportFrom(_fakeProviders):
    provider = Domain._capabilityProviders['fakefmt']
    prot = ProtImportParticles(importFrom='fakefmt', fakeFmtFile='/tmp/x.fmt')
    prot.importFilePath = '/tmp/x.fmt'

    prot.importParticlesStep('fakefmt')

    assert provider.importedFor is prot


def test_validateRunsExtensionCheckThenProviderValidate(_fakeProviders):
    provider = Domain._capabilityProviders['fakefmt']
    prot = ProtImportParticles(importFrom='fakefmt', fakeFmtFile='/tmp/x.fmt')

    errors = prot._validate()

    assert errors == []
    assert provider.validatedFor is prot


def test_validateRejectsWrongExtensionWithoutCallingProvider(_fakeProviders):
    provider = Domain._capabilityProviders['fakefmt']
    prot = ProtImportParticles(importFrom='fakefmt', fakeFmtFile='/tmp/x.wrongext')

    errors = prot._validate()

    assert len(errors) == 1
    assert 'fmt' in errors[0]
    assert provider.validatedFor is None  # never reached


def test_pluginProbedProviderIsUnavailableWhenModuleMissing():
    class _Wrapper(_PluginProbedImportProvider):
        TARGET_PROTOCOLS = ['ProtImportParticles']
        KEY = 'wrapper'
        LABEL = 'Wrapper'
        PLUGIN_MODULE = 'this_module_definitely_does_not_exist_anywhere'

    assert _Wrapper().isAvailable() is False


def test_pluginProbedProviderDefaultsAvailableWithoutAModule():
    class _NoModule(_PluginProbedImportProvider):
        TARGET_PROTOCOLS = ['ProtImportParticles']
        KEY = 'nomodule'
        LABEL = 'No module'

    assert _NoModule().isAvailable() is True
