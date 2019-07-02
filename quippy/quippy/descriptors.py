# HQ XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# HQ X
# HQ X   quippy: Python interface to QUIP atomistic simulation library
# HQ X
# HQ X   Copyright T. K. Stenczel 2019
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
# HQ XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX


import quippy
from ase import Atoms
import numpy as np


def convert_atoms_types_iterable_method(method):
    """
    Decorator to transparently convert ASEAtoms objects into quippy Atoms, and
    to transparently iterate over a list of Atoms objects...

    Taken from py2 version
    """
    def wrapper(self, at, *args, **kw):
        if isinstance(at, quippy.atoms_types_module.Atoms):
            return method(self, at, *args, **kw)
        elif isinstance(at, Atoms):
            _quip_at = quippy.convert.ase_to_quip(at)
            return method(self, _quip_at, *args, **kw)
        else:
            return [wrapper(self, atelement, *args, **kw) for atelement in at]
    return wrapper

class descriptor:

    def __init__(self, args_str=None, **init_args):
        """
        Initialises Descriptor object and calculate number of dimensions and
        permutations.


        properties:
        - cutoff

        calculateable:
        - sizes: `n_desc, n_cross, n_index, err = desc.sizes(_quip_atoms)`

        """

        if args_str is None:
            raise NotImplementedError()
            # args_str = dict_to_args_str(init_args)

        # intialise the wrapped object and hide it from the user
        self._quip_descriptor = quippy.descriptors_module.descriptor(args_str)

        # kept for compatibility with older version
        # super convoluted though :D should just rethink it at some point
        self.n_dim = self.dimensions()
        self._n_perm = self.permutations()

        # arg string

    def dimensions(self):
        return self._quip_descriptor.dimensions()[0]

    def permutations(self):
        return self._quip_descriptor.n_permutations()[0]

    def cutoff(self):
        # TODO: decide if adding @property is a good idea
        # could be like get_cutoff()
        return self._quip_descriptor.cutoff()[0]

    @convert_atoms_types_iterable_method
    def sizes(self, at):
        """
        Replicating the QUIP method, is used in the rest of the methods
        """

        n_descriptors, n_cross, n_index, err = self._quip_descriptor.sizes(at)

        # fixme: is the err useful here at all?
        return n_descriptors, n_cross, n_index, err

    @convert_atoms_types_iterable_method
    def count(self, at):
        """
        Returns how many descriptors of this type are found in the Atoms
        object.
        """
        # fixme: is the decorator needed now?
        return self.sizes(at)[0]

    @convert_atoms_types_iterable_method
    def _calc_connect(self, at):
        """
        Internal method for calculating connectivity on a quip_atoms object

        Ideally called only on quip_atoms object, but put in decorator to make sure
        :param at:
        :return:
        """

        # setting to +1 is arbitrary here, the point is to set to something a bit higher than the descriptor's
        if at.cutoff < self.cutoff() + 1:
            at.set_cutoff(self.cutoff() + 1)

        # TODO: add logic to skip this if it has been calculated already for speedup
        at.calc_connect()

    @convert_atoms_types_iterable_method
    def calc_descriptor(self, at, args_str=None, **calc_args):
        """
        Calculates all descriptors of this type in the Atoms object, and
        returns the array of descriptor values. Does not compute gradients; use
        calc(at, grad=True, ...) for that.

        """

        return self.calc(at, False, args_str, **calc_args).descriptor

    @convert_atoms_types_iterable_method
    def calc(self, at, grad=False, args_str=None, **calc_args):
        """
        Calculates all descriptors of this type in the Atoms object, and
        gradients if grad=True. Results can be accessed dictionary- or
        attribute-style; 'descriptor' contains descriptor values,
        'descriptor_index_0based' contains the 0-based indices of the central
        atom(s) in each descriptor, 'grad' contains gradients,
        'grad_index_0based' contains indices to gradients (descriptor, atom).
        Cutoffs and gradients of cutoffs are also returned.


        Py3: desc.calc() only works if both `do_descriptor=True, do_grad_descriptor=True`
        So the args here only control if the result is returned or not.
        """

        # n_index = fzeros(1, 'i')
        # n_desc, n_cross = self.descriptor_sizes(at, n_index=n_index)
        # n_index = n_index[1]
        # data = fzeros((self.n_dim, n_desc))
        # cutoff = fzeros(n_desc)
        # data_index = fzeros((n_index, n_desc), 'i')
        #
        # if grad:
        #     # n_cross is number of cross-terms, proportional to n_desc
        #     data_grad = fzeros((self.n_dim, 3, n_cross))
        #     data_grad_index = fzeros((2, n_cross), 'i')
        #     cutoff_grad = fzeros((3, n_cross))
        #
        # if not grad:
        #     RawDescriptor.calc(self, at, descriptor_out=data, covariance_cutoff=cutoff,
        #                        descriptor_index=data_index, args_str=args_str)
        # else:
        #     RawDescriptor.calc(self, at, descriptor_out=data, covariance_cutoff=cutoff,
        #                        descriptor_index=data_index, grad_descriptor_out=data_grad,
        #                        grad_descriptor_index=data_grad_index, grad_covariance_cutoff=cutoff_grad,
        #                        args_str=args_str)
        #
        # results = DescriptorCalcResult()
        # convert = lambda data: np.array(data).T
        # results.descriptor = convert(data)
        # results.cutoff = convert(cutoff)
        # results.descriptor_index_0based = convert(data_index - 1)
        # if grad:
        #     results.grad = convert(data_grad)
        #     results.grad_index_0based = convert(data_grad_index - 1)
        #     results.cutoff_grad = convert(cutoff_grad)
        # return results

        if args_str is None:
            raise NotImplementedError()
        #     args_str = dict_to_args_str(calc_args)

        # calc connectivity on the atoms object with the internal one
        self._calc_connect(at)

        # descriptor calculation
        descriptor_out_raw, err = self._quip_descriptor.calc(at, do_descriptor=True, do_grad_descriptor=grad)

        # unpack to a list of dicts
        count = self.count(at)
        descriptor_out = []
        for i in range(count):
            # unpack to dict with the specific converter function
            descriptor_out.append(quippy.convert.descriptor_data_mono_to_dict(descriptor_out_raw.x[i]))


        # TODO: this needs to be changed, check the old implementation
        # could make it behave exactly as it did earlier for compatibility, but not sure if we want that actually
        # ask Gabor and James about this
        return np.array(descriptor_out)

