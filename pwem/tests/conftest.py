"""Test infrastructure for pwem/tests - does not modify any existing test
class (BaseTest, TestWorkflow, etc. are reused as-is by external plugins).
"""
import os
import shutil
import unittest

import pyworkflow as pw
from pyworkflow.protocol import HostConfig
from pyworkflow.tests.tests import DataSet

_hostsConf = os.path.join(pw.Config.SCIPION_HOME, "config", "hosts.conf")
os.makedirs(os.path.dirname(_hostsConf), exist_ok=True)
HostConfig.writeBasic(_hostsConf)

# BaseTest.setUpClass never triggers plugin discovery on its own, so the EM
# datasets pwem/tests/__init__.py registers (via Plugin._defineVariables)
# are otherwise never populated under a plain pytest/unittest run.
pw.Config.getDomain().getPlugins()

_origGetDataSet = DataSet.getDataSet.__func__


def _skippingGetDataSet(cls, name):
    ds = _origGetDataSet(cls, name)
    if pw.Config.SCIPION_TEST_NOSYNC and not os.path.isdir(ds.path):
        raise unittest.SkipTest(
            "Real EM dataset '%s' not present locally and SCIPION_TEST_NOSYNC "
            "blocks downloading it - excluded from hermetic CI." % name
        )
    return ds


DataSet.getDataSet = classmethod(_skippingGetDataSet)


# The home pyproject.toml gives the tests (through pytest-env). Without that
# plugin SCIPION_HOME may be any folder, even this repository: never remove it.
_TEST_HOME = os.path.realpath(os.path.expanduser("~/.cache/scipion_pwem_test_home"))


def pytest_sessionfinish(session, exitstatus):
    if os.path.realpath(pw.Config.SCIPION_HOME) == _TEST_HOME:
        shutil.rmtree(_TEST_HOME, ignore_errors=True)
