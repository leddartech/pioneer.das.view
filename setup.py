import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pioneer_das_view", # Replace with your own username
    version="0.0.1",
    author="Leddartech",
    description="Leddartech's das view",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    dependency_links=[
        "https://__token__:qcnZ-LPju8cqtpG1cpss@svleddar-gitlab.leddartech.local/api/v4/projects/481/packages/pypi/simple/pioneer-common",
        "https://__token__:qcnZ-LPju8cqtpG1cpss@svleddar-gitlab.leddartech.local/api/v4/projects/487/packages/pypi/simple/pioneer-das-api",
        "https://__token__:qcnZ-LPju8cqtpG1cpss@svleddar-gitlab.leddartech.local/api/v4/projects/488/packages/pypi/simple/pioneer-common-gui"
    ],
    install_requires=[
        'numpy',
        'matplotlib',
        'PyQt5>=5.14',
        'tqdm',
        'pyyaml',
        'pandas',
        'opencv-python',
        'pioneer-common',
        'pioneer-common-gui',
        'pioneer-das-api',
        'utm'
    ],
    include_package_data=True
)