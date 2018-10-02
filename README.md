# ckanext-file_uploader_ui

Enhance the [CKAN]() file uploading UI with the following features:

* Upload multiple files at once
* Drag & Drop files

Minimal supported CKAN version: 2.8.1

## Installation

* Activate your CKAN virtual environment
* Install the ckanext-file_uploader_ui package into your virtual environment:
  * `pip install ckanext-file_uploader_ui`
* If you are using [xloader](https://github.com/ckan/ckanext-xloader) to load data into the datastore
  * install this version of xloader (until [this PR](https://github.com/ckan/ckanext-xloader/pull/44) is merged)
  * `pip install -U https://github.com/OriHoch/ckanext-xloader/archive/support-modifying-download-request.zip#egg=ckanext-xloader`
* Add ``file_uploader_ui`` to the ``ckan.plugins`` setting in your CKAN
* Restart CKAN.

## Translations

Translations are done in Transifex: https://www.transifex.com/the-public-knowledge-workshop/ckanext-file_uploader_ui

### Updating translations code

Update the .pot file - should be done in case of additional / modified strings in the templates

```
python setup.py extract_messages
```

Edit the .pot file and remove core ckan strings (which are there only because of extending core ckan templates)

Leave only strings unique to odata.

Translate and update the translations under i18n

Compile translated po files

```
python setup.py compile_catalog
```

## Updating the package on PYPI

Update the version in `VERSION.txt`, then build and upload:

```
python setup.py sdist &&\
twine upload dist/ckanext-file_uploader_ui-$(cat VERSION.txt).tar.gz
```

ckanext-file_uploader_ui should be availabe on PyPI as https://pypi.python.org/pypi/ckanext-file_uploader_ui.
