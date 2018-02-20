import numpy as np
import os, sys, re, json
from reaction_tools import *
from ase import Atoms, Atom
from ase.calculators.gaussian import Gaussian
from ase.calculators.vasp import Vasp
from ase.calculators.emt import EMT
from ase.collections import methane
from ase.optimize import BFGS
from ase.vibrations import Vibrations
from ase.db import connect
from ase.io import read
from ase.build import add_adsorbate
# -------------------------------------------------
# calculate reaction energy.
# molecule's data should be stored in "methane.json"
# -------------------------------------------------
# settings
#
argvs = sys.argv
reactionfile = argvs[1]

calculator   = "vasp"
calculator = calculator.lower()

#
# if surface present, provide surface file
# in ase.db form
#
surface = False

if surface:
	db = connect('surf.db')
	surf    = db.get_atoms(id=1)
	lattice = db.get(id=1).data.lattice
	facet   = db.get(id=1).data.facet

	# load site information
	f = open('site_info.json','r')
	site_info = json.load(f)
	f.close()

(r_ads, r_site, r_coef,  p_ads, p_site, p_coef) = get_reac_and_prod(reactionfile)

rxn_num = get_number_of_reaction(reactionfile)
Ea = np.array(2, dtype="f")

## --- parameters
ZPE = False
SP  = False
maxoptsteps = 200
ads_hight = 2.5
# whether to do single point after optimization
# at different computational level

## --- Gaussian ---
if "gau" in calculator:
	method = "m06"
	basis  = "aug-cc-pvtz" # do not use aesterisk for polarization func
	if SP:
		method_sp = "ccsd(t)"
	basis_name = re.sub("\(", "", basis)
	basis_name = re.sub("\)", "", basis_name)
	basis_name = re.sub(",",  "", basis_name)
	label = method + "-" + basis_name

## --- VASP ---
elif "vasp" in calculator:
	xc     = "pbe"
	prec   = "normal"
	encut  = 400.0 # 213.0 or 400.0 or 500.0
	potim  = 0.10
	nsw    = 100
	ediff  = 1.0e-5
	ediffg = -0.01
	kpts   = [1, 1, 1]
	vacuum = 10.0
	setups = None
	#setups = {"O" : "_h"}

	method = xc
	basis = ""
	label = method

## --- EMT --- -> nothing to set


if ZPE:
	label = label + "ZPE"
if SP:
	label = label + "SP"

barrierfile  = reactionfile.split(".")[0] + "_Ea_" + label + ".txt"
fbarrier = open(barrierfile, "w")
fbarrier.close()

print "calculator:" + calculator + " method: " + method + " basis: " + basis

for irxn in range(rxn_num):
	fbarrier = open(barrierfile, "a")
	print "--- calculating elementary reaction No. ", irxn, "---"

	reac_en = np.array(range(len(r_ads[irxn])),dtype="f")
	prod_en = np.array(range(len(p_ads[irxn])),dtype="f")
	reac_A  = np.array(range(len(r_ads[irxn])),dtype="f")
	prod_A  = np.array(range(len(r_ads[irxn])),dtype="f")
	#
	# reactants
	#
	for imol, mol in enumerate(r_ads[irxn]):
		print "----- reactant: molecule No.", imol, " is ", mol, "-----"

		if mol == "surf":
			tmp = surf
		else:
			tmp = methane[mol]

		site = r_site[irxn][imol]

		try:
			site_pos = site.split(".")[1]
		except:
			site_pos = "x1y1"

		if site != 'gas':
			surf_tmp = surf.copy()
			offset = site_info[lattice][facet][site][site_pos]
			print "lattice",lattice; print "facet", facet; print "site",site; print "site_pos",site_pos
			add_adsorbate(surf_tmp, tmp, ads_hight, position=(0,0), offset=offset)
			tmp = surf_tmp
			del surf_tmp

		magmom  = tmp.get_initial_magnetic_moments()
		natom   = len(tmp.get_atomic_numbers())
		coef    = r_coef[irxn][imol]
		r_traj  = label + str(irxn) + "-" + str(imol) + "reac.traj"
		r_label = label + str(irxn) + "-" + str(imol)

		if "gau" in calculator:
			tmp.calc = Gaussian(label=r_label, method=method, basis=basis)
			opt = BFGS(tmp, trajectory=r_traj)
			opt.run(fmax=0.05, steps=maxoptsteps)
			if SP:
				r_label = r_label + "_sp"
				tmp.calc = Gaussian(label=r_label, method=method_sp, basis=basis, force=None)
		elif "vasp" in calculator:
			cell = np.array([1, 1, 1])
			cell = vacuum*cell
			tmp.cell = cell
		 	tmp.calc = Vasp(output_template=r_label, prec=prec, xc=xc, ispin=2, encut=encut, ismear=0, istart=0, setups=setups,
					ibrion=2, potim=potim, nsw=nsw, ediff=ediff, ediffg=ediffg, kpts=kpts )
		elif "emt" in calculator:
			tmp.calc = EMT()
			opt = BFGS(tmp, trajectory=r_traj)
			opt.run(fmax=0.05, steps=maxoptsteps)

		en  = tmp.get_potential_energy()

		if ZPE == True and natom != 1:
			vib = Vibrations(tmp)
			vib.run()
			hnu = vib.get_energies()
			zpe = vib.get_zero_point_energy()
			reac_en[imol] = en + zpe
			os.system("rm vib.*")
		else:
			reac_en[imol] = en

		reac_en[imol] = coef * reac_en[imol]

	#
	# products
	#
	for imol, mol in enumerate(p_ads[irxn]):
		print "----- product: molecule No.", imol, " is ", mol, "-----"

		if mol == "surf":
			tmp = surf
		else:
			tmp   = methane[mol]

		site = p_site[irxn][imol]
		try:
			site_pos = site.split(".")[1]
		except:
			site_pos = "x1y1"

		if site != 'gas':
			surf_tmp = surf.copy()
			offset = site_info[lattice][facet][site][site_pos]
			print "lattice",lattice; print "facet", facet; print "site",site; print "site_pos",site_pos
			add_adsorbate(surf_tmp, tmp, ads_hight, position=(0,0), offset=offset)
			tmp = surf_tmp
			del surf_tmp

		magmom  = tmp.get_initial_magnetic_moments()
		natom   = len(tmp.get_atomic_numbers())
		coef    = p_coef[irxn][imol]
		p_traj  = label + str(irxn) + "-" + str(imol) + "prod.traj"
		p_label = label + str(irxn) + "-" + str(imol)

		if "gau" in calculator:
			tmp.calc = Gaussian(label=p_label, method=method, basis=basis)
			opt = BFGS(tmp, trajectory=p_traj)
			opt.run(fmax=0.05, steps=maxoptsteps)
			if SP:
				label = label + "_sp"
				tmp.calc = Gaussian(method=method_sp, basis=basis)
		elif "vasp" in calculator:
			cell = np.array([1, 1, 1])
			cell = vacuum*cell
			tmp.cell = cell
		 	tmp.calc = Vasp(output_template=p_label, prec=prec, xc=xc, ispin=2, encut=encut, ismear=0, istart=0, setups=setups,
					ibrion=2, potim=potim, nsw=nsw, ediff=ediff, ediffg=ediffg, kpts=kpts )
		elif "emt" in calculator:
			tmp.calc = EMT()
			opt = BFGS(tmp, trajectory=p_traj)
			opt.run(fmax=0.05, steps=maxoptsteps)

		en  = tmp.get_potential_energy()

		if ZPE == True and natom != 1:
			vib = Vibrations(tmp)
			vib.run()
			hnu = vib.get_energies()
			zpe = vib.get_zero_point_energy()
			prod_en[imol] = en + zpe
			os.system("rm vib.*")
		else:
			prod_en[imol] = en

		prod_en[imol] = coef * prod_en[imol]

	deltaE = np.sum(prod_en) - np.sum(reac_en)
	print "deltaE = ",deltaE
	Eafor  =  deltaE
	Earev  = -deltaE
	Ea = [Eafor, Earev]
	fbarrier.write("{0:<16.8f} {1:<16.8f}\n".format(Eafor, Earev))
	fbarrier.close()
	#
	# loop over reaction
	#

remove_parentheses(barrierfile)

