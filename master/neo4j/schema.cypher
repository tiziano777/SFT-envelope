// Neo4j 5.x Schema Definition
// UNIQUE Constraints (5 total)

CREATE CONSTRAINT unique_recipe_id IF NOT EXISTS
FOR (r:Recipe) REQUIRE r.recipe_id IS UNIQUE;

CREATE CONSTRAINT unique_exp_id IF NOT EXISTS
FOR (e:Experiment) REQUIRE e.exp_id IS UNIQUE;

CREATE CONSTRAINT unique_ckp_id IF NOT EXISTS
FOR (c:Checkpoint) REQUIRE c.ckp_id IS UNIQUE;

CREATE CONSTRAINT unique_model_name IF NOT EXISTS
FOR (m:Model) REQUIRE m.model_name IS UNIQUE;

CREATE CONSTRAINT composite_component_key IF NOT EXISTS
FOR (co:Component) REQUIRE (co.technique_code, co.framework_code) IS UNIQUE;

// BTREE Indexes (3 on Experiment hashes)

CREATE INDEX idx_experiment_config_hash IF NOT EXISTS
FOR (e:Experiment) ON (e.config_hash);

CREATE INDEX idx_experiment_code_hash IF NOT EXISTS
FOR (e:Experiment) ON (e.code_hash);

CREATE INDEX idx_experiment_req_hash IF NOT EXISTS
FOR (e:Experiment) ON (e.req_hash);
