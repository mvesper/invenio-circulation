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
        'js/circulation/cal_setup',
        'node_modules/bootstrap-datepicker/js/bootstrap-datepicker',
    ],
function($, chs, _bdp) {
    var _data = {};

    $('.entity_action').on('click', function(event) {
        _data = $(this).data();
        if (_data.hasOwnProperty('modal_type') == true) {
            if (_data.modal_type == 'time_pick') {
                var _cal = JSON.parse($(this).attr('data-cal_data'));
                cal.update(_cal);
                $('#circulation_extension_time_pick').modal();
                return
            } else {
                $('#'+_data.modal_id).modal();
                return
            }
        }

        function success(data) {
            _data = {};
            $(document).scrollTop(0);
            window.location.reload();
        }

        $.ajax({
            type: "POST",
            url: "/circulation/api/circulation/run_action",
            data: JSON.stringify(JSON.stringify(_data)),
            success: success,
            contentType: 'application/json',
        });
    });

    $('.modal_submit').on('click', function(event) {
        $('#'+_data.modal_id).find('.modal_value').each(function(i, element) {
            _data[$(element).data('modal_attr')] = $(element).val();
        });

        function success(data) {
            _data = {};
            $(document).scrollTop(0);
            window.location.reload();
        }

        $.ajax({
            type: "POST",
            url: "/circulation/api/circulation/run_action",
            data: JSON.stringify(JSON.stringify(_data)),
            success: success,
            contentType: 'application/json',
        });
    });

    $('.modal_value').on('change', function(event){
        // TODO: This needs to be changed now :(
        if (Object.keys(_data).length == 0) { //Otherwise an error occurs on load
            return
        }

        if (!_data.hasOwnProperty('check_on_change')){
            return
        }

        var elem = getModalContentElem(event);
        _data[_data.modal_attr] = $(elem).find('#modal_value').val();
        var button = $(elem).find('.modal_submit');

        function success(data){
            var res = JSON.parse(data);
            if (res === true) {
                $(button).prop("disabled", false);
                $(button).removeClass('btn-danger');
                $(button).addClass('btn-success');
            } else {
                $(button).prop("disabled", true);
                $(button).removeClass('btn-success');
                $(button).addClass('btn-danger');
            }
        }

        $.ajax({
            type: "POST",
            url: "/circulation/api/circulation/try_action",
            data: JSON.stringify(JSON.stringify(_data)),
            success: success,
            contentType: 'application/json',
        });
    });

    var cal = null;

    $('#modal-cal-heatmap').ready(function(){
        var _id = '#modal-cal-heatmap';
        if ($(_id).length == 0) {
            return;
        }
        cal = chs.setup('#modal-cal-heatmap');
    });

    $('.circulation_date').datepicker({ format: 'yyyy-mm-dd'});
});
