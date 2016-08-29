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
  angular
    .module('circulation')
    .controller('UserHubController', UserHubController)

  UserHubController.$inject = [
    '$scope',
    'CirculationSearch',
    'HoldStore',
    'SettingsStore'
  ];

  function UserHubController($scope, CirculationSearch, HoldStore, SettingsStore) {
    var vm = this;
    var userId = document.getElementById('user-id').dataset.id;
    var relevantActions = [
      ['extend', 'extend'],
      ['lose', 'lose'],
      ['cancel', 'cancel']
    ];
    vm.holds = HoldStore.holds;
    vm.currentLoans = [];
    vm.currentRequests = [];
    vm.settings = SettingsStore.settings;
    vm.extendLoan = extendLoan;
    vm.loseHold = loseHold;
    vm.cancelRequest = cancelRequest;

    $scope.$watch(function() {
      return vm.settings;
    }, function(newVal, oldVal) {
      HoldStore.validateHolds(relevantActions);
    }, true);

    $scope.$watch(function() {
      return vm.holds;
    }, function(newVal, oldVal) {
      distributeHolds(vm.holds);
    }, true);

    angular.element(document).ready(function () {
      var search = '_circulation.holdings.user_id:' + userId;
      CirculationSearch.search(search, function(response) {
        HoldStore.categorizeItems(userId, response.data.hits.hits);
      });
    });

    function distributeHolds(holds) {
      vm.currentLoans = [];
      vm.currentRequests = [];

      holds.forEach(function(hold, index) {
        hold._originalIndex = index;
        if (hold._loan == true) {
          vm.currentLoans.push(hold);
        } else {
          vm.currentRequests.push(hold);
        }
      });
    }

    function extendLoan(index) {
      HoldStore.performActionOnHold(index, 'extend');
    }

    function loseHold(index) {
      HoldStore.performActionOnHold(index, 'lose');
      HoldStore.remove(index);
    }

    function cancelRequest(index) {
      HoldStore.performActionOnHold(index, 'cancel');
      HoldStore.remove(index);
    }

  }
})(angular);
