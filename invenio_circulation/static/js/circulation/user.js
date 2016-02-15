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
        'node_modules/cal-heatmap/cal-heatmap',
        'js/other/jsoneditor.min',
        'node_modules/bootstrap-datepicker/js/bootstrap-datepicker',
    ],
function($, ch, _, _bdp) {
    function get_data(args) {
        tmp =  {'user_id': null,
                'item_id': null,
                'clc_id': null,
                'action': null,
                'start_date': null,
                'end_date': null,
                'requested_end_date': null,
                'waitlist': null,
                'delivery': null}

        for (var key in args) {
            if (args.hasOwnProperty(key)) {
              tmp[key] = args[key];
            }
        }

        return tmp;
    }

    function perform_user_action(elem) {
        /*
        var user_id = elem.attr('data-user_id');
        user_id = user_id === undefined? null : user_id;
        var item_id = elem.attr('data-item_id');
        item_id = item_id === undefined? null : item_id;
        var clc_id = elem.attr('data-clc_id');
        clc_id = clc_id === undefined? null : clc_id;
        var action = elem.attr('data-action');
        action = action === undefined? null : action;

        var start_date = $('#circulation_date_from').val();
        start_date = start_date === undefined? null : start_date;
        var end_date = $('#circulation_date_to').val();
        end_date = end_date === undefined? null : end_date;

        var waitlist = $('#circulation_option_waitlist').is(':checked');
        waitlist = waitlist === undefined? null : waitlist;
        var delivery = $('#circulation_option_delivery').val();
        delivery = delivery === undefined? null : delivery;
        
        var search_body = get_data({'users': [user_id],
                                    'items': [item_id],
                                    'clcs': [clc_id],
                                    'action': action,
                                    'start_date': start_date,
                                    'end_date': end_date,
                                    'waitlist': waitlist,
                                    'delivery': delivery})

        */
        $.ajax({
            type: "POST",
            url: "/circulation/api/circulation/run_action",
            data: JSON.stringify(JSON.stringify($(elem).data())),
            success: function(){window.location.reload();},
            contentType: 'application/json',
        });

    }

    $('.user_action').on('click', function(event){
        perform_user_action($(this));
    });

    var _data = {};

    $('.current_hold_user_action').on('click', function(event){
        var action = $(this).attr('data-action');

        if (action == 'loan_extension' || action == 'request_ill_extension'){
            var _cal = JSON.parse($(this).attr('data-cal_data'));
            cal.update(_cal);
            _data = $(this).data();
            $('#circulation_extension_time_pick').modal();
            return
        }
        perform_user_action($(this));
    });

    $('#entity_detail').ready(function() {
        if ($('#entity_detail').length == 0) {
            return;
        }
        var editor = $('#entity_detail');
        var data = JSON.parse(editor.attr('data-editor_data'));
        var schema = JSON.parse(editor.attr('data-editor_schema'));

        json_editor = new JSONEditor($('#entity_detail')[0], 
                {
                    schema: schema,
                    theme: 'bootstrap3',
                    no_additional_properties: true,
                });
        json_editor.setValue(data);
    });

    $(document).ready(function(){
        /*
        if($('#circulation_alert').length){
            function hide_circulation_alert(){
                $('#circulation_alert').fadeOut(1000);
            }
            setTimeout(hide_circulation_alert, 5000);
        }
        */
        //$('.circulation_alert').toggle();
    });

    cal = null;

    $('#cal-heatmap').ready(function(){
        if ($('#cal-heatmap').length == 0) {
            return;
        }
        cal = new CalHeatMap();
        var data = JSON.parse($('#cal-heatmap').attr('data-cal_data'));
        var range = parseInt($('#cal-heatmap').attr('data-cal_range'));
        if (range == 0){
            return
        }
        var init = {itemSelector: "#cal-heatmap",
                    domain: "month",
                    subDomain: "x_day",
                    range: range,
                    cellSize: 30,
                    subDomainTextFormat: "%d",
                    legend: [1],
                    legendColors: ["green", "#EE0000"],
                    displayLegend: false,}
        cal.init(init);
    });

    $('.record_item').mouseenter(function(){
        var data = JSON.parse($(this).attr('data-cal_data'));
        var range = parseInt($(this).attr('data-cal_range'));
        if (range != 0){
            cal.update(data);
        }

        var warnings = JSON.parse($(this).attr('data-warnings'));
        if (warnings.length == 0) {
            return
        }
        var content = [];
        for (var i = 0; i < warnings.length; i++) {
            var category = warnings[i][0];
            var message = warnings[i][1];
            content.push(category + ': ' + message);
        }
        content = content.join('<br>');
        $(this).popover({
            content:content,
            container:'body',
            placement:'top',
            html:true}).popover('show');
    });

    $('.record_item').mouseleave(function(){
        cal.update({});
        $(this).popover('hide');
    });

    $('#user_check_params').on('click', function(){
        var user_id = $(this).attr('data-user_id');
        var record_id = $(this).attr('data-record_id');
        var start_date = $('#circulation_date_from').val();
        var end_date = $('#circulation_date_to').val();
        var waitlist = $('#circulation_option_waitlist').is(':checked');
        var delivery = $('#circulation_option_delivery').val();

        var state = start_date+':'+end_date+':'+waitlist+':'+delivery;

        window.location.href = '/circulation/user/'+user_id+'/record/'+record_id+'/'+state
    });

    $('#circulation_option_waitlist').ready(function(){
        var obj = $('#circulation_option_waitlist');
        obj.attr('checked', (obj.attr('data-checked') === 'True'));
    });

    $('#circulation_option_delivery').ready(function(){
        var obj = $('#circulation_option_delivery');
        obj.val(obj.attr('data-val'));
    });

    $('#circulation_extension_date').on('change', function(event){
        if (Object.keys(_data).length == 0) { //Otherwise an error occurs on load
            return
        }

        var data = _data;
        data['requested_end_date'] = $('#circulation_extension_date').val();

        function success(data){
            var res = JSON.parse(data);
            if (res === true) {
                $('#circulation_extension_button').prop("disabled", false);
                $('#circulation_extension_button').removeClass('btn-danger');
                $('#circulation_extension_button').addClass('btn-success');
            } else {
                $('#circulation_extension_button').prop("disabled", true);
                $('#circulation_extension_button').removeClass('btn-success');
                $('#circulation_extension_button').addClass('btn-danger');
            }
        }

        $.ajax({
            type: "POST",
            url: "/circulation/api/circulation/try_action",
            data: JSON.stringify(JSON.stringify(data)),
            success: success,
            contentType: 'application/json',
        });
    });

    $('#circulation_extension_button').on('click', function(event){
        var data = _data;
        data['requested_end_date'] = $('#circulation_extension_date').val();

        $.ajax({
            type: "POST",
            url: "/circulation/api/circulation/run_action",
            data: JSON.stringify(JSON.stringify(data)),
            success: function(){window.location.reload();},
            contentType: 'application/json',
        });
    });

    $('#circulation_date_from').datepicker({ format: 'yyyy-mm-dd' });
    $('#circulation_date_to').datepicker({ format: 'yyyy-mm-dd' });
    $('#circulation_extension_date').datepicker({ format: 'yyyy-mm-dd'});
}
);
