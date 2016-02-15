/*
 * This file is part of Invenio.
 * Copyright (C) 2015 CERN.
 *
 * Invenio is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * Invenio is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Invenio; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
 */

define(
    [
        'jquery',
    ],
function($) {
    $('#to_details').on('click', function(event){
        var data = $(event.target).data();
        var link = data.link;
        delete data.link;

        for (var key in data) {
            data[key] = $(data[key]).val();
        }

        window.location.href = '/circulation/lists/' + link + '/detail/' + encodeURIComponent(JSON.stringify(data));
    });

    $('#circulation_date_from').datepicker({dateFormat: 'yy-mm-dd'});
    $('#circulation_date_to').datepicker({dateFormat: 'yy-mm-dd'});
}
);
