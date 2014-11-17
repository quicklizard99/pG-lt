#! /bin/usr/env python
# D.J. Bennett
# 24/03/2014
"""
pglt system tools
"""

# PACKAGES
import subprocess
import threading
import os
import Queue
import pickle
from datetime import datetime
from setup_tools import setUpLogging
from setup_tools import tearDownLogging
from setup_tools import sortArgs
from setup_tools import prime

# MESSAGES
toofewspecies_msg = '\nERROR: The program halted as there are too few \
species left of phylogeny building -- five is the minimum. You may \
have started with too few names, or names given could not be \
taxonomically resolved or there may be too little sequence data \
available.'
taxonomicrank_msg = '\nERROR: It is likely that one or more names\
have been resolved incorrectly, as such the parent taxonomic group \
has been set to Eukaryotes which is too high a taxonomic rank for \
phylogenetic analysis. Consider adding a parent ID to the \
parameters.csv to prevent incorrect names resolution or reducing the \
taxonomic diversity of the analysis names.'
outgroup_msg = '\nERROR: The outgroup has been dropped. This may be \
due to too few sequence data available for outgroup or a failure to \
align sequences that are available. If outgroup has been \
automatically selected, consider manually choosing an outgroup.'
raxml_msg = '\nERROR: Generated maxtrys poor phylogenies \
consecutively, consider reducing rttpvalue.'
unexpected_msg = '\nERROR: The following unexpected error occurred:\n\
\"{0}\" \n\
Please email details to the program maintainer for help.'


# ERROR CLASSES
class StageError(Exception):
    pass


class TooFewSpeciesError(Exception):
    pass


class TaxonomicRankError(Exception):
    pass


class OutgroupError(Exception):
    pass


class MafftError(Exception):
    pass


class RAxMLError(Exception):
    pass


class TrysError(Exception):
    pass


# OTHER CLASSES
class Stager(object):
    """Stager class : runs each file in stage folder. Adapted from\
 code written by L. Hudson."""
    # STAGES is added to Stager at __init__.py

    def __init__(self, wd, stage, verbose=False, debug=False):
        if stage not in self.STAGES:
            raise StageError('Stage [{0}] not recognised'.format(stage))
        else:
            self.wd = wd
            self.folder = os.path.split(wd)[-1]
            self.stage = stage
            self.logname = '{0}_stage{1}_logger'.format(self.folder, stage)
            # dir is second element of tuple
            self.output_dir = os.path.join(wd, self.STAGES[stage][1])
            self.verbose = verbose
            self.debug = debug

    def _start(self):
        self.logger.info('-' * 70)
        self.logger.info('Stage [{0}] started at [{1}]'.
                         format(self.stage, self._time_string()))
        self.logger.info('-' * 70)

    def _end(self):
        self.logger.info('-' * 70)
        self.logger.info('Stage [{0}] finished at [{1}]'.
                         format(self.stage, self._time_string()))
        self.logger.info('-' * 70 + '\n\n')

    def _error(self, msg):
        """Return true when error raised, log informative message"""
        self.logger.error(msg)
        self.logger.info('.... Moving to next folder')
        self.logger.info('Stage [{0}] unfinished at [{1}]'.
                         format(self.stage, self._time_string()))
        self.logger.info('-' * 70 + '\n\n')
        return True

    def _time_string(self):
        return datetime.today().strftime("%A, %d %B %Y %I:%M%p")

    def _cmd(self):
        """Run stage command. Catch errors raised."""
        error_raised = None
        try:
            # function is first element of tuple
            # pass wd and logger
            self.STAGES[self.stage][0](wd=self.wd, logger=self.logger)
        except TooFewSpeciesError:
            error_raised = self._error(toofewspecies_msg)
        except TaxonomicRankError:
            error_raised = self._error(taxonomicrank_msg)
        except OutgroupError:
            error_raised = self._error(outgroup_msg)
        except RAxMLError:
            error_raised = self._error(raxml_msg)
        except Exception as unexp_err:
            error_raised = self._error(unexpected_msg.format(unexp_err))
        return error_raised

    def run(self):
        # make sure dir exists
        if not os.path.isdir(self.output_dir):
            os.mkdir(self.output_dir)
        # set up a logger
        self.logger = setUpLogging(verbose=self.verbose, debug=self.debug,
                                   logname=self.logname,
                                   directory=self.output_dir)
        # log system info
        self._start()
        # run stage
        failed = self._cmd()
        if not failed:
            # log end time
            self._end()
        # remove logger
        tearDownLogging(self.logname)
        return failed

    @classmethod
    def run_all(klass, wd, stage, verbose):
        for s in sorted(Stager.STAGES.keys()[stage:]):
            Stager(wd, s).run()


class Runner(object):
    """Runner class : run stages across folders"""
    # _pars and _gpars is added at __init__.py

    def __init__(self, folders, nworkers, threads_per_worker, wd, email,
                 verbose=False, debug=False):
        self.wd = wd
        self.nworkers = nworkers
        self.threads_per_worker = threads_per_worker
        self.folders = folders
        self.verbose = verbose
        self.debug = debug
        self.email = email

    def setup(self, folders, base_logger):
        """Setup files across folders"""
        for folder in folders:
            arguments = sortArgs(directory=folder, email=self.email,
                                 logger=base_logger,
                                 default_pars_file=self._pars,
                                 default_gpars_file=self._gpars)
            # save threads per worker in each folder
            with open(os.path.join(folder, '.threads.p'), "wb") as file:
                pickle.dump(self.threads_per_worker, file)
            _ = prime(folder, arguments)
            del _

    def _worker(self):
        while True:
            # get folder and stages from queue
            folder, stage = self.q.get()
            # get a working dir for folder
            stage_wd = os.path.join(self.wd, folder)
            # run stage for folder
            stager = Stager(wd=stage_wd, stage=stage, verbose=self.verbose,
                            debug=self.debug)
            failed = stager.run()
            # if failed, remove folder from list
            if failed:
                self.folders.remove(folder)
            self.q.task_done()

    def run(self, folders, stage, parallel=False):
        """Run folders and stages"""
        if parallel:
            nworkers = self.nworkers
        else:
            nworkers = 1
        # create queue
        self.q = Queue.Queue(maxsize=0)
        # create nworkers workers
        threads = []
        for i in range(nworkers):
            t = threading.Thread(target=self._worker)
            threads.append(t)
            t.daemon = True
            t.start()
        # set workers running across all folders for stage
        for folder in folders:
            self.q.put((folder, stage))
        # join main thread and keep alive to watch for KIs
        # http://stackoverflow.com/questions/7610545/python-how-to-kill-threads-blocked-on-queue-with-signals
        main = threading.Thread(target=self.q.join)
        main.daemon = True
        main.start()
        while main.isAlive():
            main.join(3600)


class TerminationPipe(object):
    """TerminationPipe class : exectute background programs. Adapted pG code \
written by W.D. Pearse."""
    def __init__(self, cmd, timeout=99999, silent=True):
        self.cmd = cmd
        self.timeout = timeout
        self.process = None
        self.output = None
        self.failure = False
        self.stderr = 'EMPTY'
        self.stdout = 'EMPTY'
        self.silent = silent

    def run(self):
        def silentTarget():
            self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE,
                                            shell=True, stderr=subprocess.PIPE)
            self.output = self.process.communicate()

        def loudTarget():
            self.process = subprocess.Popen(self.cmd, shell=False)
            self.output = self.process.communicate()
        if self.silent:
            thread = threading.Thread(target=silentTarget)
        else:
            thread = threading.Thread(target=loudTarget)
        thread.start()
        thread.join(self.timeout)
        if thread.is_alive():
            self.process.terminate()
            thread.join()
            self.failure = True
