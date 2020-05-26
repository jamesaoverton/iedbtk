-- Make a search table
DROP INDEX IF EXISTS search_structure_id;
DROP INDEX IF EXISTS search_source_antigen_id;
DROP INDEX IF EXISTS search_assay_id;
DROP INDEX IF EXISTS search_reference_id;
DROP INDEX IF EXISTS search_linear_sequence;
DROP INDEX IF EXISTS search_structure_assay_ids;
DROP INDEX IF EXISTS search_structure_reference_ids;
DROP INDEX IF EXISTS search_ids;
DROP TABLE IF EXISTS search;
CREATE TABLE search (
  search_id INTEGER PRIMARY KEY AUTOINCREMENT,
  structure_id INT,
  description TEXT,
  source_antigen_id TEXT,
  source_antigen_label TEXT,
  source_antigen_source_organism_id TEXT,
  source_antigen_source_organism_label TEXT,
  source_organism_id TEXT,
  source_organism_label TEXT,
  linear_sequence TEXT,
  tcell_id INT,
  bcell_id INT,
  elution_id INT,
  assay_id INT,
  assay_type_id TEXT,
  reference_id INT,
  pubmed_id INT,
  reference_author TEXT,
  reference_title TEXT,
  reference_date INT
);

INSERT INTO search
SELECT NULL AS search_id,
  structure_id,
  structure_description,
  source_antigen_obi_id AS source_antigen_id,
  source_antigen_name AS source_antigen_label,
  source_antigen_source_org_id AS source_antigen_source_organism_id,
  source_antigen_source_org_name AS source_antigen_source_organism_label,
  source_organism_id,
  source_organism_name AS source_organism_label,
  linear_sequence,
  tcell_id,
  bcell_id,
  elution_id,
  assay_id,
  as_type_id AS assay_type_id,
  reference_id,
  pubmed_id,
  reference_author,
  reference_title,
  reference_date
FROM simple_search;

CREATE INDEX search_structure_id ON search(structure_id);
CREATE INDEX search_source_antigen_id ON search(source_antigen_id);
CREATE INDEX search_assay_id ON search(assay_id);
CREATE INDEX search_reference_id ON search(reference_id);
CREATE INDEX search_linear_sequence ON search(linear_sequence);
CREATE INDEX search_structure_assay_ids ON search(structure_id, assay_id);
CREATE INDEX search_structure_reference_ids ON search(structure_id, reference_id);
CREATE INDEX search_ids ON search(structure_id, source_antigen_id, assay_id, reference_id);
