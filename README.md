# SalesManager — Sales & Customer Record Management System

SalesManager is a desktop-based business management application built to help small businesses organize customer records, manage products, create bills, and track sales through a simple web interface running locally on a computer.

## Features

- **Customer Management:** Add, view, edit, and manage customer records.
- **Product Management:** Maintain product details, prices, and stock information.
- **Sales & Billing:** Manage sales transactions and billing records.
- **Invoice History:** Review previously recorded sales and invoices.
- **Payment Management:** Organize payment records.
- **Reports:** Access business sales information.
- **MySQL Database:** Store business records in a structured relational database.
- **Dark Theme Interface:** Use a consistent, modern interface designed for everyday business operations.

## Technology Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript
- **Database:** MySQL
- **Development Tools:** Visual Studio Code, Git, GitHub

## Project Structure

```text
SalesManager/
├── static/          # CSS, JavaScript, and static assets
├── templates/       # HTML templates
├── app.py           # Flask application
├── db.py            # Database connection
├── .gitignore       # Excluded files and folders
└── README.md        # Project documentation
```

Additional Python scripts may be included for database setup and checking.

## Getting Started

### Prerequisites

- Python 3
- MySQL Server
- Git
- Visual Studio Code (recommended)

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yashagale08/SalesManager.git
   ```

2. Open the project folder:

   ```bash
   cd SalesManager
   ```

3. Create and activate a virtual environment:

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

4. Install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

5. Configure your local MySQL database and environment variables according to the project's database configuration.

6. Start the Flask application using the project's configured entry point.

   ```bash
   python app.py
   ```

7. Open the local address displayed in the terminal in your browser.

## Database Configuration

SalesManager uses MySQL to store business information. Configure the database name, username, password, host, and port for your local installation.

**Security:** Never publish database passwords, `.env` files, real customer records, or other confidential information.

## Project Status

This project is under development. Features and setup instructions may change as development continues.

## Author

**Yash Agale**

GitHub: https://github.com/yashagale08

## License

No license has been specified yet. Contact the author before reusing or distributing this project.
