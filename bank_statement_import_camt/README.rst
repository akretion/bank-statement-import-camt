The module *bank_statement_import_camt* is a module to import SEPA CAMT .052 and .053 bank statement files. It uses the bank statement import framework https://github.com/OCA/bank-statement-import This is a simple and easy-to-debug module with only 110 lines of code. It still lacks full support for initial and ending balances (should be easy to add).

This module *bank_statement_import_camt* is an alternative to
the OCA module *bank_statement_parse_camt* (227 lines of code)
and it's dependancies *bank_statement_parse* (475 lines) and
*bank_account_search* (90 lines), that currently support CAMT .053
but not .052. I decided to write this alternative module for 2 reasons:

* it was too difficult for me to add support for CAMT .052 in the current OCA module *bank_statement_parse_camt* ;

* I think that the module *bank_statement_parse* is a sort of "framework" above the framework provided by the module *account_bank_statement_import* and that it is an unnecessary layer that we should not use any more.
