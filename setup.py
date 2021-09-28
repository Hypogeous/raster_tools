import numpy as np
from multiprocessing import cpu_count
from setuptools import setup, Extension
from Cython.Build import cythonize
from Cython.Compiler import Options

Options.fast_fail = True

setup(
    ext_modules=cythonize(
        [
            Extension(
                "raster_tools.costdist._heap",
                ["raster_tools/costdist/_heap.pyx"],
                extra_compile_args=[
                    "-O3",
                    "-march=native",
                    "-g0",
                ],
            ),
            Extension(
                "raster_tools.costdist._core",
                ["raster_tools/costdist/_core.pyx"],
                extra_compile_args=[
                    "-O3",
                    "-march=native",
                    "-g0",
                ],
            ),
        ],
        nthreads=cpu_count(),
    ),
    include_dirs=[np.get_include()],
)