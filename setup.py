from setuptools import setup, find_packages

# Read requirements from requirements.txt
with open("requirements.txt") as f:
    required_packages = f.read().splitlines()

setup(
    name="eBird2ABAP",
    version="0.1",
    author="Raphaël Nussbaumer",
    description="Create ABAP card from eBird data",
    packages=find_packages(),
    package_data={
        "eBird2ABAP": ["data/species_list/matched_species.csv"],
    },
    include_package_data=True,
    install_requires=required_packages,
)
