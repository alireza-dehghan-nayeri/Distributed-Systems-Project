-- Create Database
CREATE DATABASE IF NOT EXISTS kubelesspy_database;

-- Use the new database
USE kubelesspy_database;

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


SET CLUSTER SETTING kv.rangefeed.enabled = true;

-- Create a Changefeed
CREATE CHANGEFEED FOR functions
    INTO 'kafka://kafka.default.svc.cluster.local:9092?topic_prefix=changefeed-'
    WITH updated;