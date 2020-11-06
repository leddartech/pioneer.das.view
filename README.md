# pioneer.das.view

pioneer.das.view is a python application used to visualize leddartech's datasets.

## Installation

Before installing, you should add to your pip.conf file the gitlab pypi server url to trust.

```conf
[global]
extra-index-url = https://pioneer:yK6RUkhUCNHg3e1yxGT4@svleddar-gitlab.leddartech.local/api/v4/projects/481/packages/pypi/simple
                  https://pioneer:yK6RUkhUCNHg3e1yxGT4@svleddar-gitlab.leddartech.local/api/v4/projects/487/packages/pypi/simple
                  https://pioneer:yK6RUkhUCNHg3e1yxGT4@svleddar-gitlab.leddartech.local/api/v4/projects/488/packages/pypi/simple
                  https://pioneer:yK6RUkhUCNHg3e1yxGT4@svleddar-gitlab.leddartech.local/api/v4/projects/493/packages/pypi/simple
trusted-host = svleddar-gitlab.leddartech.local
```

Use the package manager [pip](https://pioneer:yK6RUkhUCNHg3e1yxGT4@svleddar-gitlab.leddartech.local/api/v4/projects/493/packages/pypi/simple/pioneer-das-view) to install pioneer.das.view .

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

```python
pipenv install --skip-lock

pipenv run python ./pioneer/das/view/apps/dasview.py /path/to/dataset

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
