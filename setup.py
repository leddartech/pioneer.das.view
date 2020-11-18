import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pioneer_das_view", # Replace with your own username
    version="0.4.0",
    author="Leddartech",
    description="Leddartech's das view",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=[
        'pioneer',
        'pioneer.das',
        'pioneer.das.view',
        'pioneer.das.view.apps',
        'pioneer.das.view.qml',
        'pioneer.das.view.qml.Das',
        'pioneer.das.view.windows'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    dependency_links=[
        "https://pioneer:yK6RUkhUCNHg3e1yxGT4@svleddar-gitlab.leddartech.local/api/v4/projects/481/packages/pypi/simple/pioneer-common",
        "https://pioneer:yK6RUkhUCNHg3e1yxGT4@svleddar-gitlab.leddartech.local/api/v4/projects/487/packages/pypi/simple/pioneer-das-api",
        "https://pioneer:yK6RUkhUCNHg3e1yxGT4@svleddar-gitlab.leddartech.local/api/v4/projects/488/packages/pypi/simple/pioneer-common-gui"
    ],
    install_requires=[
        'numpy',
        'matplotlib',
        'PyQt5==5.14',
        'tqdm',
        'pyyaml',
        'pandas',
        'opencv-python',
        'pioneer-common>=0.4',
        'pioneer-common-gui>=0.1',
        'pioneer-das-api>=0.4',
        'utm',
        'docopt'
    ],
    include_package_data = True
)