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
    .controller('CirculationController', CirculationController)

  CirculationController.$inject = [
    '$scope',
    'ItemStore',
    'UserStore',
    'SettingsStore',
    'Config'];

  function CirculationController($scope, ItemStore, UserStore, SettingsStore, Config) {
    var vm = this;
    vm.items = ItemStore.items;
    vm.users = UserStore.users;
    vm.itemActions = ItemStore.itemActions;
    vm.removeItem = ItemStore.remove;
    vm.removeUser = UserStore.remove;
    vm.settings = SettingsStore.settings;
    vm.loanItems = loanItems;
    vm.requestItems = requestItems;
    vm.returnItems = returnItems;

    vm.actionStatus = {loan: 0, request: 0, ret: 0}

    $scope.$watch(function() {
      return vm.itemActions;
    }, function(newVal, oldVal) {
      vm.actionStatus.loan = ItemStore.getItemsActionState('loan');
      vm.actionStatus.request = ItemStore.getItemsActionState('request');
      vm.actionStatus.ret = ItemStore.getItemsActionState('ret');
    }, true);

    $scope.$watch(function() {
      return vm.settings;
    }, function(newVal, oldVal) {
      ItemStore.validateItems(Config.config.actions);
    }, true);

    $scope.$watch(function() {
      return vm.users;
    }, function(newVal, oldVal) {
      ItemStore.validateItems(Config.config.actions);
    }, true);

    function loanItems() {
      performActionOnItems(Config.config.actions.loan);
    }
    
    function requestItems() {
      performActionOnItems(Config.config.actions.request);
    }

    function returnItems() {
      performActionOnItems(Config.config.actions.return);
    }

    function performActionOnItems(action) {
      for (var i = 0; i < vm.items.length; i++) {
        ItemStore.performActionOnItem(i, action);
      }
      ItemStore.validateItems(Config.config.actions);
    }

  }
})(angular);
