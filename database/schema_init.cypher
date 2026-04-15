// ============================================================================
// Schema Initialization for FineTuning Envelope Lineage System
// ============================================================================
// This file is idempotent: safe to run multiple times without errors.
// All constraints use CREATE ... IF NOT EXISTS syntax (Neo4j 4.4+).

// ─────────────────────────────────────────────────────────────────────────
// Recipe Uniqueness
// ─────────────────────────────────────────────────────────────────────────
// Enforce unique recipe names at the database level.
// Prevents duplicate recipes even if application-level checks fail.
CREATE CONSTRAINT unique_recipe_name
    IF NOT EXISTS
    FOR (r:Recipe)
    REQUIRE r.name IS UNIQUE;

// ─────────────────────────────────────────────────────────────────────────
// Notes:
// - Additional constraints (Model, Experiment, etc.) can be added here
//   as the schema evolves in future phases.
// - Always use "IF NOT EXISTS" for idempotency in production environments.
// ─────────────────────────────────────────────────────────────────────────
