/*
 * This file is part of invenio.
 * Copyright (C) 2016 CERN.
 *
 * invenio is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * invenio is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with invenio; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
 *
 * In applying this license, CERN does not
 * waive the privileges and immunities granted to it by virtue of its status
 * as an Intergovernmental Organization or submit itself to any jurisdiction.
 */


(function (angular) {
  // Setup
  angular
    .module('circulationSettings')
    .factory('circulationSettingsStore', circulationSettingsStore);

  function circulationSettingsStore() {
    var settings = {
      startDate: '',
      endDate: '',
      delivery: ['mail', 'pickup'],
      selectedDelivery: 'mail',
      waitlist: false,
    };

    var service = {
      settings: settings,
      getPayload: getPayload,
    };

    return service;

    function getPayload() {
      var data = {
        'start_date': settings.startDate,
        'end_date': settings.endDate,
        'delivery': settings.selectedDelivery,
        'waitlist': settings.waitlist,
      }

      angular.forEach(data, function(value, key) {
        if (value == '' || value == null) {
          delete data[key];
        }
      });

      return data;
    }
  }
})(angular);