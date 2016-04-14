# This file is part of Invenio.
# Copyright (C) 2009, 2010, 2011, 2014 CERN.
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

"""Invenio LDAP interface for BibCirculation at CERN. """

from time import sleep
from thread import get_ident

CFG_CERN_SITE = 1
try:
    import ldap
    import ldap.filter
    CFG_BIBCIRCULATION_HAS_LDAP = CFG_CERN_SITE
except (ImportError, IOError):
    CFG_BIBCIRCULATION_HAS_LDAP = False

CFG_CERN_LDAP_URI = "ldap://xldap.cern.ch:389"
CFG_CERN_LDAP_BASE = "dc=cern,dc=ch"

_ldap_connection_pool = {}


def _cern_ldap_login():
    return ldap.initialize(CFG_CERN_LDAP_URI)


def get_user_info(nickname="", email="", ccid=""):
    """Query the CERN LDAP server for information about a user.
    Return a dictionary of information"""
    try:
        connection = _ldap_connection_pool[get_ident()]
    except KeyError:
        connection = _ldap_connection_pool[get_ident()] = _cern_ldap_login()

    if not nickname and not email and not ccid:
        return {}
    if nickname:
        nickname = '(displayName={0})'.format(ldap.filter
                                              .escape_filter_chars(nickname))
    if email:
        email = '(mail={0})'.format(ldap.filter.escape_filter_chars(email))
    if ccid:
        ccid = '(employeeID={0})'.format(ldap.filter
                                         .escape_filter_chars(str(ccid)))

    query_filter = ('(& (| {0} {1} {2}) '
                    '(| (employeetype=primary) '
                    '(employeetype=external) '
                    '(employeetype=ExCern) ) )').format(nickname, email, ccid)

    try:
        results = connection.search_st(CFG_CERN_LDAP_BASE, ldap.SCOPE_SUBTREE,
                                       query_filter, timeout=5)
    except ldap.LDAPError:
        # Mmh.. connection error? Let's reconnect at least once just in case
        sleep(1)
        connection = _ldap_connection_pool[get_ident()] = _cern_ldap_login()
        results = connection.search_st(CFG_CERN_LDAP_BASE, ldap.SCOPE_SUBTREE,
                                       query_filter, timeout=5)

    if len(results) > 1:
        # Maybe one ExCern and primary at the same time.
        # In this case let's give precedence to ExCern
        types = {}
        for result in results:
            employee_type = result[1]['employeeType'][0]
            user_acc_ctrl = result[1]['userAccountControl'][0]
            if employee_type == 'Primary' and user_acc_ctrl == '512':
                return result[1]
            types[result[1]['employeeType'][0]] = result[1]
        if 'ExCern' in types and 'Primary' in types:
            return types['ExCern']
        if 'Primary' in types:
            return types['Primary']
        # Ok otherwise we just pick up something :-)
    if results:
        return results[0][1]
    else:
        return {}
