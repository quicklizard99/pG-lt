#! /bin/usr/env python
# D.J. Bennett
# 26/05/2014
"""
Test phylogeny stage.
"""

import unittest
import os
import shutil
import pickle
from pglt.stages import phylogeny_stage as pstage
from Bio import AlignIO
from Bio import Phylo
from cStringIO import StringIO

# DIRS
working_dir = os.path.dirname(__file__)


# FUNCTIONS
def genPhylogeny():
    treedata = "(outgroup, (B, C), (D, E))"
    handle = StringIO(treedata)
    tree = Phylo.read(handle, "newick")
    return tree


# DUMMIES
class DummyAlignmentStore(object):
    def __init__(self, clusters, genedict, allrankids, indir, logger):
        pass


class DummyGenerator(object):
    phylogenies = [genPhylogeny()]

    def __init__(self, alignment_store, rttpvalue, outdir, maxtrys, logger,
                 wd):
        pass

    def run(self):
        return True


# TEST DATA
with open(os.path.join(working_dir, 'data', 'test_alignment_ref.faa'), 'r')\
        as file:
    alignment = AlignIO.read(file, 'fasta')

paradict = {'nphylos': 1, 'maxtrys': 1, 'rttpvalue': 0.5}
genedict = {}
allrankids = []


class PhylogenyStageTestSuite(unittest.TestCase):

    def setUp(self):
        # stub out
        self.true_AlignmentStore = pstage.ptools.AlignmentStore
        self.true_Generator = pstage.ptools.Generator
        pstage.ptools.Generator = DummyGenerator
        pstage.ptools.AlignmentStore = DummyAlignmentStore
        # create input data
        with open(".paradict.p", "wb") as file:
            pickle.dump(paradict, file)
        with open(".genedict.p", "wb") as file:
            pickle.dump(genedict, file)
        with open(".allrankids.p", "wb") as file:
            pickle.dump(allrankids, file)
        os.mkdir('3_alignment')
        os.mkdir('4_phylogeny')
        os.mkdir(os.path.join('3_alignment', 'COI'))
        os.mkdir(os.path.join('3_alignment', 'rbcl'))
        with open(os.path.join('3_alignment', 'rbcl',
                               'test_alignment_rbl.faa'), 'w') as file:
            count = AlignIO.write(alignment, file, "fasta")
            del count
        with open(os.path.join('3_alignment', 'COI',
                               'test_alignment_COI.faa'), 'w') as file:
            count = AlignIO.write(alignment, file, "fasta")
            del count

    def tearDown(self):
        # remove all files potentially generated by phylogeny stage
        phylogeny_files = ['.paradict.p', '.genedict.p', '.allrankids.p']
        while phylogeny_files:
            try:
                phylogeny_file = phylogeny_files.pop()
                os.remove(phylogeny_file)
            except OSError:
                pass
        # remove all folders potentially generated by phylogeny stage
        phylogeny_folders = ['3_alignment', '4_phylogeny', 'tempfiles']
        while phylogeny_folders:
            try:
                phylogeny_folder = phylogeny_folders.pop()
                shutil.rmtree(phylogeny_folder)
            except OSError:
                pass
        # stub in
        pstage.ptools.Generator = self.true_Generator
        pstage.ptools.AlignmentStore = self.true_AlignmentStore

    def test_phylogeny_stage(self):
        # run
        res = pstage.run()
        # clean dir
        os.remove(os.path.join('4_phylogeny', 'distribution.tre'))
        os.remove(os.path.join('4_phylogeny', 'consensus.tre'))
        os.rmdir('4_phylogeny')
        # assert
        self.assertIsNone(res)

if __name__ == '__main__':
    unittest.main()
