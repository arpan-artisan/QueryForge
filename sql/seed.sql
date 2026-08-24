INSERT INTO customers (id, name, email, created_at) VALUES
    (1, 'Aarav Mehta', 'aarav@example.com', '2026-01-04'),
    (2, 'Maya Rao', 'maya@example.com', '2026-01-08'),
    (3, 'Ishaan Kapoor', 'ishaan@example.com', '2026-02-14'),
    (4, 'Nisha Shah', 'nisha@example.com', '2026-03-02')
ON CONFLICT (id) DO NOTHING;

INSERT INTO products (id, name, category, unit_price) VALUES
    (1, 'Starter Keyboard', 'Accessories', 45.00),
    (2, 'Noise Canceling Headphones', 'Audio', 150.00),
    (3, 'USB-C Dock', 'Accessories', 95.00),
    (4, 'Portable Monitor', 'Displays', 220.00),
    (5, 'Webcam Pro', 'Video', 80.00)
ON CONFLICT (id) DO NOTHING;

INSERT INTO orders (id, customer_id, order_date, status) VALUES
    (1, 1, '2026-06-01', 'completed'),
    (2, 2, '2026-06-03', 'completed'),
    (3, 3, '2026-06-12', 'refunded'),
    (4, 1, '2026-07-07', 'completed'),
    (5, 4, '2026-07-20', 'pending'),
    (6, 2, '2026-08-03', 'completed'),
    (7, 3, '2026-08-10', 'completed')
ON CONFLICT (id) DO NOTHING;

INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES
    (1, 1, 1, 2, 45.00),
    (2, 1, 3, 1, 95.00),
    (3, 2, 2, 1, 150.00),
    (4, 2, 5, 2, 80.00),
    (5, 3, 4, 1, 220.00),
    (6, 4, 2, 2, 150.00),
    (7, 4, 3, 1, 95.00),
    (8, 5, 5, 1, 80.00),
    (9, 6, 4, 1, 220.00),
    (10, 6, 1, 1, 45.00),
    (11, 7, 3, 2, 95.00)
ON CONFLICT (id) DO NOTHING;

INSERT INTO refunds (id, order_id, refund_date, amount, reason) VALUES
    (1, 3, '2026-06-15', 220.00, 'Damaged item')
ON CONFLICT (id) DO NOTHING;
