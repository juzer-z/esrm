import frappe


def execute():
    """Preserve legacy combined settlements while enabling component settlement links."""
    frappe.db.sql(
        """
        update `tabTicket Booking`
        set original_iata_settlement = iata_settlement,
            reissue_iata_settlement = iata_settlement,
            iata_settlement = null,
            iata_settlement_status = 'Settled'
        where reissue_status = 'Reissued'
          and ifnull(iata_settlement, '') != ''
          and ifnull(original_iata_settlement, '') = ''
          and ifnull(reissue_iata_settlement, '') = ''
        """
    )
