# HQ XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# HQ X
# HQ X   quippy: Python interface to QUIP atomistic simulation library
# HQ X
# HQ X   Copyright James Kermode 2019
# HQ X
# HQ X   These portions of the source code are released under the GNU General
# HQ X   Public License, version 2, http://www.gnu.org/copyleft/gpl.html
# HQ X
# HQ X   If you would like to license the source code under different terms,
# HQ X   please contact James Kermode, james.kermode@gmail.com
# HQ X
# HQ X   When using this software, please cite the following reference:
# HQ X
# HQ X   http://www.jrkermode.co.uk/quippy
# HQ X
# HQ XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX


"""
ASE-compatible Calculator wrapping a QUIP Potential object

"""

import ase
import ase.calculators.calculator
import numpy as np
from copy import deepcopy as cp

import quippy

__all__ = ['Potential']


class Potential(ase.calculators.calculator.Calculator):
    callback_map = {}

    implemented_properties = ['energy', 'forces', 'virial', 'stress',
                              'local_virial', 'local_energy', 'local_stress']

    # earlier in quippy
    # ['energy', 'energies', 'forces', 'stress', 'stresses',
    #  'numeric_forces', 'elastic_constants',
    #  'unrelaxed_elastic_constants']

    def __init__(self, args_str, param_str=None, atoms=None, calculation_always_required=False, param_filename=None, **kwargs):

        # update_docstring not implemented yet, it was oo_quip.update_doc_string() in the earlier version

        """

        from quip_docstring:

        args_str : str
            Valid arguments are 'Sum', 'ForceMixing', 'EVB', 'Local_E_Mix' and 'ONIOM', and any type of simple_potential
        param_str : str
            contents of xml parameter file for potential initializers, if needed

        -----------------------------------------------------------------------

        ase calculator has the following arguments for initialisation:

        let's not care about files for now, so just take them as None

        nay     restart: str
                    Prefix for restart file.  May contain a directory.  Default
                    is None: don't restart.
        nay     ignore_bad_restart_file: bool
                    Ignore broken or missing restart file.  By default, it is an
                    error if the restart file is missing or broken.
        nay     label: str
                    Name used for all files.  May contain a directory.
                atoms: Atoms object
                    Optional Atoms object to which the calculator will be
                    attached.  When restarting, atoms will get its positions and
                    unit-cell updated from file.

        ------------------------------------------------------------------------
        from old quippy arguments:

        used:
            init_args=None, param_str=None, atoms=None

        not used:
            calculator=None
            fpointer=None
            error=None

        not implemented yet:
            pot1=None, pot2=None
            param_filename=None
            bulk_scale=None
            mpi_obj=None
            callback=None
            calculation_always_required=False
            finalise=True
        """

        self._default_properties = ['energy', 'forces']
        self.calculation_always_required = calculation_always_required

        ase.calculators.calculator.Calculator.__init__(self, restart=None, ignore_bad_restart_file=False, label=None,
                                                       atoms=atoms, **kwargs)
        # init the quip potential
        if param_filename is not None and type(param_filename) == str:
            self._quip_potential = quippy.potential_module.Potential.filename_initialise(args_str=args_str,
                                                                                         param_filename=param_filename)
        else:
            self._quip_potential = quippy.potential_module.Potential(args_str=args_str, param_str=param_str)
        # init the quip atoms as None, to have the variable
        self._quip_atoms = None

        # from old
        if atoms is not None:
            atoms.set_calculator(self)
        self.name = args_str

        pass

    def calculate(self, atoms=None, properties=None, system_changes=None,
                  forces=None, virial=None, local_energy=None,
                  local_virial=None, vol_per_atom=None,
                  copy_all_properties=True):
        """Do the calculation.

        properties: list of str
            List of what needs to be calculated.  Can be any combination
            of 'energy', 'forces', 'stress', 'dipole', 'charges', 'magmom'
            and 'magmoms'.
        system_changes: list of str
            List of what has changed since last calculation.  Can be
            any combination of these six: 'positions', 'numbers', 'cell',
            'pbc', 'initial_charges' and 'initial_magmoms'.

        Subclasses need to implement this, but can ignore properties
        and system_changes if they want.  Calculated properties should
        be inserted into results dictionary like shown in this dummy
        example::

            self.results = {'energy': 0.0,
                            'forces': np.zeros((len(atoms), 3)),
                            'stress': np.zeros(6),
                            'dipole': np.zeros(3),
                            'charges': np.zeros(len(atoms)),
                            'magmom': 0.0,
                            'magmoms': np.zeros(len(atoms))}

        The subclass implementation should first call this
        implementation to set the atoms attribute.



        from docstring of quippy.potential_module.Potential.calc

        Each physical quantity has a
corresponding optional argument, which can either be an 'True'
to store the result inside the Atoms object (i.e. in
Atoms%params' or in 'Atoms%properties' with the
default name, a string to specify a different property or
parameter name, or an array of the the correct shape to
receive the quantity in question, as set out in the table
below.

        ================ ============= ================ =========================
        Array argument   Quantity       Shape           Default storage location
        ================ ============= ================ =========================
        ``energy``        Energy        ``()``           ``energy`` param
        ``local_energy``  Local energy  ``(at.n,)``      ``local_energy`` property
        ``force``         Force         ``(3,at.n)``     ``force`` property
        ``virial``        Virial tensor ``(3,3)``        ``virial`` param
        ``local_virial``  Local virial  ``(3,3,at.n)``   ``local_virial`` property
        ================ ============= ================ =========================


        """

        # handling the property inputs
        if properties is None:
            properties = self.get_default_properties()
        else:
            properties = list(set(self.get_default_properties() + properties))

        if len(properties) == 0:
            raise RuntimeError('Nothing to calculate')

        for prop in properties:
            if prop not in self.implemented_properties:
                raise RuntimeError("Don't know how to calculate property '%s'" % prop)

        # passing arguments which will be changed by the calculator
        _dict_args = {}
        # TODO implement this for energy too

        val = _check_arg(forces)
        if val == 'y':
            properties += ['force']
        elif val == 'add':
            properties += ['force']
            _dict_args['force'] = forces

        val = _check_arg(virial)
        if val == 'y':
            properties += ['virial']
        elif val == 'add':
            properties += ['virial']
            _dict_args['virial'] = virial

        val = _check_arg(local_energy)
        if val == 'y':
            properties += ['local_energy']
        elif val == 'add':
            properties += ['local_energy']
            _dict_args['local_energy'] = local_energy

        val = _check_arg(local_virial)
        if val == 'y':
            properties += ['local_virial']
        elif val == 'add':
            properties += ['local_virial']
            _dict_args['local_virial'] = local_virial

        # needed dry run of the ase calculator
        ase.calculators.calculator.Calculator.calculate(self, atoms, properties, system_changes)

        if not self.calculation_always_required and not self.calculation_required(self.atoms, properties):
            return

        # construct the quip atoms object which we will use to calculate on
        self._quip_atoms = quippy.convert.ase_to_quip(self.atoms, self._quip_atoms)

        # constructing args_string with automatically aliasing the calculateable non-quippy properties
        args_str = 'energy'
        # no need to add logic to energy, it is calculated anyways (returned when potential called)
        if 'virial' in properties or 'stress' in properties:
            args_str += ' virial'
        if 'local_virial' in properties or 'stresses' in properties:
            args_str += ' local_virial'
        if 'energies' in properties or 'local_energy' in properties:
            args_str += ' local_energy'
        if 'forces' in properties:
            args_str += ' force'
        # TODO: implement 'elastic_constants', 'unrelaxed_elastic_constants', 'numeric_forces'

        # the calculation itself
        _energy, _ferror = self._quip_potential.calc(self._quip_atoms, args_str=args_str, **_dict_args)

        self.results['energy'] = cp(_energy)  # fixme: don't overwrite existing properties, check for changes in atoms

        # retrieve data from _quip_atoms.properties and _quip_atoms.params
        _quip_properties = quippy.utils.get_dict_arrays(self._quip_atoms.properties)
        _quip_params = quippy.utils.get_dict_arrays(self._quip_atoms.params)

        # process potential output to ase.properties
        # not handling energy here, because that is always returned by the potential above
        if 'virial' in _quip_params.keys():
            stress = -_quip_params['virial'].copy() / self.atoms.get_volume()
            # convert to 6-element array in Voigt order
            self.results['stress'] = np.array([stress[0, 0], stress[1, 1], stress[2, 2],
                                               stress[1, 2], stress[0, 2], stress[0, 1]])
            self.results['virial'] = _quip_params['virial'].copy()

        if 'force' in _quip_properties.keys():
            self.results['forces'] = np.copy(_quip_properties['force'].T)

        if 'local_energy' in _quip_properties.keys():
            self.results['energies'] = np.copy(_quip_properties['local_energy'].T)

        if 'local_virial' in _quip_properties.keys():
            self.results['local_virial'] = np.copy(_quip_properties['local_virial'])

        if 'stresses' in properties:
            # use the correct atomic volume
            if vol_per_atom is not None:
                if vol_per_atom in self.atoms.arrays.keys():
                    # case of reference to a column in atoms.arrays
                    _v_atom = self.atoms.arrays[vol_per_atom]
                else:
                    # try for case of a given volume
                    try:
                        _v_atom = float(vol_per_atom)
                    except ValueError:
                        # cannot convert to float, so wrong
                        raise ValueError('volume_per_atom: not found in atoms.arrays.keys() and cannot utilise value '
                                         'as given atomic volume')
            else:
                # just use average
                _v_atom = self.atoms.get_volume() / self._quip_atoms.n
            self.results['stresses'] = -np.copy(_quip_properties['local_virial']).T.reshape((self._quip_atoms.n, 3, 3),
                                                                                            order='F') / _v_atom
        if isinstance(copy_all_properties, bool) and copy_all_properties:
            if atoms is not None:
                _at_list = [self.atoms, atoms]
            else:
                _at_list = list(self.atoms)

            for at in _at_list:
                _skip_keys = set(list(self.results.keys()) + ['Z', 'pos', 'species', 'map_shift', 'n_neighb'])

                # default params arguments
                at.info['energy'] = cp(_energy)

                if 'stress' in self.results.keys():
                    at.info['stress'] = self.results['stress'].copy()

                # default array arguments
                for key in ('forces', 'energies', 'stresses'):
                    if key in self.results.keys():
                        at.arrays[key] = self.results[key].copy()

                # any other params
                for param, val in _quip_params.items():
                    if param not in _skip_keys:
                        at.info[param] = cp(val)

                # any other arrays
                for prop, val in _quip_properties.items():
                    if prop not in _skip_keys:
                        at.arrays[prop] = np.copy(val, order='C')


    def get_virial(self, atoms=None):
        return self.get_property('virial', atoms)

    def get_local_virial(self, atoms=None):
        return self.get_stresses(atoms)

    def get_local_energy(self, atoms=None):
        return self.get_energies(atoms)

    def get_energies(self, atoms=None):
        return self.get_property('energies', atoms)

    def get_stresses(self, atoms=None):
        return self.get_property('stresses', atoms)

    def get_default_properties(self):
        """Get the list of properties to be calculated by default"""
        return self._default_properties[:]

    def set_default_properties(self, properties):
        """Set the list of properties to be calculated by default"""
        self._default_properties = properties[:]


def _check_arg(arg):
    """Checks if the argument is True bool or string meaning True"""

    true_strings = ('True', 'true', 'T', 't', '.true.', '.True.')

    if arg is None:
        return 'n'
    else:
        if isinstance(arg, bool):
            if arg:
                return 'y'
            else:
                return 'n'
        if isinstance(arg, str):
            if arg in true_strings:
                return 'y'
            else:
                return 'n'
        return 'add'
