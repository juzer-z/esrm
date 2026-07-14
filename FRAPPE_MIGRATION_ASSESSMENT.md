# Frappe / ERPNext Migration Assessment

Date: 2026-04-20

## Goal

Migrate the current ESRM MIS into the Frappe ecosystem, using:

- ERPNext as the main company ERP
- a custom ticketing/travel operations module on top of Frappe / ERPNext
- standard ERP modules for accounting and other small-business operations

This plan is sized for a small company with about 5-10 users.

## Materials Downloaded Locally

Official upstream repositories were downloaded into this workspace:

- `frappe-materials/frappe`
- `frappe-materials/erpnext`

These are the core reference codebases for:

- Frappe Framework
- ERPNext

## Executive Recommendation

For your company size, the best fit is:

1. Use `ERPNext` for core business operations.
2. Use a `custom Frappe app` for the current booking/ticketing workflow.
3. Keep accounting inside standard ERPNext instead of building custom finance logic.
4. Prefer `Frappe Cloud` first unless you already have strong Linux/devops capacity.

Why:

- 5-10 users is small enough that ERPNext can cover a lot out of the box.
- your current MIS has a narrow operational workflow that maps well to custom DocTypes and print/report customizations
- accounting is already a strong standard module in ERPNext and should not be rebuilt
- managed hosting reduces maintenance burden, upgrades, backups, and admin overhead

## What Your Current MIS Does

From the current project review, the existing MIS mainly covers:

- user login and role-based access
- customer management
- booking/ticket record management
- invoice/payment status tracking
- password change/settings
- basic dashboard and reports
- downloadable report generation

The most real business logic today is around:

- Customers
- Bookings
- Invoice/payment tracking

The dashboard/reporting area is only partially implemented in the current app.

## Recommended ERPNext Scope

### Use Standard ERPNext Modules

These should be adopted with minimal customization:

- `Accounts`
- `CRM`
- `Selling`
- `Buying`
- `Projects` or `Support` if needed later
- `Users / Roles / Permissions`
- `Print Formats`
- `Reports / Dashboards / Workspaces`
- `File Attachments`

### Build as Custom App

The ticketing module should be a dedicated custom Frappe app, for example:

- `esrm_travel`

Inside that app, create custom DocTypes such as:

- `Ticket Booking`
- `Airline`
- `Route / Sector`
- `Ticketing Supplier` or map to Supplier if appropriate
- `Booking Payment Detail`
- `Ticket Issue / Reissue / Refund Log`

Depending on how operationally strict you want the system to be, `Ticket Booking` can either:

- stay as a custom operational DocType and link to ERPNext accounting documents
- or become part of a standard sales flow using Customer + Item/Service + Sales Invoice

## Best Functional Mapping

### Customer Management

Current MIS `Customer` should map directly to ERPNext `Customer`.

Likely extra custom fields:

- short name
- travel/customer code
- billing contact details
- passport-related defaults if needed
- corporate account flags

### Booking Management

Current MIS `Booking` should become a custom DocType such as `Ticket Booking`.

Suggested fields based on your current app:

- customer
- booking reference
- passenger name
- passport number
- purpose
- issue date
- PNR
- ticket number
- route
- flight date
- airline
- flight number
- gross amount
- IATA amount
- invoice amount
- invoice number
- payment status
- payment mode
- remarks
- uploaded ticket
- created by / assigned agent

### Accounting

Do not keep invoice logic only inside the booking record.

Instead:

- booking remains the operational source record
- accounting posts through ERPNext documents

Recommended accounting mapping:

- `Sales Invoice` for customer billing
- `Payment Entry` for receipts
- `Journal Entry` for manual adjustments
- `Purchase Invoice` if you want supplier-side ticket cost capture
- `Cost Center` for department or business-line reporting

This gives you:

- proper receivables
- ageing reports
- general ledger
- profit/loss and cash flow visibility
- audit trail

### Roles

Suggested roles:

- `System Manager`
- `Accounts User` / `Accounts Manager`
- `Ticketing Agent`
- `Ticketing Supervisor`
- `Sales User` if needed

### Reports

Your current MIS reports should be rebuilt using a mix of:

- standard report view
- Report Builder
- Query Reports
- Script Reports
- dashboard charts
- number cards

### Print / Invoice Output

Your invoice/ticket print flow should move to:

- custom `Print Formats`
- PDF output from Frappe
- optional branded invoice and itinerary formats

## What Can Be Customized in Frappe / ERPNext

Frappe is flexible enough to support your use case in multiple layers.

### No-Code / Low-Code Customizations

- Custom Fields
- Property Setters
- Customize Form
- Role permissions
- Workflows
- Web Forms
- Report Builder
- Print Format Builder
- Dashboard charts
- Number cards
- Workspace customization

Best for:

- small field additions
- minor process changes
- admin-maintained custom screens
- approval steps
- print layout changes

### Semi-Technical Customizations

- Client Scripts
- Server Scripts
- Query Reports
- custom notifications
- assignment rules
- auto-naming
- document validations

Best for:

- client-side form behavior
- server-side validations
- field auto-fill
- approval automation
- small business rules

### Full Custom App Development

- custom DocTypes
- Python controllers
- hooks
- fixtures
- custom pages
- custom reports
- custom print templates
- API integrations
- background jobs
- migration patches

Best for:

- the booking/ticketing module
- integration with airline/GDS/other systems later
- durable, version-controlled business logic
- multi-environment deployment

## What Should Be Standard vs Custom

### Keep Standard

- company setup
- chart of accounts
- customer master
- users and permissions
- sales invoices
- payment entries
- bank/cash accounting
- financial statements
- tax structure where applicable
- attachments and communications

### Customize Lightly

- customer extra fields
- invoice print format
- travel-related fields on Sales Invoice if needed
- dashboards and saved reports
- workflows for approval

### Build Custom

- booking lifecycle
- ticket issue / reissue / refund logic
- travel-specific operational forms
- ticketing performance dashboards
- any complex booking-to-finance automation

## Recommended Target Design

### Option A: Leanest and Best Starting Option

- ERPNext standard for master data + accounts
- one custom DocType `Ticket Booking`
- one action button or server method to generate `Sales Invoice`
- payments handled in `Payment Entry`

This is the best first phase.

### Option B: More Structured Travel ERP

- custom DocTypes for booking, segments, supplier cost, refunds, reissues
- workflow states for draft / ticketed / invoiced / partially paid / closed / refunded
- tighter linkage to Sales Invoice and Purchase Invoice

This is better after phase 1 is stable.

## Recommended Modules for Your Company

For a small team, I would start with:

- `Accounts`
- `CRM`
- `Selling`
- `Buying`
- `Support` or `Projects` only if you need them
- custom `Ticketing` app

I would avoid enabling too many modules initially, especially:

- Manufacturing
- Stock-heavy workflows
- HR/Payroll
- Assets

Only add those if you truly need them.

## Hosting Recommendation

For 5-10 users, first recommendation:

- `Frappe Cloud`

Why:

- faster launch
- simpler upgrades
- backups handled
- lower sysadmin burden
- easier for a small team

Choose self-hosting only if:

- you need strict infrastructure control
- you already have Linux/Frappe admin capability
- you want full custom deployment ownership from day one

## Migration Approach

### Phase 1: Foundation

- set up ERPNext site
- configure company
- set chart of accounts
- define users and roles
- define customer master structure
- decide booking-to-invoice flow

### Phase 2: Ticketing MVP

- create custom app
- create `Ticket Booking` DocType
- add required fields and permissions
- create workflow states
- build print formats
- link booking to Sales Invoice / Payment Entry

### Phase 3: Data Migration

Migrate at least:

- users
- customers
- open bookings
- invoice references
- payment status

Potentially also:

- historical bookings
- attachments
- legacy invoice PDFs

### Phase 4: Reporting

- booking register
- outstanding receivables
- agent-wise performance
- airline-wise sales
- monthly ticket revenue
- payment collection dashboard

### Phase 5: Operational Hardening

- approval workflows
- validations
- audit fields
- notification rules
- backup/recovery checklist
- user training

## Data Migration Notes

Your current source data model is simple enough that migration is realistic.

Main mappings:

- `User` -> ERPNext `User`
- `Customer` -> ERPNext `Customer`
- `Booking` -> custom `Ticket Booking`
- `invoice_amount`, `invoice_no`, `payment_status` -> linked sales/accounting flow

Important decision:

- whether historical invoices will be recreated as proper ERPNext accounting documents
- or imported only as legacy references while new transactions go live in ERPNext

For a small business, the practical approach is often:

- migrate master data and open balances properly
- import older operational history as reference data
- start full accounting transactions in ERPNext from a clean cutover date

## Risks / Decisions You Should Make Early

1. Whether booking records generate accounting documents automatically or manually.
2. Whether supplier-side ticket cost will be tracked in ERPNext from day one.
3. Whether historical accounting will be fully migrated or only opening balances imported.
4. Whether you want cloud-hosted or self-hosted.
5. Whether you want only one ticketing DocType first, or a richer travel module immediately.

## My Recommended Final Stack

For your case, I recommend:

- Platform: `ERPNext + Frappe`
- Hosting: `Frappe Cloud`
- Core modules enabled:
  - Accounts
  - CRM
  - Selling
  - Buying
- Custom app:
  - `esrm_travel`
- First custom DocType:
  - `Ticket Booking`

This gives you:

- strong accounting
- fast implementation
- low operational overhead
- room to grow into a proper travel ERP later

## Useful Official References

- ERPNext introduction: https://docs.frappe.io/erpnext
- ERPNext accounting overview: https://docs.frappe.io/erpnext/accounting/introduction
- Customize ERPNext: https://docs.frappe.io/erpnext/user/manual/en/customize-erpnext
- Customizing DocTypes: https://docs.frappe.io/framework/v15/user/en/basics/doctypes/customize
- Printing / Print Formats: https://docs.frappe.io/framework/user/en/desk/printing
- Report Builder: https://docs.frappe.io/framework/v15/user/en/desk/reports/report-builder
- REST API: https://docs.frappe.io/framework/v15/user/en/api/rest
- Create an App: https://docs.frappe.io/framework/v15/user/en/tutorial/create-an-app
- Create a DocType: https://docs.frappe.io/framework/v15/user/en/tutorial/create-a-doctype
- Hooks and Fixtures: https://docs.frappe.io/framework/v15/user/en/python-api/hooks
- Exporting Customizations: https://docs.frappe.io/framework/v15/user/en/guides/app-development/exporting-customizations
- Installation: https://docs.frappe.io/framework/user/en/installation
- ERPNext pricing / hosting overview: https://frappe.io/erpnext/pricing/

## Suggested Next Step

Create a formal solution blueprint with:

- exact DocTypes
- exact fields
- role matrix
- workflow states
- data migration mapping
- invoice/print design plan
- implementation phases

That should be the next document before actual build work starts.
