import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as h

from ckan.common import _
from flask import Blueprint, request, jsonify, redirect, send_file, make_response

from werkzeug.datastructures import FileStorage, ContentRange
from werkzeug.http import parse_content_range_header

import os
import uuid
import json
import datetime
import logging
from ckan.lib.plugins import DefaultTranslation

log = logging.getLogger(__name__)


def file_uploader_ui():
    package_id = request.form['package_id']
    package_show = toolkit.get_action('package_show')
    # this ensures current user is authorized to view the package
    package = package_show(data_dict={'name_or_id': package_id})
    package_id = package['id']
    assert package

    file_storage = request.files['files[]'] # type: FileStorage
    file_range = parse_content_range_header(request.headers.get('Content-Range'))

    if file_range:
        log.debug("File Uploader Received File: %s [%d / %d]",file_storage.filename, file_range.stop, file_range.length)
    else:
        log.debug("File Uploader Received File: %s",file_storage.filename)

    storage_path = os.path.join(
        toolkit.config.get('ckan.storage_path'),
        toolkit.config.get('ckanext.file_uploader_ui_path', 'file_uploader_ui'),
        package_id)
    # Keep these logs appearing in production for the Jan 2020 West Africa meet

    try:
        os.makedirs(storage_path)
    except OSError as e:
        # errno 17 is file already exists
        if e.errno != 17:
            raise

    file_path = os.path.join(storage_path, file_storage.filename)

    try:

        if 0 and os.path.exists(file_path) and file_range.start == 0:
            # Abort if file exists already
            return toolkit.abort(400, 'File with that name already in progress')
        elif file_range is None or file_range.start == 0:
            log.debug("Bulk uploading to temporary file %s",file_path)
            with open(file_path, 'wb') as f:
                f.write(file_storage.stream.read())
        else:
            with open(file_path, 'ab') as f:
                f.seek(file_range.start)
                f.write(file_storage.stream.read())

    except OSError:
        # log.exception will include the traceback so we can see what's wrong
        log.exception('Failed to write content to file %s',file_path)
        return toolkit.abort(500, 'File upload failed')

    return jsonify({'files': [{'name': file_storage.filename, 'size':os.path.getsize(file_path)}]})


def file_uploader_finish(package_id, package_type=None, resource_type=None):
    package_show = toolkit.get_action('package_show')
    # this ensures current user is authorized to view the package
    package = package_show(data_dict={'name_or_id': package_id})
    assert package
    package_id = package['id']
    resource_create = toolkit.get_action('resource_create')
    package_path = os.path.join(
        toolkit.config.get('ckan.storage_path'),
        toolkit.config.get('ckanext.file_uploader_ui_path', 'file_uploader_ui'),
        package_id
    )

    log.info("Adding bulk uploaded files to dataset %s",package_id)

    uploads = []
    for file_name in os.listdir(package_path):
        file_path = os.path.join(package_path, file_name)
        with open(file_path,'rb') as f:
            file_upload_storage = FileStorage(f)
            data_dict = {
                'package_id': package_id,
                'name': file_name,
                'upload': file_upload_storage,
                'last_modified': datetime.datetime.utcnow() }
            data_dict = _merge_with_configured_defaults(data_dict)
            resource_create(data_dict=data_dict)
            uploads.append(file_name)
        os.remove(file_path)

    if uploads:
        h.flash_success(_('The following resources were created: {}').format(', '.join(uploads)))

    return toolkit.redirect_to('dataset.resources', id=package_id)


def _merge_with_configured_defaults(data_dict):
    """
    Allow configurable default values for resource properties created through
    file uploader. These are configured through a json string in the config.
    """
    defaults = toolkit.config.get('ckanext.file_uploader_ui_defaults', "")
    if defaults:
        defaults = json.loads(defaults)
        for key, value in defaults.items():
            data_dict[key] = value
    return data_dict


def file_uploader_add_resources(package_id):
    package_show = toolkit.get_action('package_show')
    package = package_show(data_dict={'name_or_id': package_id})
    package_patch = toolkit.get_action('package_patch')
    package_patch(data_dict={ 'id':package['id'], 'state': 'active'})

    return toolkit.redirect_to('dataset.resources', id=package['id'])


class File_Uploader_UiPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.ITranslation)

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'file_uploader_ui')

    def i18n_domain(self):
        return 'ckanext-file_uploader_ui'

    def get_blueprint(self):
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates'
        blueprint.add_url_rule(u'/file_uploader_ui/upload',
                               u'file_uploader_ui_upload',
                               file_uploader_ui,
                               methods=['POST'])
        blueprint.add_url_rule(u'/file_uploader_ui/finish/<package_id>',
                               u'file_uploader_ui_finish',
                               file_uploader_finish,
                               methods=['GET'])
        blueprint.add_url_rule(u'/file_uploader_ui/add_resources/<package_id>',
                               u'file_uploader_ui_add_resources',
                               file_uploader_add_resources,
                               methods=['GET'])

        return blueprint

