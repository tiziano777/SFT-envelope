# Lineage System Troubleshooting

## Issue 1: Handshake Timeout (Daemon Doesn't Start)

**Symptom:** run.sh logs `⚠ Handshake timeout. Running in degraded mode`

**Causes:**
- Master API unreachable
- Daemon crashed
- Network blocked
- Wrong Master URL or API key

**Debug Steps:**

```bash
# Check 1: Master API running?
curl -i http://localhost:8000/health

# Check 2: Daemon logs?
tail -50 setups/setup_myexp/.daemon.log 2>&1

# Check 3: Network connectivity?
ping $MASTER_API_URL

# Check 4: X-API-Key configured?
echo $X_API_KEY

# Check 5: Daemon process exists?
ps aux | grep "python -m worker.daemon"
```

**Solution:**
- Ensure `make master-up` completed successfully
- Verify X-API-KEY is set and correct
- Check network reachability to Master
- Restart daemon: `kill $(cat .daemon.pid)` then re-run setup

---

## Issue 2: Checkpoint Push Returns 404 (Experiment Not Found)

**Symptom:** transfer_log.jsonl shows `checkpoint_push returned 404`

**Causes:**
- Handshake never completed (degraded mode)
- exp_id mismatch
- Neo4j down
- Experiment deleted

**Debug Steps:**

```bash
# Check 1: .exp_id file created?
cat setups/setup_myexp/.exp_id

# Check 2: Handshake succeeded?
ls -la setups/setup_myexp/.handshake_done

# Check 3: Neo4j has experiment?
cypher "MATCH (e:Experiment {exp_id: 'e-20260410-001'}) RETURN e"

# Check 4: Transfer log shows which exp_id?
tail setups/setup_myexp/transfer_log.jsonl | jq '.exp_id'

# Check 5: Check daemon logs for handshake error
tail -20 setups/setup_myexp/.daemon.log | grep -i handshake
```

**Solution:**
- Delete .handshake_done and .exp_id, restart setup
- Verify Master API is running
- Check Neo4j connection: `docker exec neo4j cypher-shell "MATCH (e:Experiment) RETURN COUNT(e)"`

---

## Issue 3: Circular Dependency Detected (409 Conflict)

**Symptom:** API returns `409: Circular dependency in lineage graph`

**Causes:**
- DERIVED_FROM relation creates cycle (exp1 → exp2 → exp1)
- Merge with self
- Bug in strategy detection

**Debug Steps:**

```bash
# Find cycles
cypher "MATCH path = (e:Experiment)-[:DERIVED_FROM|RETRY_FROM*]->(e) RETURN path"

# List all experiments with their relations
cypher "MATCH (e1:Experiment)-[r:DERIVED_FROM|RETRY_FROM]->(e2:Experiment) RETURN e1.exp_id, type(r), e2.exp_id"

# Check depth of experiment chain
cypher "MATCH (e:Experiment {exp_id: 'e-001'})-[:DERIVED_FROM*]->(e2) RETURN LENGTH(p) AS depth"
```

**Solution:**
- Contact admin to break cycle in Neo4j (delete problematic relation)
- Regenerate from RESUME strategy (not BRANCH)

---

## Issue 4: Config Change Not Triggering BRANCH (Strategy=RESUME when should be BRANCH)

**Symptom:** Handshake returns RESUME but config was changed

**Causes:**
- Trigger hash not updated
- requirements.txt changed (excluded from hash intentionally)
- Hash algorithm mismatch

**Debug Steps:**

```bash
# Recompute hashes
python -c "
from envelope.shared import ConfigHasher
import yaml

with open('my_config.yaml') as f:
    cfg = yaml.safe_load(f)
config_hash = ConfigHasher.hash_config(cfg)
print(f'config_hash: {config_hash}')
"

# Check if train.py or rewards/* changed
git diff HEAD setups/setup_myexp/train.py setups/setup_myexp/rewards/

# Check requirements.txt (should NOT be included in hash)
diff setups/setup_myexp/requirements.txt setups/setup_oldexp/requirements.txt
```

**Solution:**
- Verify config.yaml was saved before running setup
- requirements.txt is intentionally excluded (implementation detail)
- Force BRANCH by changing a hashed field in config

---

## Issue 5: Neo4j Connection Refused (Master API Unavailable)

**Symptom:** Master API crashes on startup; logs show `Connection refused` for `bolt://localhost:7687`

**Causes:**
- Neo4j container not running
- Port 7687 blocked
- NEO4J_URI misconfigured

**Debug Steps:**

```bash
# Check Neo4j container
docker ps | grep neo4j

# Check port listening
lsof -i :7687

# Check Docker logs
docker logs fintuning-envelope-neo4j-1

# Check environment
echo $NEO4J_URI
```

**Solution:**
- Run `make master-up` to start Neo4j
- If port conflict: `docker-compose down && docker-compose up`
- Check Docker daemon: `docker ps` should show running containers

---

## Issue 6: Worker Daemon High CPU / Memory Leak

**Symptom:** daemon.py consuming 20%+ CPU or > 1GB RAM after training

**Causes:**
- Watchdog not cleaning up
- transfer_log.jsonl too large
- Queue backlog

**Debug Steps:**

```bash
# Check process
ps aux | grep daemon.py

# Check transfer log size
du -h setups/setup_myexp/transfer_log.jsonl

# Check queue backlog (how many events pending?)
wc -l setups/setup_myexp/transfer_log.jsonl

# Check memory
top -p $(pgrep -f daemon.py)
```

**Solution:**
- Let daemon flush (wait 5 min after training_done)
- If stuck: `kill $(pgrep -f daemon.py)`
- Manually flush: `python -c "from worker.pusher import AsyncPusher; ..."`

---

## Issue 7: Checkpoint URI Not Resolved (404 when reading artifact)

**Symptom:** Master cannot stat file at checkpoint.uri

**Causes:**
- URI scheme not supported (e.g., s3:// without S3StorageWriter implemented)
- Worker path not accessible
- URI wrong

**Debug Steps:**

```bash
# Check checkpoint URI
cypher "MATCH (c:Checkpoint {ckp_id: 'e-001_c5'}) RETURN c.uri"

# Try to read manually
ls -la /path/to/checkpoint

# Check URIResolver support
python -c "from master.storage import URIResolver; r=URIResolver(); print(r.get_writer('s3://...'))"

# Check if file exists
python -c "import asyncio; from master.storage import URIResolver; asyncio.run(URIResolver().file_exists('file:///path/to/file'))"
```

**Solution:**
- Ensure checkpoint file exists at URI path
- If s3://, implement S3StorageWriter (currently stub)
- For file://, verify absolute path is correct

---

## Issue 8: Tests Failing — Neo4j Nodes Not Cleaned Up

**Symptom:** test_1 passes but test_2 fails with `UNIQUE constraint violation`

**Causes:**
- Test cleanup didn't run
- _TEST label not applied
- Previous test left nodes

**Debug Steps:**

```bash
# Count test nodes
cypher "MATCH (n:_TEST) RETURN LABELS(n), COUNT(*) GROUP BY LABELS(n)"

# Check for orphaned experiments
cypher "MATCH (e:Experiment) WHERE e.exp_id LIKE 'test-%' RETURN COUNT(e)"

# Manual cleanup
cypher "MATCH (n:_TEST) DETACH DELETE n"
```

**Solution:**
- Ensure conftest.py fixture cleanup runs
- Manually delete if stuck: `cypher "MATCH (e:Experiment) WHERE e.exp_id LIKE 'test-%' DETACH DELETE e"`

---

## Getting Help

**Check these in order:**

1. Read docs:
   - [Architecture](architecture.md) — System design
   - [Schema](schema.md) — Node types and relations
   - [API Reference](api-reference.md) — Endpoint details

2. Check logs:
   - `setups/setup_myexp/.daemon.log` — Daemon logs
   - `setups/setup_myexp/transfer_log.jsonl` — Audit trail
   - `docker logs fintuning-envelope-master-1` — API logs
   - `docker logs fintuning-envelope-neo4j-1` — Neo4j logs

3. Enable debug logging:
   ```bash
   export DEBUG=1
   export LOG_LEVEL=DEBUG
   bash run.sh
   ```

4. Collect logs for issue report:
   ```bash
   tar -czf debug-logs.tar.gz \
     setups/setup_myexp/.daemon.log \
     setups/setup_myexp/transfer_log.jsonl \
     .planning/STATE.md
   ```
