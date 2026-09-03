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
Coverage for pwem's native import-capability-provider wrappers
(pwem/protocols/protocol_import/import_providers.py) -- these are thin
adapters around the exact same Domain.importFromPlugin(...) calls the old
getImportClass() elif chain made, so what needs protecting here is the
mechanical mapping (module/class names, which field holds the file path,
declared extensions), not the wrapped plugins' own conversion logic (that
stays untouched, verified separately whenever the real plugin is
installed -- see test_protocol_import_particles_providers.py's
end-to-end manual check against real xmipp3 for one live example).
"""
import pyworkflow.protocol.params as params
from pwem.protocols import ProtImportParticles
from pwem.protocols.protocol_import import import_providers as ip

ALL_PROVIDERS = [
    ip.EmxParticlesImportProvider,
    ip.Xmipp3ParticlesImportProvider,
    ip.RelionParticlesImportProvider,
    ip.ScipionParticlesImportProvider,
    ip.FrealignParticlesImportProvider,
    ip.EmanParticlesImportProvider,
]


def test_allProvidersDeclareRequiredMetadata():
    keys = set()
    for providerClass in ALL_PROVIDERS:
        assert providerClass.TARGET_PROTOCOLS == ['ProtImportParticles']
        assert providerClass.KEY
        assert providerClass.LABEL
        keys.add(providerClass.KEY)

    assert keys == {'emx', 'xmipp3', 'relion', 'scipion', 'frealign', 'eman'}


def test_pluginBackedProvidersDeclareAPluginModuleToProbe():
    pluginBacked = {
        ip.EmxParticlesImportProvider: 'emxlib',
        ip.Xmipp3ParticlesImportProvider: 'xmipp3',
        ip.RelionParticlesImportProvider: 'relion',
        ip.FrealignParticlesImportProvider: 'cistem',
        ip.EmanParticlesImportProvider: 'eman2',
    }
    for providerClass, expectedModule in pluginBacked.items():
        assert providerClass.PLUGIN_MODULE == expectedModule

    # scipion's own local format has no external plugin to probe for.
    assert ip.ScipionParticlesImportProvider.isAvailable(
        ip.ScipionParticlesImportProvider()) is True


def test_defineParamsAddsExactlyTheLegacyFieldsPerFormat():
    expectedFields = {
        ip.EmxParticlesImportProvider: {'emxFile', 'alignType'},
        ip.Xmipp3ParticlesImportProvider: {'mdFile'},
        ip.RelionParticlesImportProvider: {'starFile', 'ignoreIdColumn'},
        ip.ScipionParticlesImportProvider: {'sqliteFile'},
        ip.FrealignParticlesImportProvider: {'frealignLabel', 'stackFile', 'parFile'},
        ip.EmanParticlesImportProvider: {'lstFile'},
    }

    for providerClass, fields in expectedFields.items():
        form = _FakeForm()
        providerClass().defineParams(form, condition="importFrom == 'x'")
        addedNames = {call[0] for call in form.calls}
        assert addedNames == fields
        for call in form.calls:
            assert call[2].get('condition') == "importFrom == 'x'"


def test_getFilePathReadsTheDeclaredField():
    prot = ProtImportParticles()
    prot.mdFile = params.String('/data/images.xmd')
    assert ip.Xmipp3ParticlesImportProvider().getFilePath(prot) == '/data/images.xmd'

    prot.starFile = params.String('  /data/it025_data.star  ')
    assert ip.RelionParticlesImportProvider().getFilePath(prot) == '/data/it025_data.star'


def test_importFromDelegatesToDomainImportFromPlugin(monkeypatch):
    calls = []

    class _FakeImporter:
        def __init__(self, *args):
            calls.append(args)

        def importParticles(self):
            calls.append('imported')

    monkeypatch.setattr(
        ip.Domain, 'importFromPlugin',
        lambda module, objects=None, errorMsg='', doRaise=False: _FakeImporter)

    prot = ProtImportParticles()
    prot.mdFile = params.String('/data/images.xmd')

    ip.Xmipp3ParticlesImportProvider().importFrom(prot)

    assert calls[0] == (prot, '/data/images.xmd')
    assert calls[1] == 'imported'


def test_validateDelegatesToTheSameImporterValidateParticles(monkeypatch):
    validated = []

    class _FakeImporter:
        def __init__(self, *args):
            pass

        def validateParticles(self):
            validated.append(True)
            return ['some error']

    monkeypatch.setattr(
        ip.Domain, 'importFromPlugin',
        lambda module, objects=None, errorMsg='', doRaise=False: _FakeImporter)

    prot = ProtImportParticles()
    prot.mdFile = params.String('/data/images.xmd')

    errors = ip.Xmipp3ParticlesImportProvider().validate(prot)

    assert validated == [True]
    assert errors == ['some error']


class _FakeForm:
    def __init__(self):
        self.calls = []

    def addParam(self, name, paramClass, **kwargs):
        self.calls.append((name, paramClass, kwargs))
