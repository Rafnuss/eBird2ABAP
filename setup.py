from setuptools import setup, find_packages

# Use README.md for the long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="eBird2ABAP",
    version="0.2.1",
    author="Raphaël Nussbaumer",
    description="Create ABAP card from eBird data",
    long_description=long_description,
    long_description_content_type="text/markdown",  # Specify Markdown
    packages=find_packages(),
    package_data={
        "eBird2ABAP": ["matched_species.csv"],
    },
    include_package_data=True,
    install_requires=["numpy", "pandas"],
)
