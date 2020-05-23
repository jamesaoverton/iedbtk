-- # Define tables

DROP TABLE IF EXISTS statements;
CREATE TABLE statements (
  zn TEXT,
  sc TEXT,
  sb TEXT,
  pc TEXT,
  oi TEXT,
  oc TEXT,
  ob TEXT,
  ol TEXT,
  dc TEXT,
  lt TEXT
);

DROP TABLE IF EXISTS weights;
CREATE TABLE weights (
  id INT,
  weight INT
);

DROP TABLE IF EXISTS active;
CREATE TABLE active (
  id TEXT PRIMARY KEY,
  label TEXT,
  parent TEXT,
  weight INT,
  total INT
);


-- # Import data

.mode tabs
.import cache/weights.tsv weights

ATTACH DATABASE 'build/taxdmp.db' AS taxdmp;


-- # Fill tables

-- Add labels to statements
INSERT INTO statements(zn, sc, pc, oc)
SELECT "NCBITaxon:" || nodes.tax_id AS zn,
       "NCBITaxon:" || nodes.tax_id AS sc,
       "rdfs:label" AS pc,
       names.name_txt AS ol
FROM nodes JOIN names ON names.tax_id = nodes.tax_id
WHERE names.name_class = "scientific name";

-- Given a table of ids and weights
-- find the ancestors for each id
-- and return a table of ancestor ids and the descendant's weight.
-- Then use GROUP BY to sum over the weights.
WITH RECURSIVE
  ancestors(n, weight) AS (
    SELECT id, weight FROM weights
    UNION
    SELECT parent_tax_id, weight FROM nodes, ancestors
     WHERE tax_id = ancestors.n
      AND tax_id != parent_tax_id
  )
INSERT INTO active(id, label, parent, weight, total)
SELECT "NCBITaxon:" || n,
       names.name_txt,
       "NCBITaxon:" || nodes.parent_tax_id,
       coalesce(weights.weight, 0),
       SUM(ancestors.weight)
FROM ancestors
LEFT JOIN weights ON weights.id = n
JOIN nodes ON nodes.tax_id = n
JOIN names ON names.tax_id = n
WHERE names.name_class = "scientific name"
GROUP BY n;

--SELECT * FROM statements LIMIT 3;
--SELECT * FROM active LIMIT 3;
