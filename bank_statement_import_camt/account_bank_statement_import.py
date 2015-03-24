# -*- coding: utf-8 -*-
##############################################################################
#
#    CAMT .052+.053 import module for Odoo
#    Copyright (C) 2015 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
from lxml import etree
from openerp import models, _
from openerp.exceptions import Warning


_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    def _check_camt(self, cr, uid, data_file, context=None):
        try:
            root = etree.fromstring(
                data_file, parser=etree.XMLParser(recover=True))
            ns = root.tag
            if not ns.startswith('{urn:iso:std:iso:20022:tech:xsd:camt.'):
                return False
        except:
            return False
        return root

    def _parse_file(self, cr, uid, data_file, context=None):
        """
        Parse the CAMT XML file
        """
        camt = self._check_camt(
            cr, uid, data_file, context=context)
        if not camt:
            _logger.debug("Statement file was not a camt file.")
            return super(AccountBankStatementImport, self)._parse_file(
                cr, uid, data_file, context=context)
        ns = camt.tag[1:camt.tag.index("}")]
        camt_type = ns[36:39]
        assert camt_type in ('052', '053'), 'wrong camt type'
        if camt_type == '052':
            body_tag = 'Rpt'
        else:
            body_tag = 'Stmt'
        iban_xpath = camt.xpath(
            '//ns:%s/ns:Acct/ns:Id/ns:IBAN' % body_tag, namespaces={'ns': ns})
        account_number = iban_xpath[0].text
        statement_name_xpath = camt.xpath(
            '//ns:GrpHdr/ns:MsgId', namespaces={'ns': ns})
        statement_name = statement_name_xpath[0].text
        currency = False
        transactions = []
        camt_entries = camt.xpath(
            '//ns:%s/ns:Ntry' % body_tag, namespaces={'ns': ns})
        end_balance = 0.0
        for entry in camt_entries:
            entry_amt = entry.xpath('ns:Amt', namespaces={'ns': ns})
            amount_str = entry_amt[0].text
            amount = float(amount_str)
            end_balance += amount
            entry_currency = entry.xpath('ns:Amt/@Ccy', namespaces={'ns': ns})
            line_currency = entry_currency[0].upper()
            if not currency:
                currency = line_currency
            elif currency != line_currency:
                raise Warning(
                    _("The statement line with amount %s has a currency "
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

        vals_bank_statement = {
            'name': statement_name,
            'transactions': transactions,
            'balance_start': 0,
            'balance_end_real': end_balance,
            # TODO : add real support for balances read from camt file
            }
        return currency, account_number, [vals_bank_statement]
