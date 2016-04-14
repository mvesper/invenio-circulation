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
        'js/other/awesomplete'
    ],
function($) {
    $('.circ_id_complete').each(function(i, element) {
        var awesomplete = new Awesomplete(element, {list: []});
        var entity = $(element).data('entity');
        var last_input = null;

        function success(data) {
            data = JSON.parse(data);
            var res = [];
            $(data).each(function(i, val) {
                res.push({label: val.value, value: val.id});
            });
            awesomplete.list = res;
            awesomplete.evaluate();
        }

        $(element).on('input', function(event) {
            var search = {entity: entity, search: event.target.value};
            var ajax_query = {
                type: "POST",
                url: "/circulation/api/entity/search_autocomplete",
                data: JSON.stringify(JSON.stringify(search)),
                success: success,
                contentType: 'application/json',
            };

            function run() {
                var now = new Date();
                if (now - last_input > 800) {
                    $.ajax(ajax_query);
                }
            }

            last_input = new Date();
            setTimeout(run, 1000);
        });
    });
});
