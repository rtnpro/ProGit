# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

API namespace version 0.

"""

import flask

API = flask.Blueprint('api_ns', __name__, url_prefix='/api/0')


from progit import __api_version__, APP, SESSION
import progit
import progit.lib


@API.route('/version/')
@API.route('/version')
def api_version():
    '''
    API Version
    -----------
    Display the most recent api version.

    ::

        /api/version

    Accepts GET queries only.

    Sample response:

    ::

        {
          "version": "1"
        }

    '''
    return flask.jsonify({'version': __api_version__})


@API.route('/users/')
@API.route('/users')
def api_users():
    '''
    List users
    -----------
    Returns the list of all users that have logged into this progit instances.
    This can then be used as input for autocompletion in some forms/fields.

    ::

        /api/users

    Accepts GET queries only.

    Sample response:

    ::

        {
          "users": ["user1", "user2"]
        }

    '''
    pattern = flask.request.args.get('pattern', None)
    if pattern is not None and not pattern.endswith('*'):
        pattern += '*'

    return flask.jsonify(
        {
            'users': [
                user.username
                for user in progit.lib.search_user(
                    SESSION, pattern=pattern)
            ]
        }
    )


@API.route('/<repo>/tags')
@API.route('/<repo>/tags/')
@API.route('/fork/<username>/<repo>/tags')
@API.route('/fork/<username>/<repo>/tags/')
def api_project_tags(repo, username=None):
    '''
    List all the tags of a project
    ------------------------------
    Returns the list of all tags of the specified project.

    ::

        /api/<repo>/tags

        /api/fork/<username>/<repo>/tags

    Accepts GET queries only.

    Sample response:

    ::

        {
          "tags": ["tag1", "tag2"]
        }

    '''
    pattern = flask.request.args.get('pattern', None)
    if pattern is not None and not pattern.endswith('*'):
        pattern += '*'

    project = progit.lib.get_project(SESSION, repo, username)
    if not project:
        output = {'output': 'notok', 'error': 'Project not found'}
        jsonout = flask.jsonify(output)
        jsonout.status_code = 404
        return jsonout

    return flask.jsonify(
        {
            'tags': [
                tag.tag
                for tag in progit.lib.get_tags_of_project(
                    SESSION, project, pattern=pattern)
            ]
        }
    )
