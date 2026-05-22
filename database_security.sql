-- ============================================================
-- FoodOrderingDB - Database Security Setup Script
-- Run this entire file in SSMS against your FoodOrderingDB
-- Make sure you are connected as sa or a sysadmin account
-- ============================================================


-- ============================================================
-- SECTION 0: SCHEMA UPDATES
-- New columns required by the brute force protection feature.
-- Run this first before the rest of the script.
-- ============================================================

USE FoodOrderingDB;
GO

-- Add brute force tracking columns to the user table.
-- failed_login_attempts: counts consecutive wrong passwords.
-- locked_until: account is locked until this datetime (NULL = not locked).
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.[user]') AND name = 'failed_login_attempts'
)
    ALTER TABLE dbo.[user] ADD failed_login_attempts INT NOT NULL DEFAULT 0;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.[user]') AND name = 'locked_until'
)
    ALTER TABLE dbo.[user] ADD locked_until DATETIME NULL;
GO


-- ============================================================
-- SECTION 1: ROW-LEVEL SECURITY (RLS)
-- Customers can only see their own orders.
-- Admins can see all orders.
-- The app sets session context on every DB request.
-- ============================================================

USE FoodOrderingDB;
GO

-- Drop existing policy and function if they exist (safe to re-run)
IF EXISTS (SELECT 1 FROM sys.security_policies WHERE name = 'OrdersRLSPolicy')
    DROP SECURITY POLICY dbo.OrdersRLSPolicy;
GO
IF OBJECT_ID('dbo.fn_rls_orders_predicate', 'IF') IS NOT NULL
    DROP FUNCTION dbo.fn_rls_orders_predicate;
GO

-- Predicate function: returns 1 (allow) if the row's user_id matches
-- the session context user_id, OR if the session role is Admin.
CREATE FUNCTION dbo.fn_rls_orders_predicate(@user_id INT)
RETURNS TABLE
WITH SCHEMABINDING
AS
RETURN SELECT 1 AS result
WHERE
    @user_id = CAST(SESSION_CONTEXT(N'user_id') AS INT)
    OR 'Admin' = CAST(SESSION_CONTEXT(N'user_role') AS NVARCHAR(20));
GO

-- Apply as both a FILTER predicate (blocks SELECT) and
-- a BLOCK predicate (blocks INSERT/UPDATE with wrong user_id).
CREATE SECURITY POLICY OrdersRLSPolicy
ADD FILTER PREDICATE dbo.fn_rls_orders_predicate(user_id) ON dbo.orders,
ADD BLOCK  PREDICATE dbo.fn_rls_orders_predicate(user_id) ON dbo.orders
WITH (STATE = ON);
GO

-- HOW TO TEST RLS (run in a new SSMS query window):
--   EXEC sp_set_session_context N'user_id',   1;
--   EXEC sp_set_session_context N'user_role', N'Customer';
--   SELECT * FROM dbo.orders;    -- only rows where user_id = 1
--
--   EXEC sp_set_session_context N'user_role', N'Admin';
--   SELECT * FROM dbo.orders;    -- all rows


-- ============================================================
-- SECTION 2: DYNAMIC DATA MASKING (DDM)
-- Hides PII from standard DB users.
-- Users with UNMASK permission see the real data.
--
-- FIX: email has a unique constraint so we cannot use
-- ALTER COLUMN directly. We drop the constraint first,
-- add the mask, then recreate the constraint.
-- ============================================================

USE FoodOrderingDB;
GO

-- Step 1: Find and drop the unique constraint on email
DECLARE @constraintName NVARCHAR(256);
SELECT @constraintName = name
FROM sys.key_constraints
WHERE parent_object_id = OBJECT_ID('dbo.[user]')
  AND type = 'UQ'
  AND COL_NAME(parent_object_id, (
        SELECT column_id FROM sys.index_columns ic
        WHERE ic.object_id = parent_object_id AND ic.index_id = unique_index_id
  )) = 'email';

IF @constraintName IS NOT NULL
    EXEC('ALTER TABLE dbo.[user] DROP CONSTRAINT ' + @constraintName);
GO

-- Step 2: Apply the email mask (shows a***@***.com to standard users)
ALTER TABLE dbo.[user]
ALTER COLUMN email NVARCHAR(150) MASKED WITH (FUNCTION = 'email()');
GO

-- Step 3: Recreate the unique constraint
ALTER TABLE dbo.[user]
ADD CONSTRAINT UQ_user_email UNIQUE (email);
GO

-- Step 4: Mask the password_hash column (shows 'xxxx' to standard users)
ALTER TABLE dbo.[user]
ALTER COLUMN password_hash NVARCHAR(255) MASKED WITH (FUNCTION = 'default()');
GO

-- Step 5: Create a test user to demonstrate masking.
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'test_mask')
BEGIN
    CREATE USER test_mask WITHOUT LOGIN;
END
GRANT SELECT ON dbo.[user] TO test_mask;
GO

-- Step 6: Allow the app login to read real values (login requires this).
-- If your app DB user is different, replace 'webapp_user'.
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'webapp_user')
BEGIN
    GRANT UNMASK TO webapp_user;
END
GO

-- HOW TO TEST DDM:
--   EXECUTE AS USER = 'test_mask';
--   SELECT email, password_hash FROM dbo.[user];   -- masked values
--   REVERT;
--   SELECT email, password_hash FROM dbo.[user];   -- real values (as sysadmin)


-- ============================================================
-- SECTION 3: TRANSPARENT DATA ENCRYPTION (TDE)
-- Encrypts the entire database file on disk.
-- Protects against someone stealing the .mdf file directly.
-- ============================================================

-- Step 1: Create the master key in the master database
USE master;
GO
IF NOT EXISTS (SELECT * FROM sys.symmetric_keys WHERE name = '##MS_DatabaseMasterKey##')
    CREATE MASTER KEY ENCRYPTION BY PASSWORD = 'Str0ng!MasterKeyP@ss';
GO

-- Step 2: Create a certificate to protect the encryption key
IF NOT EXISTS (SELECT * FROM sys.certificates WHERE name = 'TDECert')
    CREATE CERTIFICATE TDECert WITH SUBJECT = 'FoodOrderingDB TDE Certificate';
GO

-- IMPORTANT: Back up the certificate after this script runs.
-- If the certificate is lost you cannot open the database.
-- Run this manually and store the files somewhere safe:
--
-- BACKUP CERTIFICATE TDECert
--     TO FILE = 'C:\Backup\TDECert.cer'
--     WITH PRIVATE KEY (
--         FILE           = 'C:\Backup\TDECert.pvk',
--         ENCRYPTION BY PASSWORD = 'BackupCertP@ss123'
--     );

-- Step 3: Create the database encryption key using AES-256 (skip if already exists)
USE FoodOrderingDB;
GO
IF NOT EXISTS (SELECT * FROM sys.dm_database_encryption_keys WHERE database_id = DB_ID())
BEGIN
    CREATE DATABASE ENCRYPTION KEY
        WITH ALGORITHM = AES_256
        ENCRYPTION BY SERVER CERTIFICATE TDECert;
    ALTER DATABASE FoodOrderingDB SET ENCRYPTION ON;
END
ELSE
    PRINT 'TDE already enabled — skipping.';
GO

-- Verify (encryption_state = 3 means fully encrypted)
SELECT
    d.name,
    d.is_encrypted,
    dk.encryption_state,
    dk.percent_complete
FROM sys.dm_database_encryption_keys dk
JOIN sys.databases d ON dk.database_id = d.database_id
WHERE d.name = 'FoodOrderingDB';
GO


-- ============================================================
-- SECTION 4: SQL SERVER AUDIT
-- Tracks failed logins (brute-force detection) and
-- SELECT on sensitive tables (insider snooping).
--
-- FIX: Create the audit log folder first, then create the audit.
-- Run this block in SSMS one step at a time if needed.
-- ============================================================

USE master;
GO

-- Step 1: Create the log folder using xp_cmdshell
--         (enable xp_cmdshell temporarily if needed)
EXEC sp_configure 'show advanced options', 1; RECONFIGURE;
EXEC sp_configure 'xp_cmdshell', 1;          RECONFIGURE;
EXEC xp_cmdshell 'mkdir C:\SQLAuditLogs 2>nul';
EXEC sp_configure 'xp_cmdshell', 0;          RECONFIGURE;
EXEC sp_configure 'show advanced options', 0; RECONFIGURE;
GO

-- Step 2: Create the server audit
IF NOT EXISTS (SELECT 1 FROM sys.server_audits WHERE name = 'FoodOrderingAudit')
BEGIN
    CREATE SERVER AUDIT FoodOrderingAudit
    TO FILE (
        FILEPATH = 'C:\SQLAuditLogs\',
        MAXSIZE   = 50 MB,
        MAX_FILES = 5,
        RESERVE_DISK_SPACE = OFF
    )
    WITH (
        QUEUE_DELAY = 1000,
        ON_FAILURE  = CONTINUE
    );
END
GO
ALTER SERVER AUDIT FoodOrderingAudit WITH (STATE = ON);
GO

-- Step 3: Audit failed logins at the server level
IF NOT EXISTS (
    SELECT 1 FROM sys.server_audit_specifications WHERE name = 'FailedLoginSpec'
)
BEGIN
    CREATE SERVER AUDIT SPECIFICATION FailedLoginSpec
    FOR SERVER AUDIT FoodOrderingAudit
    ADD (FAILED_LOGIN_GROUP)
    WITH (STATE = ON);
END
GO

-- Step 4: Audit SELECT on sensitive tables at the database level
USE FoodOrderingDB;
GO
IF NOT EXISTS (
    SELECT 1 FROM sys.database_audit_specifications WHERE name = 'SensitiveTableAuditSpec'
)
BEGIN
    CREATE DATABASE AUDIT SPECIFICATION SensitiveTableAuditSpec
    FOR SERVER AUDIT FoodOrderingAudit
    ADD (SELECT ON dbo.[user]     BY public),
    ADD (SELECT ON dbo.audit_logs BY public),
    ADD (SELECT ON dbo.orders     BY public)
    WITH (STATE = ON);
END
GO

-- HOW TO VIEW AUDIT LOGS:
--   SELECT *
--   FROM sys.fn_get_audit_file('C:\SQLAuditLogs\*', DEFAULT, DEFAULT)
--   ORDER BY event_time DESC;


-- ============================================================
-- SECTION 5: EXECUTE AS — HIJACKING DEMO + DEFENCE
-- Shows how an attacker could impersonate a higher-privilege
-- login, then demonstrates how to block it.
--
-- FIX: DENY IMPERSONATE is a server-scope permission,
--      so it must run in the master database.
-- ============================================================

USE FoodOrderingDB;
GO

-- Setup: create a low-privilege user to simulate an attacker
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'low_user')
    CREATE LOGIN low_user WITH PASSWORD = 'LowUser@123';
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'low_user')
    CREATE USER low_user FOR LOGIN low_user;
GO
GRANT SELECT ON dbo.orders TO low_user;
GO

-- DEMO — attacker hijacks sa context:
EXECUTE AS LOGIN = 'sa';
    SELECT SYSTEM_USER AS hijacked_identity;   -- shows 'sa'
    SELECT TOP 5 * FROM dbo.[user];            -- can access anything
REVERT;
SELECT SYSTEM_USER AS restored_identity;       -- back to original login
GO

-- DEFENCE: must run in master because it is a server-scope permission
USE master;
GO
DENY IMPERSONATE ON LOGIN::sa TO low_user;
GO

-- Verify the denial — this should now throw "Cannot execute as the server
-- principal because the principal 'sa' does not exist...":
-- EXECUTE AS LOGIN = 'sa';


-- ============================================================
-- SECTION 6: CODE SIGNING
-- Signs stored procedures with a certificate so any
-- unauthorised modification breaks the signature.
-- ============================================================

USE FoodOrderingDB;
GO

-- Step 1: Create a certificate for signing stored procedures
IF NOT EXISTS (SELECT 1 FROM sys.certificates WHERE name = 'SPSigningCert')
    CREATE CERTIFICATE SPSigningCert
        ENCRYPTION BY PASSWORD = 'Cert@SignP@ss123'
        WITH SUBJECT = 'Sign critical stored procedures';
GO

-- Step 2: Create the stored procedure to protect
IF OBJECT_ID('dbo.usp_GetAllOrders', 'P') IS NOT NULL
    DROP PROCEDURE dbo.usp_GetAllOrders;
GO
CREATE PROCEDURE dbo.usp_GetAllOrders
AS
    SELECT
        o.order_id,
        u.name        AS customer_name,
        o.total_price,
        o.order_status,
        o.created_at
    FROM dbo.orders o
    JOIN dbo.[user] u ON o.user_id = u.user_id;
GO

-- Step 3: Sign the procedure with the certificate
ADD SIGNATURE TO dbo.usp_GetAllOrders
    BY CERTIFICATE SPSigningCert
    WITH PASSWORD = 'Cert@SignP@ss123';
GO

-- Step 4: Verify the signature exists
SELECT
    OBJECT_NAME(major_id) AS procedure_name,
    crypt_type_desc       AS signature_type
FROM sys.crypt_properties
WHERE major_id = OBJECT_ID('dbo.usp_GetAllOrders');
GO

-- HOW TO TEST CODE SIGNING:
-- 1. Run the procedure normally (should work):
--    EXEC dbo.usp_GetAllOrders;
--
-- 2. Simulate a rogue modification:
--    ALTER PROCEDURE dbo.usp_GetAllOrders AS SELECT 'hacked';
--
-- 3. Check signature — will return no rows (signature is broken):
--    SELECT * FROM sys.crypt_properties
--    WHERE major_id = OBJECT_ID('dbo.usp_GetAllOrders');
--
-- 4. Re-sign to restore after a verified legitimate change:
--    ADD SIGNATURE TO dbo.usp_GetAllOrders
--        BY CERTIFICATE SPSigningCert
--        WITH PASSWORD = 'Cert@SignP@ss123';


-- ============================================================
-- SECTION 7: ALWAYS ENCRYPTED
-- Encrypts sensitive columns so that SQL Server never sees
-- plaintext — data is encrypted before leaving the client
-- and decrypted only on the client that holds the key.
--
-- IMPORTANT: Steps 1-3 below must be done via the SSMS wizard
-- because SSMS generates the encrypted key values using your
-- Windows Certificate Store. After the wizard, Steps 4-5
-- can be run as plain T-SQL.
--
-- SETUP STEPS IN SSMS WIZARD:
--   1. Right-click FoodOrderingDB > Tasks > Encrypt Columns
--   2. Click Next on the Introduction screen
--   3. Tick the columns you want to encrypt:
--        - dbo.[user].credit_card  → Deterministic encryption
--   4. For Column Master Key: choose "New column master key"
--        - Name: AlwaysEncryptedCMK
--        - Key store: Windows Certificate Store — Current User
--   5. For Column Encryption Key: choose "New column encryption key"
--        - Name: AlwaysEncryptedCEK
--   6. Click through and let SSMS generate and store the keys
--   7. SSMS will run the migration automatically
-- ============================================================

USE FoodOrderingDB;
GO

-- After running the SSMS wizard, verify the keys were created:
SELECT name, key_store_provider_name, key_path
FROM sys.column_master_keys
WHERE name = 'AlwaysEncryptedCMK';
GO

SELECT name FROM sys.column_encryption_keys
WHERE name = 'AlwaysEncryptedCEK';
GO

-- Verify which columns are now encrypted:
SELECT
    t.name                          AS table_name,
    c.name                          AS column_name,
    c.encryption_type_desc          AS encryption_type,
    cek.name                        AS encryption_key
FROM sys.columns c
JOIN sys.tables t ON c.object_id = t.object_id
JOIN sys.column_encryption_keys cek ON c.column_encryption_key_id = cek.column_encryption_key_id
WHERE t.name = 'user';
GO

-- HOW TO DEMONSTRATE ALWAYS ENCRYPTED:
-- 1. Open a new SSMS query window WITHOUT Always Encrypted enabled:
--    (Connection Properties > Additional Connection Parameters: leave blank)
--    SELECT email, password_hash FROM dbo.[user];
--    -- You will see encrypted binary gibberish — SQL Server cannot decrypt it
--
-- 2. Open another query window WITH Always Encrypted enabled:
--    (Connection Properties > Additional Connection Parameters:
--     type: ColumnEncryption=Enabled)
--    SELECT email, password_hash FROM dbo.[user];
--    -- You will see real plaintext values — client decrypts using certificate
