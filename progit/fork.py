#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask
import os
from math import ceil

import pygit2
from sqlalchemy.exc import SQLAlchemyError
from pygments import highlight
from pygments.lexers import guess_lexer
from pygments.lexers.text import DiffLexer
from pygments.formatters import HtmlFormatter


from progit import APP, SESSION, LOG


### Application
@APP.route('/fork/<repo>')
def fork_project(repo):
    """ Fork the project specified into the user's namespace
    """
    reponame = os.path.join(APP.config['GIT_FOLDER'], repo)
    if not os.path.exists(reponame):
        flask.abort(404)

    forkreponame = os.path.join(
        APP.config['FORK_FOLDER'],
        flask.g.fas_user.username,
        repo)

    if os.path.exists(forkreponame):
        flask.flash('Repo "%s/%s" already exists' % (
            flask.g.fas_user.username, repo))
    else:
        pygit2.clone_repository(reponame, forkreponame)
        flask.flash('Repo "%s" cloned to "%s/%s"' % (
            repo, flask.g.fas_user.username, repo))

    return flask.redirect(
        flask.url_for('view_user', username=flask.g.fas_user.username)
    )


@APP.route('/fork/<username>/<repo>')
def view_fork_repo(username, repo):
    """ Front page of a specific repo.
    """
    reponame = os.path.join(APP.config['FORK_FOLDER'], username, repo)
    if not os.path.exists(reponame):
        flask.abort(404)
    repo_obj = pygit2.Repository(reponame)

    cnt = 0
    last_commits = []
    for commit in repo_obj.walk(repo_obj.head.target, pygit2.GIT_SORT_TIME):
        last_commits.append(commit)
        cnt += 1
        if cnt == 10:
            break

    return flask.render_template(
        'repo_info.html',
        repo=repo,
        username=username,
        branches=sorted(repo_obj.listall_branches()),
        branchname='master',
        last_commits=last_commits,
        tree=sorted(last_commits[0].tree, key=lambda x: x.filemode),
    )


@APP.route('/fork/<username>/<repo>/branch/<branchname>')
def view_fork_repo_branch(username, repo, branchname):
    """ Displays the information about a specific branch.
    """
    reponame = os.path.join(APP.config['FORK_FOLDER'], username, repo)
    if not os.path.exists(reponame):
        flask.abort(404)
    repo_obj = pygit2.Repository(reponame)

    if not branchname in repo_obj.listall_branches():
        flask.abort(404)

    branch = repo_obj.lookup_branch(branchname)

    cnt = 0
    last_commits = []
    for commit in repo_obj.walk(branch.get_object().hex, pygit2.GIT_SORT_TIME):
        last_commits.append(commit)
        cnt += 1
        if cnt == 10:
            break

    return flask.render_template(
        'repo_info.html',
        repo=repo,
        username=username,
        branches=sorted(repo_obj.listall_branches()),
        branchname=branchname,
        last_commits=last_commits,
        tree=sorted(last_commits[0].tree, key=lambda x: x.filemode),
    )


@APP.route('/fork/<username>/<repo>/log')
@APP.route('/fork/<username>/<repo>/log/<branchname>')
def view_fork_log(username, repo, branchname=None):
    """ Displays the logs of the specified repo.
    """
    reponame = os.path.join(APP.config['FORK_FOLDER'], username, repo)
    if not os.path.exists(reponame):
        flask.abort(404)
    repo_obj = pygit2.Repository(reponame)

    if branchname and not branchname in repo_obj.listall_branches():
        flask.abort(404)

    if branchname:
        branch = repo_obj.lookup_branch(branchname)
    else:
        branch = repo_obj.lookup_branch('master')

    try:
        page = int(flask.request.args.get('page', 1))
    except ValueError:
        page = 1

    limit = APP.config['ITEM_PER_PAGE']
    start = limit * (page - 1)
    end = limit * page

    n_commits = 0
    last_commits = []
    for commit in repo_obj.walk(
            branch.get_object().hex, pygit2.GIT_SORT_TIME):
        if n_commits >= start and n_commits <= end:
            last_commits.append(commit)
        n_commits += 1

    total_page = int(ceil(n_commits / float(limit)))

    return flask.render_template(
        'repo_info.html',
        origin='view_fork_log',
        repo=repo,
        username=username,
        branches=sorted(repo_obj.listall_branches()),
        branchname=branchname,
        last_commits=last_commits,
        page=page,
        total_page=total_page,
    )


@APP.route('/fork/<username>/<repo>/blob/<identifier>/<path:filename>')
@APP.route('/fork/<username>/<repo>/blob/<identifier>/<path:filename>')
def view_fork_file(username, repo, identifier, filename):
    """ Displays the content of a file or a tree for the specified repo.
    """
    reponame = os.path.join(APP.config['FORK_FOLDER'], username, repo)
    if not os.path.exists(reponame):
        flask.abort(404)
    repo_obj = pygit2.Repository(reponame)

    if identifier in repo_obj.listall_branches():
        branchname = identifier
        branch = repo_obj.lookup_branch(identifier)
        commit = branch.get_object()
    else:
        try:
            commit = repo_obj.get(identifier)
            branchname = identifier
        except ValueError:
            # If it's not a commit id then it's part of the filename
            commit = repo_obj[repo_obj.head.target]
            branchname = 'master'

    def __get_file_in_tree(tree, filepath):
        ''' Retrieve the entry corresponding to the provided filename in a
        given tree.
        '''
        filename = filepath[0]
        if isinstance(tree, pygit2.Blob):
            return
        for el in tree:
            if el.name == filename:
                if len(filepath) == 1:
                    return repo_obj[el.oid]
                else:
                    return __get_file_in_tree(repo_obj[el.oid], filepath[1:])

    content = __get_file_in_tree(commit.tree, filename.split('/'))
    if not content:
        flask.abort(404, 'File not found')

    content = repo_obj[content.oid]
    if isinstance(content, pygit2.Blob):
        content = highlight(
            content.data,
            guess_lexer(content.data),
            HtmlFormatter(
                noclasses=True,
                style="tango",)
        )
        output_type = 'file'
    else:
        content = sorted(content, key=lambda x: x.filemode)
        output_type = 'tree'

    return flask.render_template(
        'file.html',
        repo=repo,
        username=username,
        branchname=branchname,
        filename=filename,
        content=content,
        output_type=output_type,
    )


@APP.route('/fork/<username>/<repo>/<commitid>')
def view_fork_commit(username, repo, commitid):
    """ Render a commit in a repo
    """
    reponame = os.path.join(APP.config['FORK_FOLDER'], username, repo)
    if not os.path.exists(reponame):
        flask.abort(404)
    repo_obj = pygit2.Repository(reponame)

    try:
        commit = repo_obj.get(commitid)
    except ValueError:
        flask.abort(404)

    if commit.parents:
        diff = commit.tree.diff_to_tree()

        parent = repo_obj.revparse_single('%s^' % commitid)
        diff = repo_obj.diff(parent, commit)
    else:
        # First commit in the repo
        diff = commit.tree.diff_to_tree(swap=True)

    html_diff = highlight(
        diff.patch,
        DiffLexer(),
        HtmlFormatter(
            noclasses=True,
            style="tango",)
    )

    return flask.render_template(
        'commit.html',
        repo=repo,
        username=username,
        commitid=commitid,
        commit=commit,
        diff=diff,
        html_diff=html_diff,
    )


@APP.route('/fork/<username>/<repo>/tree/')
@APP.route('/fork/<username>/<repo>/tree/<identifier>')
def view_fork_tree(username, repo, identifier=None):
    """ Render the tree of the repo
    """
    reponame = os.path.join(APP.config['FORK_FOLDER'], username, repo)
    if not os.path.exists(reponame):
        flask.abort(404)
    repo_obj = pygit2.Repository(reponame)

    if identifier in repo_obj.listall_branches():
        branchname = identifier
        branch = repo_obj.lookup_branch(identifier)
        commit = branch.get_object()
    else:
        try:
            commit = repo_obj.get(identifier)
            branchname = identifier
        except (ValueError, TypeError):
            # If it's not a commit id then it's part of the filename
            commit = repo_obj[repo_obj.head.target]
            branchname = 'master'

    content = sorted(commit.tree, key=lambda x: x.filemode)
    output_type = 'tree'

    return flask.render_template(
        'file.html',
        repo=repo,
        username=username,
        branchname=branchname,
        filename='',
        content=content,
        output_type=output_type,
    )