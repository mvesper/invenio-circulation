# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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

"""Invenio circulation configuration file."""

CIRCULATION_RECORDS_UI_ENDPOINTS = dict(
    item=dict(
        pid_type='cir',
        route='/circulation/item/<pid_value>',
        view_imp='invenio_circulation.views.get_json',
        record_class='invenio_circulation.models:CirculationItem',
    ),
    location=dict(
        pid_type='cir',
        route='/circulation/loc/<pid_value>',
        view_imp='invenio_circulation.views.get_json',
        record_class='invenio_circulation.models:CirculationLocation',
    ),
    loan_cycle=dict(
        pid_type='cir',
        route='/circulation/loan_cycle/<pid_value>',
        view_imp='invenio_circulation.views.get_json',
        record_class='invenio_circulation.models:CirculationLoanCycle',
    ),
)

CIRCULATION_EMAILS = dict(
        item_loan='circulation/emails/item_loan/',
        loan_updated='circulation/emails/loan_updated/'
        )

CIRCULATION_EMAILS_SENDER = 'john.doe@mail.com'

CIRCULATION_LOAN_PERIOD = 28

CIRCULATION_REST_ENDPOINTS = dict(
    item=dict(
        record_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_response'),
        },
        item_route='/circulation/item/<pid_value>',
        resolver='invenio_circulation.resolvers:resolve_item',
        circulation_class='invenio_circulation.models:CirculationItem',
        default_media_type='application/json',
    ),
    loan_cycle=dict(
        record_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_response'),
        },
        item_route='/circulation/loan_cycle/<pid_value>',
        resolver='invenio_circulation.resolvers:resolve_loan_cycle',
        circulation_class='invenio_circulation.models:CirculationLoanCycle',
        default_media_type='application/json',
    ),
    location=dict(
        record_serializers={
            'application/json': ('invenio_records_rest.serializers'
                                 ':json_v1_response'),
        },
        item_route='/circulation/location/<pid_value>',
        resolver='invenio_circulation.resolvers:resolve_location',
        circulation_class='invenio_circulation.models:CirculationLocation',
        default_media_type='application/json',
    ),
)
