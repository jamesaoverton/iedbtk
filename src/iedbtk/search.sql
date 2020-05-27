-- Make a search table
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
  non_peptide_id TEXT,
  tcell_id INT,
  bcell_id INT,
  elution_id INT,
  assay_id INT,
  assay_type_id TEXT,
  assay_positive BOOLEAN,
  reference_id INT,
  pubmed_id INT,
  reference_author TEXT,
  reference_title TEXT,
  reference_date INT
);


ATTACH DATABASE "file:build/temp.db?mode=ro" AS source;


INSERT INTO search
SELECT NULL AS search_id,
  structure_id,
  structure_description,
  NULLIF(source_antigen_obi_id, '') AS source_antigen_id,
  NULLIF(source_antigen_name, '') AS source_antigen_label,
  NULLIF(source_antigen_source_org_id, '')AS source_antigen_source_organism_id,
  NULLIF(source_antigen_source_org_name, '') AS source_antigen_source_organism_label,
  NULLIF(source_organism_id, ''),
  NULLIF(source_organism_name, '') AS source_organism_label,
  NULLIF(linear_sequence, ''),
  NULLIF(non_peptidic_obi_id, '') AS non_peptide_id,
  NULLIF(tcell_id, ''),
  NULLIF(bcell_id, ''),
  NULLIF(elution_id, ''),
  assay_id,
  as_type_id AS assay_type_id,
  like('Positive%', qualitative_measure) AS assay_positive,
  reference_id,
  NULLIF(pubmed_id, ''),
  NULLIF(reference_author, ''),
  NULLIF(reference_title, ''),
  NULLIF(reference_date, '')
FROM source.simple_search;

CREATE INDEX search_structure_id ON search(structure_id);
CREATE INDEX search_source_antigen_id ON search(source_antigen_id);
CREATE INDEX search_assay_id ON search(assay_id);
CREATE INDEX search_reference_id ON search(reference_id);
CREATE INDEX search_linear_sequence ON search(linear_sequence);
CREATE INDEX search_non_peptide_id ON search(non_peptide_id);
CREATE INDEX search_structure_assay_ids ON search(structure_id, assay_id);
CREATE INDEX search_structure_reference_ids ON search(structure_id, reference_id);
CREATE INDEX search_ids ON search(structure_id, source_antigen_id, assay_id, reference_id);
