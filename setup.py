from setuptools import setup, find_packages

setup(
    name="eBird2ABAP",
    version="0.2",
    author="Raphaël Nussbaumer",
    description="Create ABAP card from eBird data",
    packages=find_packages(),
    package_data={
        "eBird2ABAP": ["matched_species.csv"],
    },
    include_package_data=True,
    install_requires=["numpy", "pandas"],
)
