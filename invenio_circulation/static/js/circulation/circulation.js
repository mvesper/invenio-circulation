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
    function get_circulation_state() {
        var url_parts = document.URL.split('/');

        var part = null;
        for (var i=0; i < url_parts.length; i++){
            part = url_parts[i];
            if (part == 'circulation') {
                try {
                    var state = decodeURIComponent(url_parts[i+2]);
                    var tmp = state.split(':');
                    var current_state = tmp.splice(0, 7);
                    return {items: current_state[0].split(','),
                            users: current_state[1].split(','),
                            records: current_state[2].split(',')}
                } catch(err) {
                    return {items: [], users: [], records: []}
                }
            }
        }
        return part;
    }

    function build_state_string(circulation_state, from, to, waitlist, delivery, search) {
        return circulation_state.items.join(',') + ':' +
               circulation_state.users.join(',') + ':' +
               circulation_state.records.join(',') + ':' +
               from + ':' +
               to + ':' +
               waitlist + ':' +
               delivery + ':' +
               search;
    }

    $('#circulation_search').on("keydown", function(event){
        if (event.keyCode == 13) {
            var search = $('#circulation_search').val();
            var from = $('#circulation_date_from').val();
            var to = $('#circulation_date_to').val();
            var waitlist = $('#circulation_option_waitlist').is(':checked');
            var delivery = $('#circulation_option_delivery').val();
            var circulation_state = get_circulation_state();

            var state_string = build_state_string(circulation_state, from, to, waitlist, delivery, search);

            window.location.href = '/circulation/circulation/' + encodeURIComponent(state_string);
        }
    });

    $('#circulation_search_result').on("click", ".entity_delete", function(event){
        var entity = $(event.target).data()['entity'];
        var id = $(event.target).data()['id'];
        var from = $('#circulation_date_from').val();
        var to = $('#circulation_date_to').val();
        var waitlist = $('#circulation_option_waitlist').is(':checked');
        var delivery = $('#circulation_option_delivery').val();

        var circulation_state = get_circulation_state();
        circulation_state[entity+'s'].splice(circulation_state[entity+'s'].indexOf(id), 1);

        var state_string = build_state_string(circulation_state, from, to, waitlist, delivery,  '');

        window.location.href = '/circulation/circulation/' + encodeURIComponent(state_string);
    });

    $('#circulation_actions').on("click", ".btn", function(event){
        var action = $(event.target).data()['action'];
        var users = $.map($('.circulation_user'), function(val, i){
            return $(val).data('id');
        });
        var items = $.map($('.circulation_item'), function(val, i){
            return $(val).data('id');
        });
        var from = $('#circulation_date_from').val();
        var to = $('#circulation_date_to').val();
        var waitlist = $('#circulation_option_waitlist').is(':checked');
        var delivery = $('#circulation_option_delivery').val();

        var data = {action: action, users: users, items: items,
                    start_date: from, end_date: to,
                    waitlist: waitlist, delivery: delivery};

        function success(data) {
            $(document).scrollTop(0);
            window.location.href = '/circulation/';
        }

        function error(data) {
            location.reload();
        }

        $.ajax({
            type: "POST",
            url: "/circulation/api/circulation/run_action",
            data: JSON.stringify(JSON.stringify(data)),
            success: success,
            error: error,
            contentType: 'application/json',
        });
    });

    var cal = null;

    $('#cal-heatmap').ready(function(){
        if ($('#cal-heatmap').length == 0) {
            return;
        }
        cal = chs.setup('#cal-heatmap');
        cal.update($('#cal-heatmap').data().cal_data);
    });

    $('#circulation_toggle_hints').on('click', function() {
        $('.circulation_alert').toggle();
        $(this).blur();
    });

    $('.record_item').mouseenter(function(){
        var data = JSON.parse($(this).attr('data-cal_data'));
        var range = parseInt($(this).attr('data-cal_range'));
        if (range == 0){
            return
        }
        cal.update(data);
    });

    $('.record_item').mouseleave(function(){
        var data = JSON.parse($('#cal-heatmap').attr('data-cal_data'));
        var range = parseInt($('#cal-heatmap').attr('data-cal_range'));
        if (range == 0){
            return
        }
        cal.update(data);
    });

    $('.item_select').on('click', function(event){
        var record_id = $(this).attr('data-record_id');
        var item_id = $(this).attr('data-item_id');
        var state = get_circulation_state();

        //Remove record
        var i = state.records.indexOf(record_id);
        if (i != -1) {
            state.records.splice(i, 1);
        }

        //Add item
        if (state.items.length == 1 && state.items.indexOf('') == 0) {
            state.items = [];
        }
        state.items.push(item_id);

        var from = $('#circulation_date_from').val();
        var to = $('#circulation_date_to').val();
        var waitlist = $('#circulation_option_waitlist').is(':checked');
        var delivery = $('#circulation_option_delivery').val();

        var state_string = build_state_string(state, from, to, waitlist, delivery, '');

        window.location.href = '/circulation/circulation/' + encodeURIComponent(state_string);
    });

    $('#circulation_option_waitlist').ready(function(){
        var obj = $('#circulation_option_waitlist');
        obj.attr('checked', (obj.attr('data-checked') === 'True'));
    });

    $('#circulation_option_delivery').ready(function(){
        var obj = $('#circulation_option_delivery');
        obj.val(obj.attr('data-val'));
    });

    $('#circulation_check_params').on('click', function(){
        var state = get_circulation_state();
        var from = $('#circulation_date_from').val();
        var to = $('#circulation_date_to').val();
        var waitlist = $('#circulation_option_waitlist').is(':checked');
        var delivery = $('#circulation_option_delivery').val();
        var state_string = build_state_string(state, from, to, waitlist, delivery, '');

        window.location.href = '/circulation/circulation/' + encodeURIComponent(state_string);
    });

    $('#circulation_date_from').datepicker({ format: 'yyyy-mm-dd' });
    $('#circulation_date_to').datepicker({ format: 'yyyy-mm-dd' });

    // Circulation actions scrolling
    var action_buttons_original_y = $('#circulation_action_container').offset().top;
    var action_buttons_topMargin = 20;
    $('#circulation_action_container').css('position', 'relative');

    $(window).on('scroll', function(event) {
        var scroll = $(window).scrollTop();

        if (scroll < action_buttons_original_y) {
            var move = 0;
        } else {
            var move = scroll - action_buttons_original_y + action_buttons_topMargin;
        }
         
        $('#circulation_action_container').stop(false, false).animate({top: move}, 100);
    });

    $(document).ready(function() {
        $('.circulation_alert').toggle();
    });
});
