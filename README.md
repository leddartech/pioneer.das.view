# pioneer.das.view

pioneer.das.view is a python application used to visualize leddartech's datasets.

## Pixset Dataset
[Pixset](dataset.leddartech.com) is the first dataset using the leddartech Pixell sensor. A solid state flash LiDAR that can provide full wave-form data. All the annotated frames of the dataset have been recorded in Montreal and Quebec city under various environmental conditions. 

A full description of the Pixset dataset can be found here: []()

We've also published a set of tools to help users in manipulating the dataset data. The das.view can be used to visualize and compared the data from different sensors in a Leddartech's dataset.


## Installation

The pioneer.das.view can be installed using the package manager pip.


```bash
pip install pioneer-das-view
```

When developing, you can link the repository to your python site-packages and enable hot-reloading of the package.
```bash
python3 setup.py develop --user
```

If you don't want to install all the dependencies on your computer, you can run it in a virtual environment
```bash
pipenv install --skip-lock

pipenv shell
```

## Usage

```bash
dasview /path/to/dataset

```

## Troubleshooting

**QOpenGLShader::link: error: no shaders attached to the program**

QOpenGLShaderProgram::uniformLocation(backColor): shader program is not linked
QOpenGLShaderProgram::uniformLocation(color): shader program is not linked
QOpenGLShader::link: error: no shaders attached to the program

If you encounter this error, update your drivers
```
sudo ubuntu-drivers autoinstall
```

**module not found open3d.open3d_pybind**

You need to fix the open3d version to 0.10
```
pip3 uninstall open3d
pip3 install open3d==0.10
```
