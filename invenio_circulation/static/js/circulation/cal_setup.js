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
    ],
function($, ch) {
    function setup(id) {
        var cal = new CalHeatMap();
        var data = JSON.parse($(id).attr('data-cal_data'));
        var range = parseInt($(id).attr('data-cal_range'));
        if (range == 0){
            return
        }
        var init = {itemSelector: id,
                    domain: "month",
                    subDomain: "x_day",
                    range: range,
                    cellSize: 30,
                    subDomainTextFormat: "%d",
                    legend: [1],
                    legendColors: ["green", "#EE0000"],
                    displayLegend: false,}
        cal.init(init);

        return cal;
    }

    return {setup: setup}
});
