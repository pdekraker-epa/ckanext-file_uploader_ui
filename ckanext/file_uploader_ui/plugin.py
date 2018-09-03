import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint, request, jsonify
import json


def file_uploader_ui():
    resource_create = toolkit.get_action('resource_create')
    package_id = request.form['package_id']
    files = request.files.values()
    assert len(files) == 1
    resource = resource_create(data_dict={'package_id': package_id,
                                          'url': files[0].filename,
                                          'name': files[0].filename,
                                          'upload': files[0]})
    return jsonify({'files': [{'name': resource['name'],
                               'url': resource['url']}]})


class File_Uploader_UiPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'file_uploader_ui')

    def get_blueprint(self):
        blueprint = Blueprint(self.name, self.__module__)
        blueprint.template_folder = u'templates'
        blueprint.add_url_rule(u'/file_uploader_ui/upload',
                               u'file_uploader_ui_upload',
                               file_uploader_ui,
                               methods=['POST'])
        return blueprint
