# 📝 Invoice Generator

This Python script allows you to create PDF invoices for your consulting services.

## 📚 Dependencies

- `yaml`
- `pdfkit`
- `jinja2`
- `argparse`
- `shutil`

## 📦 Installation

1. Clone the repository:

```bash
git clone https://github.com/narbonnais/invoice-generator.git
```

1. Install the dependencies:

```bash
pip install -r requirements.txt
```

3. Set up the config files in the `data/config` folder.

## 🚀 Usage

### Creating a new invoice

To create a new invoice, run the following command:

```bash
python3 invoices.py create_invoice <client_alias> "Service 1:rate:units" "Service 2:rate:units" -d <invoice_date>
```

For example:

```bash
python3 invoices.py create_invoice techcorp "Security audit:5000:1" "Reimbursements:300:1" -d 2021-01-01
```

The invoice will be generated in the `data/invoices` folder, and a new entry will be added to the history file in the `data/history` folder.

### Regenerating invoices

To regenerate all invoices based on the history file, run the following command:

```bash
python3 invoices.py regenerate
```

The existing invoices will be backed up in the `data/backup` folder and the new ones will be generated in the `data/invoices` folder.

### Resetting invoice number and deleting all invoices

To reset the invoice number and delete all invoices, run the following command:

```bash
python3 invoices.py reset
```

The existing invoices will be backed up in the `data/backup` folder.

## 📝 Sample invoice

The configuration files in the `data/config` and `data/history` folders are set up to generate invoices like the following one:

![Invoice sample](./invoice-sample.png)