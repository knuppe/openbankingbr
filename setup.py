import setuptools

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

info = dict()
with open('src/openbankingbr/__version__.py', 'r') as f:
    lines = f.readlines()
    for line in lines:
        if ' = ' in line:
            key = line.split(' = ')[0]
            val = line.split(' = ')[1]
            val = val.rstrip('\t\r\n\'').lstrip('\t\'')
            info[key] = val

setuptools.setup(
    name="openbankingbr",
    version=info['__version__'],
    author=info['__author__'],
    author_email=info['__author_email__'],
    description=info['__description__'],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/knuppe/openbankingbr",
    project_urls={
        "Bug Tracker": "https://github.com/knuppe/openbankingbr/issues",
    },    
    license='MIT',
    packages=setuptools.find_packages(where="src"),    
    install_requires=[
        "requests"
    ],
    keywords=['openbanking', 'bacen', 'banco-central-brasil'],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: Portuguese (Brazilian)",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    python_requires=">=3.6",
)
