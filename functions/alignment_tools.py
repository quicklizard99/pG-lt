#!/usr/bin/python
## No warranty, no copyright
## Dominic John Bennett
## 31/08/2013

import numpy as np
import random

def parseSeqsObj(seqs_obj, gene_overlap, genes, min_nspp):
	"""Take seqs_obj and remove sequences outside of median +- overlap. Drop species and genes with too little data or no outgroup"""
	nseqs = 0
	parsed_seqs_obj = []
	medians = []
	new_genes = []
	ntaxa = []
	for j in range(len(seqs_obj)):
		if len(seqs_obj[j]) > min_nspp:
			ntaxa_gene = 0
			seq_lens = []
			for sp in seqs_obj[j]:
				seq_lens.extend([len(s) for s in sp])
			median = np.median(seq_lens)
			len_max = median + median*gene_overlap
			len_min = median - median*gene_overlap
			parsed_seqs = []
			seq_ids = []
			nseqs_gene = 0
			for sp in seqs_obj[j]:
				parsed_seq = [s for s in sp if len_min < len(s) < \
					len_max]
				seq_ids.extend([s.id for s in parsed_seq])
				if len(parsed_seq) > 0:
					nseqs_gene += len(parsed_seq)
					parsed_seqs.append(parsed_seq)
					ntaxa_gene += 1
			if len(parsed_seqs) > min_nspp:
				if "outgroup" in seq_ids:
					parsed_seqs_obj.append(parsed_seqs)
					medians.append(median)
					new_genes.append(genes[j])
					ntaxa.append(ntaxa_gene)
					nseqs += nseqs_gene
				else:
					print "!! Outgroup dropped for gene [{0}] that would have represented [{1}] species".\
						format(genes[j], ntaxa_gene)
	return (parsed_seqs_obj, new_genes, nseqs, medians, ntaxa)
	
def alignSeqsObj(gene_obj, align_len_max, nfails, median, prop):
	"""Take a gene_obj and generate 100 alignments. Return empty list if alignment fails nfails times in a row."""
	# separate outgroup seqs from rest!
	out_obj = [e for e in gene_obj if e[0].id == "outgroup"]
	gene_obj = [e for e in gene_obj if e[0].id != "outgroup"]
	nruns = 0
	mean_seqs = nseqs/len(gene_obj)
	try:
		niterations = int(round(float(mean_seqs)** \
			float(len(gene_obj))))
	except OverflowError:
		niterations = 100
	if niterations > 100: # limit to 100
		niterations = 100
	count_fails = 0
	aligns = []
	for k in range(niterations):
		if count_fails < nfails:
			# select species randomly in the geneobj and choose random seqs
			sample = random.sample(range(len(gene_obj)), int(len(gene_obj) * prop))
			samp_obj = [ee for ei,ee in enumerate(gene_obj) if ei in sample]
			samp_obj.extend(out_obj)
			seqs = [random.sample(s, 1) for s in samp_obj]
			align = pG.alignSequences(seqs, method= 'mafft', nGenes = 1)
			nruns += 1
			# drop bad alignments
			alen_max = median + (median * align_len_max)
			alen = align[0][0].get_alignment_length()
			if alen > alen_max:
				count_fails += 1
				continue
			aligns.append(align[0][0])
			count_fails = 0
		else:
			return ([], nruns)
	return (aligns, nruns)
