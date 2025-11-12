CREATE DATABASE laundrydb;
USE laundrydb;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    phone VARCHAR(15),
    role VARCHAR(20) DEFAULT 'user'
);

CREATE TABLE machines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    location VARCHAR(100),
    status VARCHAR(20) DEFAULT 'available'
);

CREATE TABLE slots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    machine_id INT,
    slot_date DATE,
    slot_start TIME,
    slot_end TIME,
    FOREIGN KEY (machine_id) REFERENCES machines(id)
);

CREATE TABLE bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    slot_id INT,
    status VARCHAR(20) DEFAULT 'booked',
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (slot_id) REFERENCES slots(id)
);

CREATE TABLE feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    message TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
