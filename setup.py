import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    lineiter = (line.strip() for line in open(filename))
    return [line for line in lineiter if line and not line.startswith("#")]

install_reqs = parse_requirements('requirements.txt')


setuptools.setup(
    name="pioneer_das_view", # Replace with your own username
    version="1.1.0",
    author="Leddartech",
    description="Leddartech's das view",
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
    install_requires=install_reqs,
    include_package_data = True,
    entry_points={
        'console_scripts': [
            'dasview = pioneer.das.view.apps.dasview:main',
        ],
    }
    
)