# ckanext-file_uploader_ui

Enhance the [CKAN]() file uploading UI with the following features:

* Upload multiple files at once
* Drag & Drop files

Minimal supported CKAN version: 2.8.1

## Installation

* Activate your CKAN virtual environment
* Install the ckanext-file_uploader_ui package into your virtual environment:
  * `pip install ckanext-file_uploader_ui`
* Add ``file_uploader_ui`` to the ``ckan.plugins`` setting in your CKAN
* Restart CKAN.

## Updating the package on PYPI

Update the version in `VERSION.txt`, then build and upload:

```
python setup.py sdist &&\
twine upload dist/ckanext-file_uploader_ui-$(cat VERSION.txt).tar.gz
```

ckanext-file_uploader_ui should be availabe on PyPI as https://pypi.python.org/pypi/ckanext-file_uploader_ui.
