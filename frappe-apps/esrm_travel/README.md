# ESRM

Custom Frappe / ERPNext app for ESRM's ticketing and travel operations.

## Features

- `Ticket Booking` DocType for operational booking control
- `Ticket Sector` child table for route legs
- `ESRM Settings` singleton for company, item, cost center, and income defaults
- ticket approval workflow for agent-to-admin review
- automatic invoice and payment synchronization back to the booking
- custom links on `Sales Invoice` and `Payment Entry`
- travel reports for register, approvals, and sales/collection summary

## Business Flow

- `Customer` remains the ERP master record
- `Ticket Booking` stores operational ticket details
- agent submits bookings for admin approval
- only approved bookings can be invoiced
- `Sales Invoice` handles billing
- `Payment Entry` handles collections
- booking status stays synchronized with invoice and payment activity

## Install

From a bench root:

```bash
bench get-app /absolute/path/to/frappe-apps/esrm_travel
bench --site yoursite install-app esrm_travel
bench --site yoursite migrate
```

After install:

1. Open `ESRM Settings`
2. Set the default company
3. Set the service item used for ticket billing
4. Set default cost center and income account if needed
5. Assign users to `Ticketing Agent` or `System Manager`
6. Review workspace visibility, report access, and print formats before go-live
