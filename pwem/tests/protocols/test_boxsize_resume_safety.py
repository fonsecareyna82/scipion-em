import unittest
from unittest.mock import MagicMock, Mock, call

from pwem.protocols.protocol_boxsize_checkpoint import ProtBoxSizeCheckpoint
from pwem.protocols.protocol_boxsize_parameters import ProtBoxSizeParameters


class TestBoxSizeResumeSafety(unittest.TestCase):

    def test_ParametersStepPublishesOutputsBeforeReturning(self):
        protocol = ProtBoxSizeParameters()
        protocol.outputsToDefine = {}

        protocol.boolExtractPartBx = MagicMock()
        protocol.boolExtractPartBx.get.return_value = False
        protocol.boolGautomatchParams = MagicMock()
        protocol.boolGautomatchParams.get.return_value = False
        protocol.boolRelionParams = MagicMock()
        protocol.boolRelionParams.get.return_value = False
        protocol.boolTopazParams = MagicMock()
        protocol.boolTopazParams.get.return_value = False
        protocol.boolConsensusParams = MagicMock()
        protocol.boolConsensusParams.get.return_value = False

        protocol.createResultsOutput = Mock()

        protocol.applyFormulaStep(100, 1.5)

        protocol.createResultsOutput.assert_called_once_with()

    def test_CheckpointStepPublishesOnlyAfterWaiting(self):
        protocol = ProtBoxSizeCheckpoint()

        protocol.boxSize1 = MagicMock()
        protocol.boxSize1.get.return_value = 100
        protocol.boxSize2 = MagicMock()
        protocol.boxSize2.get.return_value = 110
        protocol.boolTimer = MagicMock()
        protocol.boolTimer.get.return_value = True

        protocol._insertFunctionStep = Mock(side_effect=[41, 42])

        protocol._insertAllSteps()

        self.assertEqual(
            [
                call('waitingStep', prerequisites=[]),
                call('publishComparisonStep', 100, 110, prerequisites=[41]),
            ],
            protocol._insertFunctionStep.call_args_list,
            "Checkpoint publication must be a durable step that depends on "
            "the waiting step.",
        )

        protocol.outputsToDefine = {}
        protocol.disagreeFactor = MagicMock()
        protocol.disagreeFactor.get.return_value = 0.2
        protocol.boolBoxSizeAvg = MagicMock()
        protocol.boolBoxSizeAvg.get.return_value = False
        protocol.boolBoxSize1 = MagicMock()
        protocol.boolBoxSize1.get.return_value = True
        protocol.createResultsOutput = Mock()
        protocol._insertFunctionStep.reset_mock()

        protocol.applyComparisonStep(100, 110)

        protocol._insertFunctionStep.assert_not_called()
        protocol.createResultsOutput.assert_not_called()

    def test_InitParamsUsesPerInstanceOutputDictionary(self):
        first = ProtBoxSizeParameters()
        second = ProtBoxSizeParameters()

        first.initParams()
        second.initParams()

        first.outputsToDefine["onlyFirst"] = 1

        self.assertNotIn("onlyFirst", second.outputsToDefine)
        self.assertIsNot(first.outputsToDefine, second.outputsToDefine)


if __name__ == "__main__":
    unittest.main()
