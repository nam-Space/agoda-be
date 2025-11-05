-- Add sample discount data to hotels
-- Run this SQL in your MySQL database

-- Update some hotels with discounts
UPDATE hotels_hotel 
SET original_price = min_price * 1.25, 
    discount_percentage = 20 
WHERE avg_star >= 4.0 
LIMIT 5;

UPDATE hotels_hotel 
SET original_price = min_price * 1.15, 
    discount_percentage = 15 
WHERE avg_star >= 3.5 AND avg_star < 4.0 
LIMIT 3;

UPDATE hotels_hotel 
SET original_price = min_price * 1.10, 
    discount_percentage = 10 
WHERE avg_star >= 3.0 AND avg_star < 3.5 
LIMIT 3;

-- Check results
SELECT id, name, min_price, original_price, discount_percentage 
FROM hotels_hotel 
WHERE discount_percentage > 0
LIMIT 10;
