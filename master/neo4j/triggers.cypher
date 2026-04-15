// APOC Triggers for Neo4j 5.x
// Trigger 1: Automatic created_at timestamp on node creation

CALL apoc.trigger.install('neo4j', 'created_at_trigger',
  'UNWIND apoc.trigger.nodesByLabel($createdNodes, null) AS node
   SET node.created_at = datetime()',
  {phase: 'before'}) YIELD name
RETURN "Trigger created_at installed" AS message;

// Trigger 2: Automatic updated_at timestamp on property updates

CALL apoc.trigger.install('neo4j', 'updated_at_trigger',
  'UNWIND apoc.trigger.nodesByLabel($changedNodes, null) AS node
   SET node.updated_at = datetime()',
  {phase: 'before'}) YIELD name
RETURN "Trigger updated_at installed" AS message;

// Trigger 3: Orphan Checkpoint validation
// Prevents creating Checkpoint without parent derivation (except is_merging=true)

CALL apoc.trigger.install('neo4j', 'orphan_checkpoint_validation',
  'UNWIND apoc.trigger.nodesByLabel($createdNodes, "Checkpoint") AS ckp
   WHERE NOT (ckp)-[:PRODUCED_BY|DERIVED_FROM|RETRY_FROM|MERGED_FROM]->()
     AND NOT ckp.is_merging = true
   CALL apoc.util.validate(false, "Checkpoint %s is orphan and is_merging != true", [ckp.ckp_id])',
  {phase: 'after'}) YIELD name
RETURN "Trigger orphan_checkpoint_validation installed" AS message;
