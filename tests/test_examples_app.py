# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016, 2017 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.


"""Example apps test."""
import json
import os
import signal
import subprocess
import time

import pytest


@pytest.yield_fixture
def example_app():
    """Example app fixture."""
    current_dir = os.getcwd()
    # go to example directory
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exampleappdir = os.path.join(project_dir, 'examples')
    os.chdir(exampleappdir)
    # setup example
    cmd = './app-setup.sh'
    exit_status = subprocess.call(cmd, shell=True)
    assert exit_status == 0
    # Starting example web app
    cmd = 'FLASK_APP=app.py flask run --debugger -p 5000'
    webapp = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                              preexec_fn=os.setsid, shell=True)
    time.sleep(20)
    # return webapp
    yield webapp
    # stop server
    os.killpg(webapp.pid, signal.SIGTERM)
    # tear down example app
    cmd = './app-teardown.sh'
    subprocess.call(cmd, shell=True)
    # return to the original directory
    os.chdir(current_dir)
    cmd = 'pip install -e .[all]'
    subprocess.call(cmd, shell=True)


def test_example_app(example_app):
    """Test example app."""
    # load fixtures
    cmd = './app-fixtures.sh'
    exit_status = subprocess.call(cmd, shell=True)
    assert exit_status == 0

    time.sleep(20)

    # admin page
    cmd = 'curl http://localhost:5000/circulation/'
    output = subprocess.check_output(cmd, shell=True).decode('utf-8')
    assert 'invenio-search-results' in output

    # item search API
    cmd = 'curl http://localhost:5000/api/circulation/items/'
    output = json.loads(
        subprocess.check_output(cmd, shell=True).decode('utf-8')
    )
    assert len(output['hits']['hits']) > 0

    # item revision search API
    cmd = 'curl http://localhost:5000/api/circulation/item_revisions/'
    output = json.loads(
        subprocess.check_output(cmd, shell=True).decode('utf-8')
    )
    assert output and 'hits' in output and 'hits' in output['hits']

    # user hub page
    cmd = 'curl http://localhost:5000/circulation/user/'
    output = subprocess.check_output(cmd, shell=True).decode('utf-8')
    assert 'circulation-user-holdings' in output

    # admin user hub page
    cmd = 'curl http://localhost:5000/circulation/admin/user/1'
    output = subprocess.check_output(cmd, shell=True).decode('utf-8')
    assert 'user-info' in output and 'circulation-user-holdings' in output

    cmd = 'curl http://localhost:5000/circulation/admin/user/1000'
    output = subprocess.check_output(cmd, shell=True).decode('utf-8')
    assert output == ''
