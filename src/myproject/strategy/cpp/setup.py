"""
Configuration setup.py pour compiler le module C++ avec pip
Alternative à CMake pour une installation plus simple
"""

from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext
import sys

__version__ = "1.0.0"

# Flags de compilation avec OpenMP
if sys.platform == "win32":
    # MSVC: /O2 optimisation, /openmp pour parallélisation
    compile_args = ["/O2", "/openmp"]
    link_args = []
else:
    # GCC/Clang: -O3 optimisation, -fopenmp pour parallélisation
    compile_args = ["-O3", "-ffast-math", "-fopenmp"]
    link_args = ["-fopenmp"]

ext_modules = [
    Pybind11Extension(
        "strategy_metrics_cpp",
        ["strategy_metrics.cpp", "bindings.cpp"],
        include_dirs=["."],
        cxx_std=17,
        extra_compile_args=compile_args,
        extra_link_args=link_args,
    ),
]

setup(
    name="strategy_metrics_cpp",
    version=__version__,
    author="Option Strategy Team",
    description="Module C++ optimisé pour les calculs de métriques de stratégies",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
    python_requires=">=3.8",
    install_requires=["pybind11>=2.6.0"],
)
