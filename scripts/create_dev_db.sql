-- Run as a Postgres superuser (e.g. `psql -U postgres -f scripts/create_dev_db.sql`)
-- to set up the local development and test databases referenced by
-- backend/.env.example.

CREATE USER medqueue WITH PASSWORD 'medqueue_dev_pw' CREATEDB;
CREATE DATABASE medqueue_ai OWNER medqueue;
CREATE DATABASE medqueue_ai_test OWNER medqueue;
