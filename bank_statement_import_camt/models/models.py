# -*- coding: utf-8 -*-
# © 2015-2016 Akretion
# © 2016 AbAKUS it-solutions
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# @author Valentin Thirion <valentin.thirion@abakusitsolutions.eu>
# Ported to Odoo 11.0 by Alexis Yushin <alexis@ww.net>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api
from odoo.exceptions import Warning as UserError

import logging
from lxml import etree


_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    @api.model
    def _check_camt(self, data_file):
        try:
            root = etree.fromstring(
                data_file, parser=etree.XMLParser(recover=True))
            ns = root.tag
            if not ns.startswith('{urn:iso:std:iso:20022:tech:xsd:camt.'):
                return False
        except:
            return False
        return root

    @api.model
    def _parse_file(self, data_file):
        """
        Parse the CAMT XML file
        """
        camt = self._check_camt(data_file)
        if not camt:
            _logger.debug("Statement file was not a camt file.")
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)
        ns = camt.tag[1:camt.tag.index("}")]
        camt_type = ns[36:39]
        assert camt_type in ('052', '053'), 'wrong camt type'
        if camt_type == '052':
            body_tag = 'Rpt'
        else:
            body_tag = 'Stmt'

        # Account number
        iban_xpath = camt.xpath(
            '//ns:%s/ns:Acct/ns:Id/ns:IBAN' % body_tag, namespaces={'ns': ns})
        account_number = iban_xpath[0].text
        # Statement name
        statement_name_xpath = camt.xpath(
            '//ns:GrpHdr/ns:MsgId', namespaces={'ns': ns})
        statement_name = statement_name_xpath[0].text
        # Statement date
        statement_date_xpath = camt.xpath(
            '//ns:GrpHdr/ns:CreDtTm', namespaces={'ns': ns})
        statement_date = statement_date_xpath[0].text

        # Starting balance
        start_balance = 0
        camt_balances = camt.xpath(
            '//ns:%s/ns:Bal' % body_tag, namespaces={'ns': ns})
        for balance in camt_balances:
            balance_type = balance.xpath(
                'ns:Tp/ns:CdOrPrtry/ns:Cd', namespaces={'ns': ns})
            type_str = balance_type[0].text
            if type_str == 'OPBD':
                balance_amt = balance.xpath('ns:Amt', namespaces={'ns': ns})
                amount_str = balance_amt[0].text
                
                # Check if debit or credit
                balance_ind = balance.xpath('ns:CdtDbtInd', namespaces={'ns': ns})
                balance_ind_str = balance_ind[0].text
                if balance_ind[0].text == "CRDT":
                    start_balance = float(amount_str)
                if balance_ind[0].text == "DBIT":
                    start_balance = (float(amount_str)) * -1

        currency = False
        transactions = []
        camt_entries = camt.xpath(
            '//ns:%s/ns:Ntry' % body_tag, namespaces={'ns': ns})
        end_balance = start_balance
        for entry in camt_entries:
            entry_amt = entry.xpath('ns:Amt', namespaces={'ns': ns})
            amount_str = entry_amt[0].text
            amount = float(amount_str)
            entry_currency = entry.xpath('ns:Amt/@Ccy', namespaces={'ns': ns})
            line_currency = entry_currency[0].upper()
            if not currency:
                currency = line_currency
            elif currency != line_currency:
                raise UserError(_(
                    "The statement line with amount %s has a currency "
                    "%s which is different from the currency of the "
                    "other lines (%s).")
                    % (amount_str, line_currency, currency))
            entry_sign = entry.xpath('ns:CdtDbtInd', namespaces={'ns': ns})
            partner_tag = 'Dbtr'
            if entry_sign[0].text == 'DBIT':
                amount *= -1
                partner_tag = 'Cdtr'
            entry_date = entry.xpath('ns:BookgDt/ns:Dt', namespaces={'ns': ns})
            date = entry_date[0].text
            entry_partner_name = entry.xpath(
                'ns:NtryDtls//ns:RltdPties/ns:%s/ns:Nm' % partner_tag,
                namespaces={'ns': ns})
            partner_name = ""
            if len(entry_partner_name) > 0:
                partner_name = entry_partner_name[0].text
            entry_rmtinfo = entry.xpath(
                'ns:NtryDtls//ns:RmtInf/ns:Ustrd', namespaces={'ns': ns})
            label = ' '.join(line.text for line in entry_rmtinfo)
            transactions.append({
                'date': date,
                'ref': '',
                'name': u'%s | %s' % (partner_name, label),
                'amount': amount,
                'unique_import_id':
                u'%s-%s-%s-%s' % (date, amount, partner_name, label),
                })
            end_balance += amount

        vals_bank_statement = {
            'name': statement_name,
            'transactions': transactions,
            'balance_start': start_balance,
            'balance_end_real': end_balance,
            'date': statement_date,
            # TODO : add real support for balances read from camt file
            }
        return currency, account_number, [vals_bank_statement]
