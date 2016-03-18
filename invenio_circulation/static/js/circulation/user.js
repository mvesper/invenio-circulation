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
        'js/other/jsoneditor.min',
        'node_modules/bootstrap-datepicker/js/bootstrap-datepicker',
    ],
function($, chs, _, _bdp) {
    $('.user_action').on('click', function(event){
        var start_date = $('#circulation_date_from').val();
        start_date = start_date === undefined? null : start_date;
        var end_date = $('#circulation_date_to').val();
        end_date = end_date === undefined? null : end_date;

        var waitlist = $('#circulation_option_waitlist').is(':checked');
        waitlist = waitlist === undefined? null : waitlist;
        var delivery = $('#circulation_option_delivery').val();
        delivery = delivery === undefined? null : delivery;

        var data = $(this).data();
        data['start_date'] = start_date;
        data['end_date'] = end_date;
        data['waitlist'] = waitlist;
        data['delivery'] = delivery;

        $.ajax({
            type: "POST",
            url: "/circulation/api/user/run_action",
            data: JSON.stringify(JSON.stringify(data)),
            success: function(){window.location.reload();},
            contentType: 'application/json',
        });
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

    var cal = null;

    $('#cal-heatmap').ready(function(){
        if ($('#cal-heatmap').length == 0) {
            return;
        }
        cal = chs.setup('#cal-heatmap');
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
        var record_id = $(this).attr('data-record_id');
        var start_date = $('#circulation_date_from').val();
        var end_date = $('#circulation_date_to').val();
        var waitlist = $('#circulation_option_waitlist').is(':checked');
        var delivery = $('#circulation_option_delivery').val();

        var state = start_date+':'+end_date+':'+waitlist+':'+delivery;

        window.location.href = '/circulation/user/record/'+record_id+'/'+state
    });

    $('#circulation_option_waitlist').ready(function(){
        var obj = $('#circulation_option_waitlist');
        obj.attr('checked', (obj.attr('data-checked') === 'True'));
    });

    $('#circulation_option_delivery').ready(function(){
        var obj = $('#circulation_option_delivery');
        obj.val(obj.attr('data-val'));
    });

    $('#circulation_date_from').datepicker({ format: 'yyyy-mm-dd' });
    $('#circulation_date_to').datepicker({ format: 'yyyy-mm-dd' });
});
