INSERT INTO dbo.Sales (SaleDate, ProductName, Quantity, Price) VALUES
('2024-01-01', 'Laptop', 5, 1200.00),
('2024-01-02', 'Smartphone', 10, 800.00),
('2024-01-03', 'Tablet', 7, 450.00);

-- Verify inserted rows
SELECT * FROM dbo.Sales;