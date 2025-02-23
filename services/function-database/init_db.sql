-- Create Database
CREATE DATABASE IF NOT EXISTS my_database;

-- Use the new database
USE my_database;

-- Create Tables
CREATE TABLE IF NOT EXISTS functions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name STRING UNIQUE NOT NULL,
    state STRING NOT NULL,
    code STRING NOT NULL,
    requirements STRING NOT NULL,
    deployment_yaml STRING DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    function_id UUID REFERENCES functions(id) ON DELETE CASCADE,
    log_message STRING NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Create Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_functions_state ON functions(state);
CREATE INDEX IF NOT EXISTS idx_logs_function_id ON logs(function_id);
