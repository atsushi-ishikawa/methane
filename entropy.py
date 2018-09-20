import numpy as np
import os,sys
from ase import Atoms, Atom
from ase.collections import methane
from reaction_tools import *
#
# Calculate entropy change along the reaction
#
argvs   = sys.argv
infile  = argvs[1]
outfile = "deltaS.txt"
f = open(outfile,"w")

(r_ads, r_site, r_coef,  p_ads, p_site, p_coef) = get_reac_and_prod(infile)

rxn_num = get_number_of_reaction(infile)

for irxn in range(rxn_num):
	# print "----- irxn = ", irxn, "-----"
	reac_S = 0.0
	prod_S = 0.0
	#
	# reactants
	#
	for imol, mol in enumerate(r_ads[irxn]):
		mol = mol[0]
		mol = remove_side_and_flip(mol)
		site = r_site[irxn][imol][0]

		if site != 'gas' or mol == 'surf' or mol == 'def':
			# surface species
			entropy = 0.0
			# print "R: molecular entropy for surf = ",entropy, "eV/K"
		else:
			tmp = methane[mol]
			try:
				entropy = methane.data[mol]['molecular_entropy']
				# print "R: molecular entropy for",mol," = ",entropy, "eV/K"
			except:
				entropy = 0.0

		reac_S += entropy

	#
	# products
	#
	for imol, mol in enumerate(p_ads[irxn]):
		mol  = mol[0]
		mol  = remove_side_and_flip(mol)
		site = p_site[irxn][imol][0]

		if site != 'gas' or mol == 'surf' or mol == 'def':
			entropy = 0.0
			# print "P: molecular entropy for surf = ",entropy, "eV/K"
		else:
			tmp = methane[mol]
			try:
				entropy = methane.data[mol]['molecular_entropy']
				# print "P: molecular entropy for",mol," = ",entropy, "eV/K"
			except:
				entropy = 0.0

		prod_S += entropy

	deltaS = np.sum(prod_S) - np.sum(reac_S)

	# write to file
	f.write("{0:>16.8e}\n".format(deltaS))

