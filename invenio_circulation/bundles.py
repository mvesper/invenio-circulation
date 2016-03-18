# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2014, 2015 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Circulation bundles."""

from __future__ import unicode_literals

from invenio_theme.bundles import js as _js

from invenio_assets import NpmBundle, RequireJSFilter


js_circulation = NpmBundle(
    "js/circulation/circulation_init.js",
    output="gen/circulation.%(version)s.js",
    filters=RequireJSFilter(exclude=[_js.contents[1]]),
    npm={'cal-heatmap': 'latest',
         'd3': 'latest',
         'bootstrap-datepicker': 'latest'},
)

js_entity = NpmBundle(
    "js/circulation/entity_init.js",
    output="gen/entity%(version)s.js",
    filters=RequireJSFilter(exclude=[_js.contents[1]]),
    npm={'cal-heatmap': 'latest',
         'd3': 'latest',
         'bootstrap-datepicker': 'latest',
         'typeahead': 'latest',
         'jquery.tabbable': 'latest'},
)

js_user = NpmBundle(
    "js/circulation/user_init.js",
    output="gen/user%(version)s.js",
    filters=RequireJSFilter(exclude=[_js.contents[1]]),
    npm={'cal-heatmap': 'latest',
         'd3': 'latest',
         'bootstrap-datepicker': 'latest'},
)

js_lists = NpmBundle(
    "js/circulation/lists_init.js",
    output="gen/lists%(version)s.js",
    filters=RequireJSFilter(exclude=[_js.contents[1]]),
    npm={'cal-heatmap': 'latest',
         'd3': 'latest',
         'bootstrap-datepicker': 'latest'},
)

css = NpmBundle(
    "css/other/cal-heatmap.css",
    "css/circulation/user.css",
    # "vendors/jquery-ui/themes/redmond/jquery-ui.css",
    # "vendors/typeahead.js-bootstrap3.less/typeahead.css",
    output="gen/circulation.css",
)
