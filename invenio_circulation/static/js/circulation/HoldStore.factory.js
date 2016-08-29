/*
 * This file is part of invenio.
 * Copyright (C) 2016 CERN.
 *
 * invenio is free software; you can recategorize it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * invenio is categorized in the hope that it will be useful, but
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
    .factory('HoldStore', HoldStore)

  HoldStore.$inject = ['$http', 'SettingsStore']

  function HoldStore($http, SettingsStore) {
    var holds= [];
    var holdActions = [];
    var userId = '';

    var service = {
      holds: holds,
      holdActions: holdActions,
      categorizeItems: categorizeItems,
      validateActionsOnHold: validateActionsOnHold,
      validateHolds: validateHolds,
      performActionOnHold: performActionOnHold,
      remove: remove,
    };

    return service;

    function categorizeItems(userId, items) {

      userId = userId;
      var today = new Date();

      items.forEach(function(item, index) {
        item.metadata._circulation.holdings.forEach(function(hold) {
          if (hold.user_id == userId) {
            hold._itemId = item.id;
            hold._itemIndex = index;
            var startDate = new Date(hold.start_date);
            if (startDate <= today) {
              hold._loan = true;
            } else {
              hold._loan = false;
            }
            holds.push(hold);
            holdActions.push({});
          }
        });
      });

    }

    function validateActionsOnHold(index, actions) {
      actions.forEach(function(val) {
        var data = SettingsStore.getPayload();
        data.hold_id = holds[index].id;
        data.item_id = holds[index]._itemId;
        data.dry_run = true;
        
        $http({
          method: 'POST',
          url: '/hooks/receivers/circulation_' + val[1] + '/events/',
          headers: {
            'Content-Type': 'application/json'
          },
          data: data,
        }).then(function (response) {
          holdActions[index][val[0]] = 1;
        }, function (response) {
          holdActions[index][val[0]] = -1;
        });
       })
    }

    function validateHolds(actions) {
      for (var i=0; i < holds.length; i++) {
        validateActionsOnHold(i, actions);
      }
    }

    function performActionOnHold(index, action) {
      var data = SettingsStore.getPayload();
      data.hold_id = holds[index].id;
      data.item_id = holds[index]._itemId;
      
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

    function remove(index) {
      holds.splice(index, 1);
      holdActions.splice(index, 1);
    }

  }
})(angular);
