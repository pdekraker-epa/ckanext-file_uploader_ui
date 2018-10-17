#!/usr/bin/env bash

if [ "${1}" == "--update-translations" ]; then
    tx pull --all &&\
    msgfmt -o ckanext/file_uploader_ui/i18n/ar/LC_MESSAGES/ckanext-file_uploader_ui.mo \
          ckanext/file_uploader_ui/i18n/ar/LC_MESSAGES/ckanext-file_uploader_ui.po &&\
    msgfmt -o ckanext/file_uploader_ui/i18n/he/LC_MESSAGES/ckanext-file_uploader_ui.mo \
              ckanext/file_uploader_ui/i18n/he/LC_MESSAGES/ckanext-file_uploader_ui.po

else
    VERSION_LABEL="${1}"

    [ "${VERSION_LABEL}" == "" ] \
        && echo Missing version label \
        && echo current VERSION.txt = $(cat VERSION.txt) \
        && exit 1

    echo "${VERSION_LABEL}" > VERSION.txt &&\
    python setup.py sdist &&\
    twine upload dist/ckanext-file_uploader_ui-${VERSION_LABEL}.tar.gz &&\
    echo ckanext-file_uploader_ui-${VERSION_LABEL} &&\
    echo Great Success &&\
    exit 0

    exit 1

fi
