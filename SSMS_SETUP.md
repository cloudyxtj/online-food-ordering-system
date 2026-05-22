# SQL Server / SSMS Setup (Localhost)

This Flask app uses SQLAlchemy. By default it falls back to SQLite, but it can connect to SQL Server on **localhost** with the database name **FoodOrderingDB**.

## 1. Create the database in SSMS

```sql
CREATE DATABASE FoodOrderingDB;
GO
```

## 2. Choose authentication (Windows or SQL Login)

### Option A — Windows Authentication
Use your Windows login in SSMS. No SQL login is required for basic local development.

### Option B — SQL Server Authentication (webapp_login)
Create a SQL login and a mapped database user:

```sql
USE master;
GO

CREATE LOGIN webapp_login WITH PASSWORD = 'Pa$$w0rd';
GO

USE FoodOrderingDB;
GO

CREATE USER webapp_user FOR LOGIN webapp_login;
GO

GRANT SELECT, INSERT, UPDATE ON dbo.[user] TO webapp_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON dbo.food_items TO webapp_user;
GRANT SELECT, INSERT, UPDATE ON dbo.orders TO webapp_user;
GRANT SELECT, INSERT, UPDATE ON dbo.order_items TO webapp_user;

GRANT SELECT, INSERT ON dbo.audit_logs TO webapp_user;
DENY UPDATE, DELETE ON dbo.audit_logs TO webapp_user;
GO
```

## 3. Install the SQL Server ODBC driver

Install **Microsoft ODBC Driver 18 for SQL Server** on Windows if it is not already installed.

To check installed drivers from PowerShell:

```powershell
Get-OdbcDriver | Where-Object Name -Like '*SQL Server*'
```

## 4. Configure the app (.env)

Create or edit `.env` with these values for this system:

**Windows Authentication**
```dotenv
DB_ENGINE=mssql
MSSQL_SERVER=localhost
MSSQL_DATABASE=FoodOrderingDB
MSSQL_DRIVER=ODBC Driver 18 for SQL Server
MSSQL_ENCRYPT=no
```

**SQL Server Authentication**
```dotenv
DB_ENGINE=mssql
MSSQL_SERVER=localhost
MSSQL_DATABASE=FoodOrderingDB
MSSQL_DRIVER=ODBC Driver 18 for SQL Server
MSSQL_ENCRYPT=no
MSSQL_USERNAME=webapp_login
MSSQL_PASSWORD=Pa$$w0rd
```

## 5. Install dependencies

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

If your active virtual environment is `.venv-1`, use:

```powershell
.\.venv-1\Scripts\python -m pip install -r requirements.txt
```

## 6. Create tables and sample data

```powershell
python seed.py
```

The seed script adds sample foods and this admin account:

```text
admin@foodorder.com / admin123
```

## 7. Run the app

```powershell
python run.py
```

Open the local Flask URL shown in the terminal, usually:

```text
http://127.0.0.1:5000
```

## 8. Verify in SSMS

```text
Databases > FoodOrderingDB > Tables
```

You should see:

```text
audit_logs
food_items
order_items
orders
user
```

Basic query check:

```sql
USE FoodOrderingDB;
GO

SELECT * FROM food_items;
SELECT * FROM [user];
GO
```
