from setuptools import setup


setup(
    name='cldfbench_gasttdir',
    py_modules=['cldfbench_gasttdir'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'cldfbench.dataset': [
            'gasttdir=cldfbench_gasttdir:Dataset',
        ]
    },
    install_requires=[
        'cldfbench[glottolog,excel]',
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
