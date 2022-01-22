# -*- coding: utf-8 -*-
{
    'name': "am_puchase_stock",
    'author': "Ahmed Salih",
    'category': 'Stock, purchase',
    'version': '0.1',
    'depends': ['base',
                'am_stock',
                'my_account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
}
