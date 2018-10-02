import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint, request, jsonify, redirect, send_file, make_response
from urllib import quote
from werkzeug.datastructures import FileStorage
import os
import uuid
import json
import datetime
from ckan.lib.plugins import DefaultTranslation


try:
    from ckanext.xloader.interfaces import IXloader
except ImportError:
    IXloader = None


def file_uploader_ui():
    package_id = request.form['package_id']
    package_show = toolkit.get_action('package_show')
    # this ensures current user is authorized to view the package
    package = package_show(data_dict={'name_or_id': package_id})
    assert package
    files = request.files.values()
    assert len(files) == 1
    file_storage = files[0] # type: FileStorage
    file_uuid = str(uuid.uuid4())
    file_path = os.path.join(toolkit.config.get('ckan.storage_path'), 'file_uploader_ui',
                             package_id, file_uuid)
    os.makedirs(file_path)
    file_storage.save(os.path.join(file_path, 'file'))
    with open(os.path.join(file_path, 'metadata'), 'w') as f:
        json.dump({'name': file_storage.filename, 'status': 'pending'}, f)
    file_extension = file_storage.filename.split('.')[-1]
    url = '{}/file_uploader_ui/download/{}/{}.{}'.format(toolkit.config.get('ckan.site_url'),
                                                         package_id,
                                                         file_uuid,
                                                         file_extension)
    return jsonify({'files': [{'name': file_storage.filename,
                               'url': url}]})


def file_uploader_download(package_id, file_id):
    package_show = toolkit.get_action('package_show')
    # this ensures current user is authorized to view the package
    package = package_show(data_dict={'name_or_id': package_id})
    assert package
    file_uuid = '.'.join(file_id.split('.')[:-1]) if '.' in file_id else file_id
    file_path = os.path.join(toolkit.config.get('ckan.storage_path'), 'file_uploader_ui',
                             package_id, file_uuid)
    with open(os.path.join(file_path, 'metadata')) as f:
        metadata = json.load(f)
        file_name = metadata['name']
        file_status = metadata.get('status', 'active')
    assert file_status == 'active', 'invalid file status: {}'.format(file_status)
    response = make_response(send_file(os.path.join(file_path, 'file')))
    response.headers["Content-Disposition"] = \
        "attachment;" \
        "filename*=UTF-8''{utf_filename}".format(
            utf_filename=quote(file_name.encode('utf-8'))
        )
    return response


def file_uploader_finish(package_id):
    package_show = toolkit.get_action('package_show')
    # this ensures current user is authorized to view the package
    package = package_show(data_dict={'name_or_id': package_id})
    assert package
    resource_create = toolkit.get_action('resource_create')
    package_path = os.path.join(toolkit.config.get('ckan.storage_path'), 'file_uploader_ui', package_id)
    file_metadatas = {}
    for file_uuid in os.listdir(package_path):
        file_path = os.path.join(package_path, file_uuid)
        with open(os.path.join(file_path, 'metadata')) as f:
            metadata = json.load(f)
            file_name = metadata['name']
            file_status = metadata.get('status', 'active')
        if file_status == 'pending':
            file_metadatas[file_path] = metadata
            with open(os.path.join(file_path, 'metadata'), 'w') as f:
                json.dump(dict(metadata, status='adding'), f)
            file_extension = file_name.split('.')[-1]
            url = '{}/file_uploader_ui/download/{}/{}.{}'.format(toolkit.config.get('ckan.site_url'),
                                                                 package_id,
                                                                 file_uuid,
                                                                 file_extension)
            resource_create(data_dict={'package_id': package_id,
                                       'name': file_name,
                                       'url': url,
                                       'last_modified': datetime.datetime.utcnow()})
    package_show = toolkit.get_action('package_show')
    package_update = toolkit.get_action('package_update')
    package = package_show(data_dict={'name_or_id': package_id})
    for file_path, file_metadata in file_metadatas.items():
        with open(os.path.join(file_path, 'metadata'), 'w') as f:
            json.dump(dict(file_metadata, status='active'), f)
    package['state'] = 'active'
    package_update(data_dict=package)
    return redirect('/dataset/{}'.format(package_id))


class File_Uploader_UiPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.ITranslation)
    if IXloader:
        plugins.implements(IXloader)

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
        blueprint.add_url_rule(u'/file_uploader_ui/download/<package_id>/<file_id>',
                               u'file_uploader_ui_download',
                               file_uploader_download,
                               methods=['GET'])
        return blueprint

    def modify_download_request(self, url, resource, api_key, headers):
        if 'file_uploader_ui' in url:
            headers['Authorization'] = api_key
        return url

    def can_upload(self, resource_id):
        return True

    def after_upload(self, context, resource_dict, dataset_dict):
        pass
