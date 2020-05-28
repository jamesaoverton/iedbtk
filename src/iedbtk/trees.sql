DROP TABLE IF EXISTS nonpeptide;
CREATE TABLE nonpeptide (
  parent TEXT,
  child TEXT,
  sort INT
);

DROP TABLE IF EXISTS label;
CREATE TABLE label (
  id TEXT,
  label TEXT
);

DROP TABLE IF EXISTS names;
CREATE VIRTUAL TABLE names USING FTS5(
  id,
  kind,
  name
);

ATTACH DATABASE "file:build/temp.db?mode=ro" AS source;

INSERT INTO nonpeptide
SELECT b.Obi_Id, a.Obi_Id, a.Node_Id
FROM source.molecule_finder_nonpep_tree a
JOIN source.molecule_finder_nonpep_tree b ON b.Node_Id = a.Parent_Node_Id;

INSERT INTO label
SELECT Obi_Id, Display_Name
FROM source.molecule_finder_nonpep_tree
WHERE Display_Name IS NOT NULL;

INSERT INTO names
SELECT id, 'label', label
FROM label
