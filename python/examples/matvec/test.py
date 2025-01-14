# RUN: %PYTHON %s 2>&1 | FileCheck %s

# This file contains simple test cases that combine various codegen options.

from ..core.experts import *
from ..core.harness import *
from ..core.transforms import *

from ..contraction.definitions import *

################################################################################
### Compilation strategies.
################################################################################


class TestExpert(TransformationList):

  def __init__(self, tiling_transforms):
    t = tiling_transforms + [Bufferize()] + LoweringOnlyExpert(
        'matvec', 'linalg.generic').transforms
    TransformationList.__init__(self, **{'transforms': t})


# TODO: Check generate code for basic code quality, e.g., no linalg.copy.

# No tiling.
expert_no_tiling = TestExpert([])

# 1 level of tiling.
expert_tile_1 = TestExpert([
    Tile('matvec', 'linalg.generic', tile_sizes=[8, 24]),
    Vectorize('matvec', 'linalg.generic')
])
# 1 level of tile and interchange.
expert_tile_and_interchange_1 = TestExpert([
    Tile('matvec',
         'linalg.generic',
         tile_sizes=[8, 24],
         tile_interchange=[1, 0]),
    Vectorize('matvec', 'linalg.generic')
])
# 1 level of tiling and then generalize and interchange.
expert_tile_1_and_generalize_interchange = TestExpert([
    Tile('matvec',
         'linalg.generic',
         tile_sizes=[8, 24],
         tile_interchange=[1, 0]),
    Generalize('matvec',
               'linalg.generic',
               iterator_interchange=[0, 1]),
    Vectorize('matvec', 'linalg.generic')
])
# 1 level of tiling, peel, scalarize the remaining dynamic dims.
expert_tile_1_peel_scalarize = TestExpert([
    Tile('matvec', 'linalg.generic', tile_sizes=[8], peel=[0]),
    Tile('matvec', 'linalg.generic', scalarize_dyn_dims=True),
    Vectorize('matvec', 'linalg.generic')
])
# 1 level of tiling, with padding.
expert_tile_1_pad = TestExpert([
    Tile('matvec',
         'linalg.generic',
         tile_sizes=[8, 24],
         pad=True,
         pack_paddings=[1, 1, 1]),
    Vectorize('matvec', 'linalg.generic')
])
# 1 level of tiling, with padding, hoisted.
expert_tile_1_pad_hoist = TestExpert([
    Tile('matvec',
         'linalg.generic',
         tile_sizes=[8, 24],
         pad=True,
         pack_paddings=[1, 1, 1],
         hoist_paddings=[3, 3, 3]),
    Vectorize('matvec', 'linalg.generic')
])
# 2 levels of tiling, with padding, hoisted.
expert_tile_2_pad_hoist = TestExpert([
    Tile('matvec', 'linalg.generic', tile_sizes=[8, 24]),
    Tile('matvec',
         'linalg.generic',
         tile_sizes=[4, 12],
         pad=True,
         pack_paddings=[1, 1, 1],
         hoist_paddings=[6, 6, 6]),
    Vectorize('matvec', 'linalg.generic')
])
# 3 levels of tiling, with padding, hoisted. Peeling on the 3rd level.
expert_tile_3_pad_hoist_peel = TestExpert([
    Tile('matvec', 'linalg.generic', tile_sizes=[8, 24], pad=False),
    Tile('matvec',
         'linalg.generic',
         tile_sizes=[4, 12],
         pad=True,
         pack_paddings=[1, 1, 1],
         hoist_paddings=[6, 6, 6]),
    Tile('matvec', 'linalg.generic', tile_sizes=[2, 7], peel=[0, 1]),
    Vectorize('matvec', 'linalg.generic')
])
# 3 levels of tiling, with padding, hoisted. Peeling on the 3rd level.
# Scalarize remaining dynamic dims.
expert_tile_3_pad_hoist_peel_scalarize = TestExpert([
    Tile('matvec', 'linalg.generic', tile_sizes=[8, 24]),
    Tile('matvec',
         'linalg.generic',
         tile_sizes=[4, 12],
         pad=True,
         pack_paddings=[1, 1, 1],
         hoist_paddings=[6, 6, 6]),
    Tile('matvec', 'linalg.generic', tile_sizes=[2, 7], peel=[0, 1]),
    Tile('matvec', 'linalg.generic', scalarize_dyn_dims=True),
    Vectorize('matvec', 'linalg.generic')
])
# Fuse, then tile.
expert_fuse_2_tile_1 = TestExpert([
    Fuse('matvec', 'linalg.generic', tile_sizes=[8, 16]),
    Fuse('matvec', 'linalg.generic', tile_sizes=[4, 4]),
    Tile('matvec', 'linalg.generic', tile_sizes=[2, 3]),
    Vectorize('matvec', 'linalg.generic'),
    Vectorize('matvec', 'linalg.fill')
])
expert_fuse_and_pad = TestExpert([
    Fuse('matvec', 'linalg.generic', tile_sizes=[16, 16]),
    Tile('matvec',
         'linalg.generic',
         tile_sizes=[8, 12],
         pad=True,
         pack_paddings=[1, 1, 1],
         hoist_paddings=[3, 3, 3]),
    Vectorize('matvec', 'linalg.generic'),
    Tile('matvec', 'linalg.fill', tile_sizes=[8, 8]),
    Vectorize('matvec', 'linalg.fill')
])

all_experts = [
    expert_no_tiling, expert_tile_1, expert_tile_and_interchange_1,
    expert_tile_1_and_generalize_interchange, expert_tile_1_peel_scalarize,
    expert_tile_1_pad, expert_tile_1_pad_hoist, expert_tile_2_pad_hoist,
    expert_tile_3_pad_hoist_peel, expert_tile_3_pad_hoist_peel_scalarize,
    expert_fuse_2_tile_1, expert_fuse_and_pad
]

################################################################################
### Problem instantiations.
################################################################################

keys = ['m', 'n']


# CHECK-NOT: FAILURE
def main():
  n_iters = 1
  problem_size_list = [[24, 32], [27, 37]]
  test_harness(lambda s, t: EinsumProblem('mn,n', 'mn', 2), [[np.float32] * 3],
               test_sizes(keys, problem_size_list),
               all_experts,
               n_iters=n_iters,
               function_name='matvec')


if __name__ == '__main__':
  main()
