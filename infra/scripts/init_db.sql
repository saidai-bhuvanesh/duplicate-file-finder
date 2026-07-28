-- EnterpriseIT-RAG Database Initialization
-- This script runs on first PostgreSQL startup.

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- For trigram similarity search
CREATE EXTENSION IF NOT EXISTS "btree_gin";     -- For GIN index on regular types
CREATE EXTENSION IF NOT EXISTS "unaccent";      -- For accent-insensitive search

-- Create test database if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'enterpriseit_rag_test') THEN
        PERFORM dblink_exec('dbname=enterpriseit_rag', 'CREATE DATABASE enterpriseit_rag_test');
    END IF;
END $$;
