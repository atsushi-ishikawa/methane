import numpy as np
import os,sys
import json
from reaction_tools import *
from ase import Atoms, Atom
from ase.calculators.gaussian import Gaussian
from ase.calculators.vasp import Vasp
from ase.calculators.emt import EMT
from ase.collections import methane
from ase.optimize import MDMin
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
#reactionfile = "test.txt"
#barrierfile  = "test_barrier.txt"
reactionfile = "gri3.0_ads.txt"
barrierfile  = "gri3.0_ads_bar.txt"
calculator   = "EMT" ; calculator = calculator.lower()
#
# if surface present, provide surface file
# in ase.db form
#
db = connect('surf.db')
surf    = db.get_atoms(id=1)
lattice = db.get(id=1).data.lattice
facet   = db.get(id=1).data.facet

# load site information
f = open('site_info.json','r')
site_info = json.load(f)
f.close()
#
fbarrier = open(barrierfile, "w")

(r_ads, r_site, r_coef,  p_ads, p_site, p_coef) = get_reac_and_prod(reactionfile)

rxn_num = get_number_of_reaction(reactionfile)
Ea = np.array(2, dtype="f")

# parameters
ZPE = False
maxoptsteps = 100
ads_hight = 2.5

## --- Gaussian ---
if "gau" in calculator:
	method = "b3lyp"
	basis  = "6-31G"
## --- VASP ---
elif "vasp" in calculator:
	xc    = "pbe"
	prec  = "normal"
	encut = 400.0
	potim = 0.10
	nsw   = 100
	ediff = 1.0e-4
	ediffg = -0.03
	kpts = [1, 1, 1]
## --- EMT --- -> nothing to set

for irxn in range(rxn_num):
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

		site = r_site[irxn][0]

		try:
			site_pos = site.split(".")[1]
		except:
			site_pos = "x1y1"

		if site != 'gas':
			surf_tmp = surf.copy()
			# print "lattice",lattice; print "facet", facet; print "site",site; print "site_pos",site_pos
			offset = site_info[lattice][facet][site][site_pos]
			add_adsorbate(surf_tmp, tmp, ads_hight, position=(0,0), offset=offset)
			tmp = surf_tmp
			del surf_tmp

		magmom = tmp.get_initial_magnetic_moments()
		natom  = len(tmp.get_atomic_numbers())
		coef   = r_coef[irxn][imol]
		r_traj = str(irxn) + "-" + str(imol) + "reac.traj"

		if "gau" in calculator:
			tmp.calc = Gaussian(method=method, basis=basis)
			opt = MDMin(tmp, trajectory=r_traj)
			opt.run(fmax=0.05, steps=maxoptsteps)
		elif "vasp" in calculator:
			cell = [10.0, 10.0, 10.0]
			tmp.cell = cell
			tmp.calc = Vasp(prec=prec,xc=xc,ispin=2,encut=encut, ismear=0, istart=0,
					ibrion=2, potim=potim, nsw=nsw, ediff=ediff, ediffg=ediffg, kpts=kpts )
		elif "emt" in calculator:
			tmp.calc = EMT()
			opt = MDMin(tmp, trajectory=r_traj)
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

		site = p_site[irxn]
		try:
			site_pos = site.split(".")[1]
		except:
			site_pos = "x1y1"

		if site != 'gas':
			surf_tmp = surf.copy()
			offset = site_info[lattice][facet][site[0]][site_pos]
			add_adsorbate(surf_tmp, tmp, ads_hight, position=(0,0), offset=offset)
			tmp = surf_tmp
			del surf_tmp

		magmom = tmp.get_initial_magnetic_moments()
		natom  = len(tmp.get_atomic_numbers())
		coef   = p_coef[irxn][imol]
		p_traj = str(irxn) + "-" + str(imol) + "prod.traj"

		if "gau" in calculator:
			tmp.calc = Gaussian(method=method, basis=basis)
			opt = MDMin(tmp, trajectory=p_traj)
			opt.run(fmax=0.05, steps=maxoptsteps)
		elif "vasp" in calculator:
			cell = [10.0, 10.0, 10.0]
			tmp.cell = cell
			tmp.calc = Vasp(prec=prec,xc=xc,ispin=2,encut=encut, ismear=0, istart=0,
					ibrion=2, potim=potim, nsw=nsw, ediff=ediff, ediffg=ediffg, kpts=kpts )
		elif "emt" in calculator:
			tmp.calc = EMT()
			opt = MDMin(tmp, trajectory=p_traj)
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
	fbarrier.write(str(Ea) + "\n")
	#
	# loop over reaction
	#

fbarrier.close()
remove_parentheses(barrierfile)
