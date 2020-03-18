import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckanext.scheming.helpers import scheming_get_dataset_schema
from ckan.lib.helpers import flash_success
from ckan.common import _
from flask import Blueprint, request, jsonify, redirect, send_file, make_response
from urllib import quote
from werkzeug.datastructures import FileStorage
import os
import uuid
import json
import datetime
import logging
from ckan.lib.plugins import DefaultTranslation

log = logging.getLogger()

try:
    from ckanext.xloader.interfaces import IXloader
except ImportError:
    IXloader = None


def file_uploader_ui():
    package_id = request.form['package_id']
    package_show = toolkit.get_action('package_show')
    # this ensures current user is authorized to view the package
    package = package_show(data_dict={'name_or_id': package_id})
    package_id = package['id']
    assert package
    files = request.files.values()
    assert len(files) == 1
    file_storage = files[0] # type: FileStorage
    file_uuid = str(uuid.uuid4())
    file_path = os.path.join(
        toolkit.config.get('ckan.storage_path'),
        toolkit.config.get('ckanext.file_uploader_ui_path', 'file_uploader_ui'),
        package_id,
        file_uuid
    )
    # Keep these logs appearing in production for the Jan 2020 West Africa meet
    log.warning("Bulk uploading file to path: {}".format(file_path))

    os.makedirs(file_path)
    file_storage.save(os.path.join(file_path, 'file'))
    with open(os.path.join(file_path, 'metadata'), 'w') as f:
        json.dump({'name': file_storage.filename, 'status': 'pending'}, f)
    file_extension = file_storage.filename.split('.')[-1]
    url = '{}/file_uploader_ui/download/{}/{}.{}'.format(
        toolkit.config.get('ckan.site_url'),
        package_id,
        file_uuid,
        file_extension
    )
    return jsonify(
        {'files': [{'name': file_storage.filename, 'url': url}]}
    )


def file_uploader_download(package_id, file_id):
    package_show = toolkit.get_action('package_show')
    # this ensures current user is authorized to view the package
    package = package_show(data_dict={'name_or_id': package_id})
    package_id = package['id']
    assert package
    file_uuid = '.'.join(file_id.split('.')[:-1]) if '.' in file_id else file_id
    file_path = os.path.join(
        toolkit.config.get('ckan.storage_path'),
        toolkit.config.get('ckanext.file_uploader_ui_path', 'file_uploader_ui'),
        package_id,
        file_uuid
    )
    # Keep these logs appearing in production for the Jan 2020 West Africa meet
    log.warning("Downloading file from path: {}".format(file_path))
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
    file_metadatas = {}
    uploads = {'updated': [], 'created': []}
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
            url = '{}/file_uploader_ui/download/{}/{}.{}'.format(
                toolkit.config.get('ckan.site_url'),
                package_id,
                file_uuid,
                file_extension
            )
            resources = [r['name'] for r in package['resources']]
            if resources.count(file_name) == 1:
                # Update existing resource instead of adding new resource.
                resource_update = toolkit.get_action('resource_update')
                resource = filter(
                    lambda x: x['name'] == file_name,
                    package['resources']
                )[0]
                resource_update(data_dict={
                    'id': resource['id'],
                    'package_id': package_id,
                    'last_modified': datetime.datetime.utcnow(),
                    "revision_id": str(uuid.uuid4()),
                    'url': url
                })
                uploads['updated'].append(file_name)
            else:
                data_dict = {
                    'package_id': package_id,
                    'name': file_name,
                    'url': url,
                    'url_type': "file_uploader_ui",
                    'last_modified': datetime.datetime.utcnow()
                }
                data_dict = _merge_with_configured_defaults(data_dict)
                data_dict = _merge_with_schema_default_values(
                    package_type,
                    resource_type,
                    data_dict
                )
                resource_create(data_dict=data_dict)
                uploads['created'].append(file_name)

    package_show = toolkit.get_action('package_show')
    package_update = toolkit.get_action('package_update')
    package = package_show(data_dict={'name_or_id': package_id})
    for file_path, file_metadata in file_metadatas.items():
        with open(os.path.join(file_path, 'metadata'), 'w') as f:
            json.dump(dict(file_metadata, status='active'), f)
    package['state'] = 'active'
    package_update(data_dict=package)
    if uploads['created']:
        flash_success(_('The following resources were created: {}').format(
            ', '.join(uploads['created'])
        ))
    if uploads['updated']:
        flash_success(_('The following resources were updated: {}').format(
            ', '.join(uploads['updated'])
        ))

    return redirect("/{}/dataset/{}".format(
        request.environ.get('CKAN_LANG'),
        package_id
    ))


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


def _merge_with_schema_default_values(package_type, resource_type, data_dict):
    """
    This function merges the file uploader default resource with the default
    values specified in the ckanext-schemining schema. It allows us to bulk
    upload multiple copies ofa particular resource type e.g. multiple spectrum
    files.
    """
    # If no package_type or resource_type we can't do this.
    if not (package_type and resource_type):
        return data_dict

    schema = scheming_get_dataset_schema(package_type)
    resource_schemas = schema.get("resource_schemas", {})
    resource_schema = resource_schemas.get(resource_type, {})
    file_name = data_dict['name']

    # Step through each field and merge in the default value if it exits.
    for field in resource_schema.get('resource_fields', []):
        if field['field_name'] == 'restricted':
            # TODO: Would be nice if restricted didn't need special treatment
            data_dict["restricted_allowed_users"] = field.get('default_users', "")
            data_dict["restricted_allowed_orgs"] = field.get('default_organizations', "")
        value = field.get('default', field.get('field_value'))
        if value:
            data_dict[field['field_name']] = value

    # Multiple resources with the same name is confusing, so merge in filename
    data_dict['name'] = "{}: {}".format(
        data_dict.get('name', ""),
        file_name
    )
    return data_dict


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
        blueprint.add_url_rule(u'/file_uploader_ui/finish/<package_id>/<package_type>/<resource_type>',
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
