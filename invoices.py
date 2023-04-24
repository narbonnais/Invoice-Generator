import yaml
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import os
from datetime import datetime
import argparse
import json

import requests
import shutil
from jinja2 import Environment, FileSystemLoader
import pdfkit


DATA_PATH = "data"
CONFIG_DATA_PATH = f"{DATA_PATH}/config"
TEMPLATES_DATA_PATH = f"{DATA_PATH}/templates"

CONSULTANT_FILE = "consultant.yaml"
SERVICES_FILE = "services.yaml"
CLIENTS_FILE = "clients.yaml"

TEMPLATES_PATH = "templates"
INVOICE_TEMPLATE_FILE = "invoice_template.html"
OUTPUT_HTML_FILE = "invoice.html"

INVOICE_NUMBER_FILE = "invoice_number.txt"

OUTPUT_PDF_FOLDER = f"{DATA_PATH}/invoices"
OUTPUT_PDF_FILE = "invoice_{}.pdf"

HISTORY_DATA_PATH = f"{DATA_PATH}/history"
HISTORY_FILE = "history.json"

BACKUP_DATA_PATH = f"{DATA_PATH}/backup"
BACKUP_FILE_PREFIX = "backup_"

BASE_CURRENCY = "USD"
CONVERT_API = f"https://api.frankfurter.app"



@dataclass
class Service:
    """Service information"""
    name: str
    units: int
    rate: float

    @property
    def total(self) -> float:
        """Return the total price of the service"""
        return self.units * self.rate

    @classmethod
    def from_dict(cls, data: dict) -> "Service":
        """Return a Service object from a dictionary"""
        return cls(**data)

    def to_dict(self) -> dict:
        """Return a dictionary from the Service object"""
        return {
            "name": self.name,
            "units": self.units,
            "rate": self.rate
        }


@dataclass
class Consultant:
    """Consultant information"""
    name: str
    address: str
    city_postal_code: str
    country: str
    phone_number: int
    email: str
    siret_number: int
    ape_code: str
    vat_number: str
    bank_name: str
    bank_account_number: str
    bank_routing_number: str

    @classmethod
    def from_dict(cls, data: dict) -> "Consultant":
        """Return a Consultant object from a dictionary"""
        return cls(**data)


@dataclass
class Client:
    """Client information"""
    full_name: str
    short_name: str
    alias: str
    address: str
    city_state_zip_code: str
    country: str

    @classmethod
    def from_dict(cls, data: dict) -> "Client":
        """Return a Client object from a dictionary"""
        return cls(**data)


@dataclass
class HistoryEntry:
    """History entry"""
    client_alias: str
    invoice_date: str
    services: list[Service]

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        """Return a HistoryEntry object from a dictionary"""
        return cls(
            client_alias=data["client_alias"],
            invoice_date=data["invoice_date"],
            services=[Service.from_dict(service)
                      for service in data["services"]]
        )

    def to_dict(self) -> dict:
        """Return a dictionary from the HistoryEntry object"""
        return {
            "client_alias": self.client_alias,
            "invoice_date": self.invoice_date,
            "services": [service.to_dict() for service in self.services]
        }


@dataclass
class History:
    """History"""
    entries: list[HistoryEntry]

    @classmethod
    def from_dict(cls, data: dict) -> "History":
        """Return a History object from a dictionary"""
        return cls(entries=[HistoryEntry.from_dict(entry) for entry in data["entries"]])

    def to_dict(self) -> dict:
        """Return a dictionary from the History object"""
        return {"entries": [entry.to_dict() for entry in self.entries]}

    def add_entry(self, entry: HistoryEntry) -> None:
        """Add an entry to the history"""
        self.entries.append(entry)


@dataclass
class Invoice:
    """Invoice information"""
    number: int
    date: str
    services: list[Service] = field(default_factory=list)

    @property
    def total(self) -> float:
        """Return the total price of the services"""
        return sum([service.total for service in self.services])

    def add_service(self, service: Service) -> None:
        """Add a service to the invoice"""
        self.services.append(service)

class ClientNotFoundError(Exception):
    """Client not found error"""
    pass


def load_yaml_file(file_path: str) -> dict:
    """Load a yaml file and return the data"""
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


def get_consultant_information() -> Consultant:
    """Return the consultant information"""
    consultant_data = load_yaml_file(f"{CONFIG_DATA_PATH}/{CONSULTANT_FILE}")
    return Consultant.from_dict(consultant_data["consultant"])


def get_client_information(client_alias: str) -> Client:
    """Return the client information from the client alias"""
    clients_data = load_yaml_file(f"{CONFIG_DATA_PATH}/{CLIENTS_FILE}")
    for client in clients_data["clients"]:
        if client["alias"] == client_alias:
            return Client.from_dict(client)
    raise ClientNotFoundError(f"Client {client_alias} not found")


def render_invoice_template(consultant: Consultant, client: Client, invoice: Invoice) -> str:
    """Render the invoice template with the provided consultant and client information"""
    env = Environment(loader=FileSystemLoader(f"{TEMPLATES_DATA_PATH}"))
    template = env.get_template(INVOICE_TEMPLATE_FILE)
    return template.render(consultant=consultant, client=client, invoice=invoice)


def save_invoice_to_file(invoice_html: str, file_path: str) -> None:
    """Save the rendered invoice HTML to a file"""
    with open(file_path, "w") as file:
        file.write(invoice_html)


def get_current_invoice_number() -> int:
    """Read the current invoice_number.txt file"""
    with open(f"{CONFIG_DATA_PATH}/{INVOICE_NUMBER_FILE}", "r") as file:
        return int(file.read().strip())


def update_invoice_number() -> None:
    """Increment and update the invoice number in the invoice_number.txt file"""
    current_number = get_current_invoice_number()
    with open(f"{CONFIG_DATA_PATH}/{INVOICE_NUMBER_FILE}", "w") as file:
        file.write(str(current_number + 1))


def format_current_date() -> str:
    """Return the current date in YYYY-MM-DD format"""
    today = datetime.now()
    return today.strftime("%Y-%m-%d")


def generate_invoice_number(client_short_name: str, invoice_date: str) -> str:
    """Generate a unique invoice number based on the client alias, current date, and invoice number"""
    invoice_number = get_current_invoice_number()
    update_invoice_number()
    return f"{client_short_name}-{invoice_date}-{invoice_number}"


def reset_invoice_number() -> None:
    """Reset the invoice number to 1"""
    with open(f"{CONFIG_DATA_PATH}/{INVOICE_NUMBER_FILE}", "w") as file:
        file.write("1")


def save_invoice_to_pdf(invoice_html: str, file_path: str) -> None:
    """Save the rendered invoice HTML to a PDF file"""
    pdfkit.from_string(invoice_html, file_path)


def load_history() -> History:
    """Load the history file and return the data"""
    with open(f"{HISTORY_DATA_PATH}/{HISTORY_FILE}", "r") as file:
        return History.from_dict(json.load(file))


def append_history(client_alias: str, invoice: Invoice) -> None:
    """Append a new entry to the history file"""
    history = load_history()
    history.add_entry(HistoryEntry(
        client_alias=client_alias,
        invoice_date=invoice.date,
        services=invoice.services
    ))
    print(f"Saving history to {HISTORY_DATA_PATH}/{HISTORY_FILE}")
    print(f"Added entry: {history.entries[-1]}")
    with open(f"{HISTORY_DATA_PATH}/{HISTORY_FILE}", "w") as file:
        json.dump(history.to_dict(), file, indent=4)


def backup_invoices() -> None:
    """Backup the invoices folder"""
    # use timestamp as part of the zip file name
    output_zip = BACKUP_FILE_PREFIX + datetime.now().strftime("%Y%m%d_%H%M%S") + ".zip"

    # Compress the invoice folder if there are any invoices
    if os.listdir(OUTPUT_PDF_FOLDER):
        shutil.make_archive(os.path.join(BACKUP_DATA_PATH,
                            output_zip), 'zip', OUTPUT_PDF_FOLDER)

def clear_invoices() -> None:
    """Clear the invoices folder"""
    for file in os.listdir(OUTPUT_PDF_FOLDER):
        os.remove(os.path.join(OUTPUT_PDF_FOLDER, file))


def regenerate_invoices(history: History) -> None:
    """Regenerate invoices for all entries in the history file"""

    backup_invoices()
    clear_invoices()
    reset_invoice_number()

    # Recreate the invoices based on the history
    for entry in history.entries:
        consultant = get_consultant_information()
        client = get_client_information(entry.client_alias)

        invoice = Invoice(
            number=generate_invoice_number(
                client.short_name, entry.invoice_date),
            date=entry.invoice_date,
        )
        for service in entry.services:
            invoice.add_service(service)

        invoice_html = render_invoice_template(consultant, client, invoice)

        pdf_file_path = f"{OUTPUT_PDF_FOLDER}/{OUTPUT_PDF_FILE.format(invoice.number)}"
        save_invoice_to_pdf(invoice_html, pdf_file_path)


def convert_currency(amount: float, target_currency: str, conversion_date: str = None) -> float:
    """Convert the amount to the target currency using an API"""
    if target_currency == BASE_CURRENCY:
        return amount
    
    # Modify the API request URL to include the date
    historical_api = f"{CONVERT_API}/{conversion_date}?from={BASE_CURRENCY}&to={target_currency}"

    response = requests.get(historical_api)
    if response.status_code != 200:
        raise Exception("Failed to fetch currency conversion rates")

    rates = response.json()["rates"]
    if target_currency not in rates:
        raise Exception(f"Currency {target_currency} not supported")

    conversion_rate = rates[target_currency]
    return amount * conversion_rate



def create_invoice(client_alias: str, services: list[dict], invoice_date: str = None) -> None:
    """Create an invoice for a client"""
    consultant = get_consultant_information()
    client = get_client_information(client_alias)

    if not invoice_date:
        invoice_date = format_current_date()

    # Parse the services input
    invoice = Invoice(number=generate_invoice_number(client.short_name, invoice_date),
                      date=invoice_date)
    for service_input in services:
        name, rate, units = service_input.split(":")
        print(name, rate, units)
        service = Service(name=name, rate=float(rate), units=int(units))
        invoice.add_service(service)

    invoice_html = render_invoice_template(consultant, client, invoice)

    pdf_file_path = f"{OUTPUT_PDF_FOLDER}/{OUTPUT_PDF_FILE.format(invoice.number)}"
    save_invoice_to_pdf(invoice_html, pdf_file_path)

    # Append the invoice to the history file
    append_history(client_alias, invoice)


def compute_income(history: History, start_date: str = None, end_date: str = None, currency: str = None) -> None:
    """Compute the income for a given date range"""
    if not start_date:
        start_date = "1970-01-01"
    if not end_date:
        end_date = format_current_date()
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")

    total_income = 0
    for entry in history.entries:
        invoice_date = datetime.strptime(entry.invoice_date, "%Y-%m-%d")
        if start_date <= invoice_date <= end_date:
            for service in entry.services:
                if currency:
                    total_income += convert_currency(service.total, currency, entry.invoice_date)
                else:
                    total_income += service.total

    if currency:
        formatted_revenue = currency + " {:,.2f}".format(total_income)
    else:
        formatted_revenue = "${:,.2f}".format(total_income)
    print(f"Total income: {formatted_revenue}")


def summarize_history(history: History, currency: str = None) -> None:
    """Summarizes history per year and per quarter"""
    summary = defaultdict(lambda: defaultdict(float))

    for entry in history.entries:
        invoice_date = datetime.strptime(entry.invoice_date, "%Y-%m-%d")
        year = invoice_date.year
        quarter = (invoice_date.month - 1) // 3 + 1
        quarter_key = f"Q{quarter}"

        for service in entry.services:
            revenue = service.total
            if currency:
                revenue = convert_currency(revenue, currency, entry.invoice_date)
            summary[str(year)][quarter_key] += revenue
            summary[str(year)]["total"] += revenue

    print("Summary of the History:")
    print("-" * 30)
    for year, subtotals in sorted(summary.items()):
        print(f"{year}:")
        for quarter, revenue in sorted(subtotals.items()):
            if currency:
                formatted_revenue = currency + " {:,.2f}".format(revenue)
            else:
                formatted_revenue = "${:,.2f}".format(revenue)
            print(f"  {quarter}: {formatted_revenue}")
    print("-" * 30)


def ensure_data_paths_exists():
    """Ensure the data paths exists"""
    os.makedirs(DATA_PATH, exist_ok=True)
    os.makedirs(HISTORY_DATA_PATH, exist_ok=True)
    os.makedirs(OUTPUT_PDF_FOLDER, exist_ok=True)
    os.makedirs(BACKUP_DATA_PATH, exist_ok=True)



def main():
    """
    Entry point for the application

    Usage:
        python3 ./invoices.py create_invoice halborn "Security audit:5000:1" "Reimbursements:300:1" -d 2021-01-01
        python3 ./invoices.py regenerate
        python3 ./invoices.py reset
    """

    ensure_data_paths_exists()

    parser = argparse.ArgumentParser(
        description="Invoice Generator and Payment Tracker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Create invoice command
    create_invoice_parser = subparsers.add_parser(
        "create_invoice", help="Create a new invoice")
    create_invoice_parser.add_argument("client_alias", help="Client alias")
    create_invoice_parser.add_argument(
        "services", nargs="+", help="Services in the format 'service:rate:units'")
    create_invoice_parser.add_argument(
        "-d", "--date", help="Date of invoice in format YYYY-MM-DD")

    regenerate_parser = subparsers.add_parser(
        "regenerate", help="Regenerate the invoices")

    reset_parser = subparsers.add_parser(
        "reset", help="Reset the invoice number and delete all invoices")
    
    compute_income_parser = subparsers.add_parser(
        "compute_income", help="Compute the income for a given period")
    compute_income_parser.add_argument("-s", "--start_date", help="Start date of the period in format YYYY-MM-DD")
    compute_income_parser.add_argument("-e", "--end_date", help="End date of the period in format YYYY-MM-DD")
    compute_income_parser.add_argument("-c", "--currency", help="Currency to use for the computation")

    summarize_history_parser = subparsers.add_parser(
        "summarize_history", help="Summarize the history")
    summarize_history_parser.add_argument("-c", "--currency", help="Currency to use for the computation")

    args = parser.parse_args()

    if args.command == "create_invoice":
        create_invoice(args.client_alias, args.services, args.date)

    elif args.command == "regenerate":
        history = load_history()
        regenerate_invoices(history)

    elif args.command == "reset":
        backup_invoices()
        clear_invoices()
        reset_invoice_number()

    elif args.command == "compute_income":
        history = load_history()
        compute_income(history, args.start_date, args.end_date, args.currency)

    elif args.command == "summarize_history":
        history = load_history()
        summarize_history(history, args.currency)


if __name__ == "__main__":
    main()
    # history = load_history()
    # compute_income(history, "2022-01-01", None, "EUR")

