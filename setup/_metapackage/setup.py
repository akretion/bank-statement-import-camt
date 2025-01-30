import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo9-addons-akretion-bank-statement-import-camt",
    description="Meta package for akretion-bank-statement-import-camt Odoo addons",
    version=version,
    install_requires=[
        'odoo9-addon-bank_statement_import_camt',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 9.0',
    ]
)
