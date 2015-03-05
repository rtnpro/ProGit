# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8']
import pkg_resources

import json
import unittest
import shutil
import sys
import os

import pygit2
from mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '..'))

import progit.lib
import tests


class ProgitFlaskRepotests(tests.Modeltests):
    """ Tests for flask app controller of progit """

    def setUp(self):
        """ Set up the environnment, ran before every tests. """
        super(ProgitFlaskRepotests, self).setUp()

        progit.APP.config['TESTING'] = True
        progit.SESSION = self.session
        progit.ui.SESSION = self.session
        progit.ui.app.SESSION = self.session
        progit.ui.repo.SESSION = self.session

        progit.APP.config['GIT_FOLDER'] = tests.HERE
        progit.APP.config['FORK_FOLDER'] = os.path.join(
            tests.HERE, 'forks')
        progit.APP.config['TICKETS_FOLDER'] = os.path.join(
            tests.HERE, 'tickets')
        progit.APP.config['DOCS_FOLDER'] = os.path.join(
            tests.HERE, 'docs')
        self.app = progit.APP.test_client()

    def test_add_user(self):
        """ Test the add_user endpoint. """

        output = self.app.get('/foo/adduser')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.get('/foo/adduser')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.get('/test/adduser')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.get('/test/adduser')
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Add user</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'user': 'ralph',
            }

            output = self.app.post('/test/adduser', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Add user</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)

            data['csrf_token'] = csrf_token
            output = self.app.post('/test/adduser', data=data)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<h2>Add user</h2>' in output.data)
            self.assertTrue(
                '<li class="error">No user &#34;ralph&#34; found</li>'
                in output.data)

            data['user'] = 'foo'
            output = self.app.post(
                '/test/adduser', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<li class="message">User added</li>' in output.data)

    def test_remove_user(self):
        """ Test the remove_user endpoint. """

        output = self.app.post('/foo/dropuser/1')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.post('/foo/dropuser/1')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.post('/test/dropuser/1')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.post('/test/settings')

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {'csrf_token': csrf_token}

            output = self.app.post(
                '/test/dropuser/2', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<li class="error">User does not have commit or cannot '
                'loose it right</li>' in output.data)

        # Add an user to a project
        repo = progit.lib.get_project(self.session, 'test')
        msg = progit.lib.add_user_to_project(
            session=self.session,
            project=repo,
            user='foo',
        )
        self.session.commit()
        self.assertEqual(msg, 'User added')

        with tests.user_set(progit.APP, user):
            output = self.app.post('/test/dropuser/2', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)
            self.assertFalse(
                '<li class="message">User removed</li>' in output.data)

            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/dropuser/2', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<li class="message">User removed</li>' in output.data)

    def test_update_description(self):
        """ Test the update_description endpoint. """
        output = self.app.post('/foo/updatedesc')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.post('/foo/updatedesc')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)

            output = self.app.post('/test/updatedesc')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.post('/test/updatedesc', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {
                'description': 'new description for test project #1',
                'csrf_token': csrf_token,
            }
            output = self.app.post(
                '/test/updatedesc', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<li class="message">Description updated</li>'
                in output.data)

    def test_view_settings(self):
        """ Test the view_settings endpoint. """
        output = self.app.get('/foo/settings')
        self.assertEqual(output.status_code, 302)

        user = tests.FakeUser()
        with tests.user_set(progit.APP, user):
            output = self.app.get('/foo/settings')
            self.assertEqual(output.status_code, 404)

            tests.create_projects(self.session)
            tests.create_projects_git(tests.HERE)

            output = self.app.get('/test/settings')
            self.assertEqual(output.status_code, 403)

        user.username = 'pingou'
        with tests.user_set(progit.APP, user):
            output = self.app.get('/test/settings', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)
            # Both checkbox checked before
            self.assertTrue(
                '<input checked id="project_docs" name="project_docs" '
                'type="checkbox" value="y">' in output.data)
            self.assertTrue(
                '<input checked id="issue_tracker" name="issue_tracker" '
                'type="checkbox" value="y">' in output.data)

            csrf_token = output.data.split(
                'name="csrf_token" type="hidden" value="')[1].split('">')[0]

            data = {}
            output = self.app.post(
                '/test/settings', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)

            # Both checkbox are still checked
            output = self.app.get('/test/settings', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)
            self.assertTrue(
                '<input checked id="project_docs" name="project_docs" '
                'type="checkbox" value="y">' in output.data)
            self.assertTrue(
                '<input checked id="issue_tracker" name="issue_tracker" '
                'type="checkbox" value="y">' in output.data)

            data = {'csrf_token': csrf_token}
            output = self.app.post(
                '/test/settings', data=data, follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<p>test project #1</p>' in output.data)
            self.assertTrue(
                '<title>Overview - test - ProGit</title>' in output.data)
            self.assertTrue(
                '<li class="message">Edited successfully settings of '
                'repo: test</li>' in output.data)

            # Both checkbox are now un-checked
            output = self.app.get('/test/settings', follow_redirects=True)
            self.assertEqual(output.status_code, 200)
            self.assertTrue('<header class="repo">' in output.data)
            self.assertTrue('<h2>Settings</h2>' in output.data)
            self.assertTrue(
                '<ul id="flashes">\n                </ul>' in output.data)
            self.assertTrue(
                '<input id="project_docs" name="project_docs" '
                'type="checkbox" value="y">' in output.data)
            self.assertTrue(
                '<input id="issue_tracker" name="issue_tracker" '
                'type="checkbox" value="y">' in output.data)

    def test_view_forks(self):
        """ Test the view_forks endpoint. """

        output = self.app.get('/foo/forks')
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/forks')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('This project has not been forked.' in output.data)

    def test_view_repo(self):
        """ Test the view_repo endpoint. """

        output = self.app.get('/foo')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(tests.HERE)

        output = self.app.get('/test')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(tests.HERE, 'test.git'))
        tests.add_readme_git_repo(os.path.join(tests.HERE, 'test.git'))

        output = self.app.get('/test')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertFalse('Forked from' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 3)

        # Turn that repo into a fork
        repo = progit.lib.get_project(self.session, 'test')
        repo.parent_id = 2
        self.session.add(repo)
        self.session.commit()

        # View the repo in the UI
        output = self.app.get('/test')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test.git'))
        tests.add_readme_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test.git'))

        output = self.app.get('/fork/pingou/test')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue('Forked from' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 3)

        # Add a fork of a fork
        item = progit.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        output = self.app.get('/fork/pingou/test3')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue('<p>test project #3</p>' in output.data)
        self.assertTrue('Forked from' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 10)

    def test_view_repo_branch(self):
        """ Test the view_repo_branch endpoint. """

        output = self.app.get('/foo/branch/master')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/branch/master')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(tests.HERE)

        output = self.app.get('/test/branch/master')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(tests.HERE, 'test.git'))
        tests.add_readme_git_repo(os.path.join(tests.HERE, 'test.git'))

        output = self.app.get('/test/branch/master')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertFalse('Forked from' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 3)

        # Turn that repo into a fork
        repo = progit.lib.get_project(self.session, 'test')
        repo.parent_id = 2
        self.session.add(repo)
        self.session.commit()

        # View the repo in the UI
        output = self.app.get('/test/branch/master')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test.git'))
        tests.add_readme_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test.git'))

        output = self.app.get('/fork/pingou/test/branch/master')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue('Forked from' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 3)

        # Add a fork of a fork
        item = progit.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        output = self.app.get('/fork/pingou/test3/branch/master')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue('<p>test project #3</p>' in output.data)
        self.assertTrue('Forked from' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 10)

    def test_view_log(self):
        """ Test the view_log endpoint. """
        output = self.app.get('/foo/log')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/log')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(tests.HERE)

        output = self.app.get('/test/log')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(tests.HERE, 'test.git'))
        tests.add_readme_git_repo(os.path.join(tests.HERE, 'test.git'))

        output = self.app.get('/test/log')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertFalse('Forked from' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 3)

        # Turn that repo into a fork
        repo = progit.lib.get_project(self.session, 'test')
        repo.parent_id = 2
        self.session.add(repo)
        self.session.commit()

        # View the repo in the UI
        output = self.app.get('/test/log')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test.git'))
        tests.add_readme_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test.git'))

        output = self.app.get('/fork/pingou/test/log?page=abc')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue('<p>test project #1</p>' in output.data)
        self.assertTrue('Forked from' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 3)

        # Add a fork of a fork
        item = progit.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        output = self.app.get('/fork/pingou/test3/log/fobranch')
        self.assertEqual(output.status_code, 404)

        output = self.app.get('/fork/pingou/test3/log')
        self.assertEqual(output.status_code, 200)
        self.assertFalse('<p>This repo is brand new!</p>' in output.data)
        self.assertTrue('<p>test project #3</p>' in output.data)
        self.assertTrue('Forked from' in output.data)
        self.assertEqual(
            output.data.count('<span class="commitid">'), 13)

    def test_view_file(self):
        """ Test the view_file endpoint. """
        output = self.app.get('/foo/blob/foo/sources')
        # No project registered in the DB
        self.assertEqual(output.status_code, 404)

        tests.create_projects(self.session)

        output = self.app.get('/test/blob/foo/sources')
        # No git repo associated
        self.assertEqual(output.status_code, 404)

        tests.create_projects_git(tests.HERE)

        output = self.app.get('/test/blob/foo/sources')
        self.assertEqual(output.status_code, 404)

        # Add some content to the git repo
        tests.add_content_git_repo(os.path.join(tests.HERE, 'test.git'))
        tests.add_readme_git_repo(os.path.join(tests.HERE, 'test.git'))
        tests.add_binary_git_repo(
            os.path.join(tests.HERE, 'test.git'), 'test.jpg')
        tests.add_binary_git_repo(
            os.path.join(tests.HERE, 'test.git'), 'test_binary')

        output = self.app.get('/test/blob/master/foofile')
        self.assertEqual(output.status_code, 404)

        # View in a branch
        output = self.app.get('/test/blob/master/sources')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="file_content">' in output.data)
        self.assertTrue(
            '<tr><td class="cell1"><a id="_1" href="#_1">1</a></td>'
            in output.data)
        self.assertTrue(
            '<td class="cell2"><pre> bar</pre></td>' in output.data)

        # View what's supposed to be an image
        output = self.app.get('/test/blob/master/test.jpg')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="file_content">' in output.data)
        self.assertTrue(
            'Binary files cannot be rendered.<br/>' in output.data)

        # View by commit id
        repo = pygit2.init_repository(os.path.join(tests.HERE, 'test.git'))
        commit = repo.revparse_single('HEAD')

        output = self.app.get('/test/blob/%s/test.jpg' % commit.oid.hex)
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="file_content">' in output.data)
        self.assertTrue(
            'Binary files cannot be rendered.<br/>' in output.data)

        # View by image name -- somehow we support this
        output = self.app.get('/test/blob/sources/test.jpg')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="file_content">' in output.data)
        self.assertTrue(
            'Binary files cannot be rendered.<br/>'
            in output.data)

        # View binary file
        output = self.app.get('/test/blob/sources/test_binary')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="file_content">' in output.data)
        self.assertTrue(
            'Binary files cannot be rendered.<br/>'
            in output.data)

        # View folder
        output = self.app.get('/test/blob/master/folder1')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="tree_list">' in output.data)
        self.assertTrue('<h3>Tree</h3>' in output.data)
        self.assertTrue(
            '<a href="/test/blob/master/folder1/folder2">' in output.data)

        # View by image name -- with a non-existant file
        output = self.app.get('/test/blob/sources/testfoo.jpg')
        self.assertEqual(output.status_code, 404)
        output = self.app.get('/test/blob/master/folder1/testfoo.jpg')
        self.assertEqual(output.status_code, 404)

        # Add a fork of a fork
        item = progit.lib.model.Project(
            user_id=1,  # pingou
            name='test3',
            description='test project #3',
            parent_id=1,
        )
        self.session.add(item)
        self.session.commit()

        tests.add_content_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_readme_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'))
        tests.add_commit_git_repo(
            os.path.join(tests.HERE, 'forks', 'pingou', 'test3.git'),
            ncommits=10)

        output = self.app.get('/fork/pingou/test3/blob/master/sources')
        self.assertEqual(output.status_code, 200)
        self.assertTrue('<section class="file_content">' in output.data)
        self.assertTrue(
            '<tr><td class="cell1"><a id="_1" href="#_1">1</a></td>'
            in output.data)
        self.assertTrue(
            '<td class="cell2"><pre> barRow 0</pre></td>' in output.data)



if __name__ == '__main__':
    SUITE = unittest.TestLoader().loadTestsFromTestCase(ProgitFlaskRepotests)
    unittest.TextTestRunner(verbosity=2).run(SUITE)