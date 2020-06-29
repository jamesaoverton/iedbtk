ATTACH DATABASE "file:build/source.db?mode=ro" AS source;
ATTACH DATABASE "file:build/nonpeptide.db?mode=ro" AS nonpeptide;

DROP TABLE IF EXISTS nonpeptide_tree;
CREATE TABLE nonpeptide_tree (
  parent TEXT,
  child TEXT,
  sort INT
);

DROP TABLE IF EXISTS nonpeptide_label;
CREATE TABLE nonpeptide_label (
  id TEXT,
  label TEXT
);

DROP TABLE IF EXISTS nonpeptide_name;
CREATE TABLE nonpeptide_name (
  id TEXT,
  kind TEXT,
  name TEXT
);

INSERT INTO nonpeptide_tree
SELECT s1.object, s1.subject, SUBSTR(s2.value, 1, 1)
FROM nonpeptide.statements s1
JOIN nonpeptide.statements s2 ON s2.subject = s1.subject
WHERE s1.predicate = 'rdfs:subClassOf'
  AND s2.predicate = 'IEDB:has-sort-name';

INSERT INTO nonpeptide_label
SELECT s.subject, s.value
FROM nonpeptide.statements s
WHERE s.predicate = 'rdfs:label';

INSERT INTO nonpeptide_name
SELECT id, 'label', label
FROM nonpeptide_label;

INSERT INTO nonpeptide_name
SELECT s.subject, 'synonym', l.label || " (" || s.value || ")"
FROM statements s
JOIN nonpeptide_label l ON l.id = s.subject
WHERE s.predicate IN (
  'IAO:0000118', -- alternative term
  'oio:hasExactSynonym',
  'oio:hasBroadSynonym',
  'oio:hasRelatedSynonym'
) AND s.value != l.label;

CREATE INDEX nonpeptide_tree_parent ON nonpeptide_tree(parent);
CREATE INDEX nonpeptide_tree_child ON nonpeptide_tree(child);
CREATE INDEX nonpeptide_label_id ON nonpeptide_label(id);



DROP TABLE IF EXISTS nonpeptide_old_tree;
CREATE TABLE nonpeptide_old_tree (
  parent TEXT,
  child TEXT,
  sort INT
);

DROP TABLE IF EXISTS nonpeptide_old_label;
CREATE TABLE nonpeptide_old_label (
  id TEXT,
  label TEXT
);

DROP TABLE IF EXISTS nonpeptide_old_name;
CREATE TABLE nonpeptide_old_name (
  id TEXT,
  kind TEXT,
  name TEXT
);

INSERT INTO nonpeptide_old_tree
SELECT b.Obi_Id, a.Obi_Id, a.Node_Id
FROM source.molecule_finder_nonpep_tree_old a
JOIN source.molecule_finder_nonpep_tree_old b ON b.Node_Id = a.Parent_Node_Id;

INSERT INTO nonpeptide_old_label
SELECT Obi_Id, Display_Name
FROM source.molecule_finder_nonpep_tree_old
WHERE Display_Name IS NOT NULL;

INSERT INTO nonpeptide_old_name
SELECT id, 'label', label
FROM nonpeptide_old_label;

WITH split(id, label, word, str) AS (
    SELECT Obi_Id, Display_Name, '', Secondary_Names || ', ' FROM source.molecule_finder_nonpep_tree_old
    UNION
    SELECT id, label,
      substr(str, 0, instr(str, ', ')),
      substr(str, instr(str, ', ') + 2)
    FROM split WHERE str != ''
)
INSERT INTO nonpeptide_old_name
SELECT id, 'synonym', label || " (" || word || ")"
FROM split WHERE word != '' AND word != label;

CREATE INDEX nonpeptide_old_tree_parent ON nonpeptide_old_tree(parent);
CREATE INDEX nonpeptide_old_tree_child ON nonpeptide_old_tree(child);
CREATE INDEX nonpeptide_old_label_id ON nonpeptide_old_label(id);


DROP VIEW IF EXISTS nonpeptide_all_name;
CREATE VIEW nonpeptide_all_name AS
SELECT * FROM nonpeptide_name
UNION ALL
SELECT * FROM nonpeptide_old_name;
