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
    .factory('ItemStore', ItemStore)

  ItemStore.$inject = ['$http', 'SettingsStore']

  function ItemStore($http, SettingsStore) {
    items = [];
    itemActions = [];

    var service = {
      items: items,
      itemActions: itemActions,
      validateActionsOnItem: validateActionsOnItem,
      validateItems: validateItems,
      performActionOnItem: performActionOnItem,
      extend: extend,
      remove: remove,
      getItemsActionState: getItemsActionState,
    };

    return service;

    function validateActionsOnItem(index, actions) {
      actions.forEach(function(val) {

        var data = SettingsStore.getPayload();
        data.item_id = items[index].id;
        data.dry_run = true;
        
        $http({
          method: 'POST',
          url: '/hooks/receivers/circulation_' + val[1] + '/events/',
          headers: {
            'Content-Type': 'application/json'
          },
          data: data,
        }).then(function (response) {
          itemActions[index][val[0]] = 1;
        }, function (response) {
          itemActions[index][val[0]] = -1;
        });
       })
    }

    function validateItems(actions) {
      for (var i=0; i < items.length; i++) {
        validateActionsOnItem(i, actions);
      }
    }

    function performActionOnItem(index, action) {
      var data = SettingsStore.getPayload();
      data.item_id = items[index].id;
      
      $http({
        method: 'POST',
        url: '/hooks/receivers/circulation_' + action + '/events/',
        headers: {
          'Content-Type': 'application/json'
        },
        data: data,
      }).then(function (response) {
        console.log('Success');
      }, function (response) {
        console.log('Failure');
      });

    }

    function getItemsActionState(action) {
      if (itemActions.length == 0) {
        return 0;
      }

      var actionState = 1;

      itemActions.forEach(function(val) {
        if (val[action] == -1) {
          actionState = -1;
        }
      });

      return actionState
    }

    function extend(values) {
      values.forEach(function(val) {
        items.push(val);
        itemActions.push({});
      });
    }

    function remove(index) {
      items.splice(index, 1);
      itemActions.splice(index, 1);
    }

  }
})(angular);
