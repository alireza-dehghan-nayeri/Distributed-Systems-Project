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
    requirements TEXT DEFAULT NULL,
    deployment_yaml TEXT DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Create Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_functions_state ON functions(state);

-- Create a Changefeed for WebSocket notifications (CockroachDB Changefeed)
CREATE CHANGEFEED FOR functions
    INTO 'kafka://kafka-service:9092'
    WITH updated, resolved;