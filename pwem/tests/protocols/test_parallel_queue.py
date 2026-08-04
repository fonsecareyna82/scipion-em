from pyworkflow.tests import BaseTest, setupTestProject

import pwem.protocols as emprot


class TestQueueBase(BaseTest):
    """ Exercises MPI/threads/GPU-param permutations for protocol
    execution, using a plugin-free dummy protocol (ProtTestQueue) instead
    of a real Relion/Xmipp protocol as the "something to run" vehicle.

    Only the useQueue=False path is covered here - the useQueue=True
    variants need a real HPC scheduler (qsub/qstat) configured in
    hosts.conf, unrelated to plugin availability. See .ai/roadmap.md.
    """

    def _checkAsserts(self, prot):
        self.assertTrue(prot.isFinished(), "Protocol did not finish.")
        self.assertEqual(prot.stepsRun.get(), prot.sleepSteps.get(),
                         "Protocol did not run the expected number of steps.")

    def _runTestQueue(self, label='', threads=1, MPI=1, doGpu=False, GPUs=''):
        prot = self.newProtocol(emprot.ProtTestQueue,
                                numberOfThreads=threads,
                                numberOfMpi=MPI,
                                sleepSecs=1,
                                sleepSteps=3)
        prot.setObjLabel(label)
        prot.doGpu.set(doGpu)
        if doGpu:
            prot.gpusToUse.set(GPUs)

        self.launchProtocol(prot)
        return prot


class TestNoQueueALL(TestQueueBase):
    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)

    def testNoGpuSerial(self):
        self._checkAsserts(self._runTestQueue("noGPU serial"))

    def testNoGpuMPI(self):
        self._checkAsserts(self._runTestQueue("noGPU MPI", MPI=4))

    def testNoGpuThreads(self):
        self._checkAsserts(self._runTestQueue("noGPU Threads", threads=4))

    def testNoGpuMPIandThreads(self):
        self._checkAsserts(
            self._runTestQueue("noGPU MPI+Threads", MPI=2, threads=5))

    def testGpuSerial(self):
        self._checkAsserts(self._runTestQueue("GPU serial", doGpu=True))

    def testGpuMPI(self):
        self._checkAsserts(
            self._runTestQueue("GPU MPI", doGpu=True, threads=5, MPI=2))

    def testGpuThreads(self):
        self._checkAsserts(
            self._runTestQueue("GPU Threads", doGpu=True, threads=4))

    def testGpuMPIandThreads(self):
        self._checkAsserts(
            self._runTestQueue("GPU MPI+Threads", doGpu=True, MPI=2, threads=3))


class TestNoQueueSmall(TestQueueBase):
    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)

    def testGpuMPI(self):
        self._checkAsserts(
            self._runTestQueue("GPU MPI", doGpu=True, threads=3, MPI=2))
