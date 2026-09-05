INSERT INTO customers (id, name, email, created_at, region, segment) VALUES
    (1, 'Aarav Mehta', 'aarav@example.com', '2026-01-04', 'West', 'Consumer'),
    (2, 'Maya Rao', 'maya@example.com', '2026-01-08', 'South', 'Business'),
    (3, 'Ishaan Kapoor', 'ishaan@example.com', '2026-02-14', 'North', 'Consumer'),
    (4, 'Nisha Shah', 'nisha@example.com', '2026-03-02', 'East', 'Consumer'),
    (5, 'Kabir Iyer', 'kabir@example.com', '2026-04-11', 'South', 'Business'),
    (6, 'Leela Menon', 'leela@example.com', '2026-05-19', 'West', 'Business');

INSERT INTO categories (id, name, description) VALUES
    (1, 'Accessories', 'Computer and workstation accessories'),
    (2, 'Audio', 'Headphones, microphones, and audio devices'),
    (3, 'Displays', 'Monitors and display equipment'),
    (4, 'Video', 'Cameras and video devices');

INSERT INTO products (id, category_id, name, sku, unit_price, active) VALUES
    (1, 1, 'Starter Keyboard', 'ACC-KEY-001', 45.00, true),
    (2, 2, 'Noise Canceling Headphones', 'AUD-HP-002', 150.00, true),
    (3, 1, 'USB-C Dock', 'ACC-DOCK-003', 95.00, true),
    (4, 3, 'Portable Monitor', 'DSP-PORT-004', 220.00, true),
    (5, 4, 'Webcam Pro', 'VID-WEB-005', 80.00, true),
    (6, 1, 'Laptop Stand', 'ACC-STAND-006', 60.00, true),
    (7, 2, 'Studio Microphone', 'AUD-MIC-007', 130.00, true),
    (8, 3, '4K Monitor', 'DSP-4K-008', 360.00, true);

INSERT INTO orders (id, customer_id, order_date, status, channel) VALUES
    (1, 1, '2026-06-01', 'completed', 'web'),
    (2, 2, '2026-06-03', 'completed', 'retail'),
    (3, 3, '2026-06-12', 'refunded', 'web'),
    (4, 1, '2026-07-07', 'completed', 'web'),
    (5, 4, '2026-07-20', 'pending', 'partner'),
    (6, 2, '2026-08-03', 'completed', 'retail'),
    (7, 3, '2026-08-10', 'completed', 'web'),
    (8, 5, '2026-08-18', 'cancelled', 'partner'),
    (9, 6, '2026-08-22', 'completed', 'web'),
    (10, 5, '2026-08-28', 'completed', 'retail');

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
    (11, 7, 3, 2, 95.00),
    (12, 8, 8, 1, 360.00),
    (13, 9, 6, 3, 60.00),
    (14, 9, 7, 1, 130.00),
    (15, 10, 8, 1, 340.00),
    (16, 10, 1, 1, 45.00);

INSERT INTO payments (id, order_id, payment_date, amount, method, status) VALUES
    (1, 1, '2026-06-01', 185.00, 'card', 'succeeded'),
    (2, 2, '2026-06-03', 310.00, 'upi', 'succeeded'),
    (3, 3, '2026-06-12', 220.00, 'card', 'succeeded'),
    (4, 4, '2026-07-07', 395.00, 'card', 'succeeded'),
    (5, 5, '2026-07-20', 80.00, 'upi', 'pending'),
    (6, 6, '2026-08-03', 265.00, 'card', 'succeeded'),
    (7, 7, '2026-08-10', 190.00, 'wallet', 'succeeded'),
    (8, 8, '2026-08-18', 360.00, 'card', 'failed'),
    (9, 9, '2026-08-22', 310.00, 'upi', 'succeeded'),
    (10, 10, '2026-08-28', 385.00, 'card', 'succeeded');

INSERT INTO refunds (id, order_id, refund_date, amount, reason) VALUES
    (1, 3, '2026-06-15', 220.00, 'Damaged item'),
    (2, 10, '2026-08-30', 45.00, 'Partial accessory refund');
