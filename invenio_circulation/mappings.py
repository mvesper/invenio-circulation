def add_copy_to(mappings):
    name = mappings['mappings'].keys()[0]
    full_text = {'type': 'string'}
    mappings['mappings'][name]['properties']['global_fulltext'] = full_text
    for key, value in mappings['mappings'][name]['properties'].items():
        try:
            value['copy_to'].append('global_fulltext')
        except AttributeError:
            value['copy_to'] = [value['copy_to'], 'global_fulltext']
        except KeyError:
            value['copy_to'] = ['global_fulltext']

item_mappings = {'mappings': {
                    'circulation_item': {
                        '_all': {'enabled': True},
                        'properties': {
                            'id': {
                                'type': 'integer',
                                'index': 'not_analyzed'},
                            'record_id': {
                                'type': 'string',
                                'index': 'not_analyzed'},
                            'location_id': {
                                'type': 'integer',
                                'index': 'not_analyzed'},
                            'isbn': {
                                'type': 'string',
                                'index': 'not_analyzed'},
                            'barcode': {
                                'type': 'string',
                                'index': 'not_analyzed'},
                            'current_status': {
                                'type': 'string',
                                'index': 'not_analyzed'},
                            'title': {
                                'type': 'string',},
                            'record': {
                                'properties': {
                                    'title': {
                                        'type': 'string',
                                        'copy_to': ['global_fulltext']}
                                    }
                                },
                            }
                        }
                    }
                 }
add_copy_to(item_mappings)

loan_cycle_mappings = {'mappings': {
                            'circulation_loan_cycle': {
                                '_all': {'enabled': True},
                                'properties': {
                                    'id': {
                                        'type': 'string',
                                        'index': 'not_analyzed'},
                                    'group_uuid': {
                                        'type': 'string',
                                        'index': 'not_analyzed'},
                                    'end_date': {
                                        'type': 'date',},
                                    'global_fulltext': {
                                        'type': 'string',},
                                    }
                                }
                            }
                       }
add_copy_to(loan_cycle_mappings)

user_mappings = {'mappings': {
                    'circulation_user': {
                        '_all': {'enabled': True},
                        'properties': {
                            'id': {
                                'type': 'integer',
                                'index': 'not_analyzed'},
                            'invenio_user_id': {
                                'type': 'integer',
                                'index': 'not_analyzed'},
                            'ccid': {
                                'type': 'string',
                                'index': 'not_analyzed'},
                            'name': {
                                'type': 'string'},
                            'email': {
                                'type': 'string'},
                            'address': {
                                'type': 'string'},
                            'phone': {
                                'type': 'string',
                                'index': 'not_analyzed'},
                            'mailbox': {
                                'type': 'string',},
                            'user_group': {
                                'type': 'string',},
                            }
                        }
                    }
                 }
add_copy_to(user_mappings)

location_mappings = {'mappings': {
                        'circulation_location': {
                            '_all': {'enabled': True},
                            'properties': {
                                'id': {
                                    'type': 'integer',
                                    'index': 'not_analyzed'},
                                'code': {
                                    'type': 'string',
                                    'index': 'not_analyzed'},
                                'name': {
                                    'type': 'string',},
                                'notes': {
                                    'type': 'string',},
                                }
                            }
                        }
                     }
add_copy_to(location_mappings)

event_mappings = {'mappings': {
                    'circulation_event': {
                        '_all': {'enabled': True},
                        'properties': {
                            'id': {
                                'type': 'integer',
                                'index': 'not_analyzed'},
                            'user_id': {
                                'type': 'integer',
                                'index': 'not_analyzed'},
                            'item_id': {
                                'type': 'integer',
                                'index': 'not_analyzed'},
                            'loan_cycle_id': {
                                'type': 'integer',
                                'index': 'not_analyzed'},
                            'location_id': {
                                'type': 'integer',
                                'index': 'not_analyzed'},
                            'loan_rule_id': {
                                'type': 'integer',
                                'index': 'not_analyzed'},
                            'mail_template_id': {
                                'type': 'integer',
                                'index': 'not_analyzed'},
                            'event': {
                                'type': 'string',},
                            'global_fulltext': {
                                'type': 'string',},
                            }
                        }
                    }
                  }
add_copy_to(event_mappings)

mail_template_mappings = {'mappings': {
                            'circulation_mail_template': {
                                '_all': {'enabled': True},
                                'properties': {
                                    'id': {
                                        'type': 'integer',
                                        'index': 'not_analyzed'},
                                    'template_name': {
                                        'type': 'string',},
                                    'subject': {
                                        'type': 'string',},
                                    'header': {
                                        'type': 'string',},
                                    'content': {
                                        'type': 'string',},
                                    }
                                }
                            }
                          }
add_copy_to(mail_template_mappings)

loan_rule_mappings = {'mappings': {
                        'circulation_loan_rule': {
                            '_all': {'enabled': True},
                            'properties': {
                                'id': {
                                    'type': 'integer',
                                    'index': 'not_analyzed'},
                                'name': {
                                    'type': 'string',
                                    'index': 'not_analyzed'},
                                'type': {
                                    'type': 'string',
                                    'index': 'not_analyzed'},
                                'loan_period': {
                                    'type': 'integer',
                                    'index': 'not_analyzed'},
                                'holdable': {
                                    'type': 'boolean',
                                    'index': 'not_analyzed'},
                                'home_pickup': {
                                    'type': 'boolean',
                                    'index': 'not_analyzed'},
                                'renewable': {
                                    'type': 'boolean',
                                    'index': 'not_analyzed'},
                                'automatic_recall': {
                                    'type': 'boolean',
                                    'index': 'not_analyzed'},
                                },
                            }
                        }
                      }
add_copy_to(loan_rule_mappings)

loan_rule_match_mappings = {
        'mappings': {
            'circulation_loan_rule_match': {
                '_all': {'enabled': True},
                'properties': {
                    'id': {
                        'type': 'integer',
                        'index': 'not_analyzed'},
                    'loan_rule_id': {
                        'type': 'integer',
                        'index': 'not_analyzed'},
                    'item_type': {
                        'type': 'string',
                        'index': 'not_analyzed'},
                    'patron_type': {
                        'type': 'string',
                        'index': 'not_analyzed'},
                    'location_code': {
                        'type': 'string',
                        'index': 'not_analyzed'},
                    },
                }
            }
        }

add_copy_to(loan_rule_match_mappings)

mappings = {'Item': item_mappings,
            'Loan Cycle': loan_cycle_mappings,
            'User': user_mappings,
            'Location': location_mappings,
            'Event': event_mappings,
            'Mail Template': mail_template_mappings,
            'Loan Rule': loan_rule_mappings,
            'Loan Rule Match': loan_rule_match_mappings}
