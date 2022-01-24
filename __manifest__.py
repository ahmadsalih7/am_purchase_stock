# -*- coding: utf-8 -*-
{
    'name': "am_purchase_stock",
    'author': "Ahmed Salih",
    'category': 'Stock, purchase',
    'version': '0.1',
    'depends': ['base',
                'am_stock',
                'am_purchase',
                'my_account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': True,
}
