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
    .directive('circulationAdminItem', circulationAdminItem)

  circulationAdminItem.$inject = ['$http', 'ItemStore', 'Config'];

  function circulationAdminItem($http, ItemStore, Config) {
    var directive = {
      link: link,
      scope: {
        index: '=',
      },
      template: '{{results.loan}} {{results.request}} {{results.return}}',
    };

    return directive;

    function link(scope, element, attributes) {
      scope.results = ItemStore.itemActions[scope.index];
      ItemStore.validateActionsOnItem(scope.index, Config.config.actions);
    }
  }
})(angular);
