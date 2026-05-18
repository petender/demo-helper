IF OBJECT_ID('dbo.Sales', 'U') IS NOT NULL
    DROP TABLE dbo.Sales;

CREATE TABLE dbo.Sales (
    SaleID INT IDENTITY(1,1) PRIMARY KEY,
    SaleDate DATE NOT NULL,
    ProductName NVARCHAR(100) NOT NULL,
    Quantity INT NOT NULL,
    Price MONEY NOT NULL
);

-- Verify table creation
SELECT * FROM sys.objects WHERE object_id = OBJECT_ID('dbo.Sales') AND type = 'U';